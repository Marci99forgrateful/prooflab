"""Bounded breadth-first / heuristic best-first search over authentic Lean states."""

from __future__ import annotations

import heapq
import platform
import subprocess
import time
from collections import deque
from threading import Event
from typing import Literal

from prooflab.candidates import (
    HeuristicRanking,
    RankingPolicy,
    UniformRanking,
    generate_candidates,
)
from prooflab.lean import (
    ROOT,
    Cancelled,
    LeanError,
    LeanSession,
    LeanTimeout,
    theorem_source,
    verify,
)
from prooflab.models import Budget, Candidate, Node, ProofState, Task, Trace


def metadata() -> dict[str, str]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "code_commit": commit.stdout.strip(),
        "lean_version": (ROOT / "lean-toolchain").read_text().strip(),
        "mathlib_revision": "f897ebcf72cd16f89ab4577d0c826cd14afaafc7",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "seed": "0 (deterministic)",
        "state_identity": "Exact tactic prefix within one native session; no semantic merging",
    }


def path_to(nodes: list[Node], node_id: int) -> list[int]:
    result = []
    current: int | None = node_id
    while current is not None:
        result.append(current)
        current = nodes[current].parent
    return list(reversed(result))


def search(
    task: Task,
    algorithm: Literal["bfs", "best_first", "automation"] = "bfs",
    budget: Budget | None = None,
    cancel: Event | None = None,
    ranking: RankingPolicy | None = None,
) -> Trace:
    budget = budget or Budget()
    trace = Trace(task=task, algorithm=algorithm, budget=budget, metadata=metadata())
    start = time.monotonic()
    deadline = start + budget.timeout_s
    policy = ranking or (HeuristicRanking() if algorithm == "best_first" else UniformRanking())
    fifo: deque[int] = deque([0])
    priority: list[tuple[float, int]] = [(0, 0)]
    prefixes: dict[int, tuple[str, ...]] = {0: ()}
    visited: set[tuple[str, ...]] = {()}

    def remaining() -> float:
        return max(0.001, deadline - time.monotonic())

    try:
        init_start = time.monotonic()
        with LeanSession(task, timeout=min(20, remaining()), cancel=cancel) as lean:
            trace.metrics.initialization_s = time.monotonic() - init_start
            trace.nodes.append(
                Node(
                    id=0,
                    parent=None,
                    depth=0,
                    state=lean.initial,
                    tactic=None,
                    status="root",
                )
            )
            while fifo if algorithm != "best_first" else priority:
                if cancel is not None and cancel.is_set():
                    raise Cancelled("Search cancelled")
                if time.monotonic() >= deadline:
                    trace.termination = "resource_limit:wall_time"
                    break
                if trace.metrics.expanded_states >= budget.max_expansions:
                    trace.termination = "resource_limit:expansions"
                    break
                current = (
                    heapq.heappop(priority)[1] if algorithm == "best_first" else fifo.popleft()
                )
                node = trace.nodes[current]
                assert node.state is not None
                if node.depth >= budget.max_depth:
                    trace.termination = "resource_limit:depth"
                    continue
                trace.metrics.expanded_states += 1
                plan_start = time.monotonic()
                candidates = generate_candidates(
                    node.state,
                    budget.max_candidates,
                    frozenset(task.forbidden_lemmas),
                )
                if algorithm == "automation":
                    candidates = [
                        Candidate(
                            tactic="aesop",
                            category="reference",
                            reason="Native Aesop baseline; not a ProofLab algorithm",
                        )
                    ]
                candidates = policy.rank_candidates(node.state, candidates)
                trace.metrics.planning_s += time.monotonic() - plan_start
                for candidate in candidates:
                    if cancel is not None and cancel.is_set():
                        raise Cancelled("Search cancelled")
                    if trace.metrics.attempted_candidates >= budget.max_attempts:
                        trace.termination = "resource_limit:attempts"
                        return trace
                    if time.monotonic() >= deadline:
                        trace.termination = "resource_limit:wall_time"
                        return trace
                    prefix = (*prefixes[current], candidate.tactic)
                    if prefix in visited:
                        continue
                    visited.add(prefix)
                    tick = time.monotonic()
                    trace.metrics.attempted_candidates += 1
                    try:
                        message = lean.step(
                            node.state.state_id,
                            candidate.tactic,
                            min(budget.tactic_timeout_s, remaining()),
                        )
                    except (LeanError, OSError) as error:
                        elapsed = time.monotonic() - tick
                        trace.metrics.lean_execution_s += elapsed
                        trace.nodes.append(
                            Node(
                                id=len(trace.nodes),
                                parent=current,
                                depth=node.depth + 1,
                                state=None,
                                tactic=candidate.tactic,
                                category=candidate.category,
                                reason=candidate.reason,
                                status="error",
                                error=str(error),
                                elapsed_ms=elapsed * 1000,
                            )
                        )
                        raise
                    elapsed = time.monotonic() - tick
                    trace.metrics.lean_execution_s += elapsed
                    accepted = message.get("status") == "accepted"
                    if message.get("status") == "execution_error":
                        raise LeanError(str(message))
                    state = (
                        ProofState.model_validate(
                            {
                                "state_id": message["state_id"],
                                "goals": message["goals"],
                            }
                        )
                        if accepted
                        else None
                    )
                    ident = len(trace.nodes)
                    solved = state is not None and not state.goals
                    successor = Node(
                        id=ident,
                        parent=current,
                        depth=node.depth + 1,
                        state=state,
                        tactic=candidate.tactic,
                        category=candidate.category,
                        lemma=candidate.lemma,
                        provenance=candidate.provenance,
                        reason=candidate.reason,
                        status="solved" if solved else "accepted" if accepted else "rejected",
                        error=message.get("error"),
                        elapsed_ms=elapsed * 1000,
                    )
                    trace.nodes.append(successor)
                    trace.metrics.max_depth = max(trace.metrics.max_depth, successor.depth)
                    if not accepted:
                        trace.metrics.rejected_candidates += 1
                        continue
                    trace.metrics.accepted_transitions += 1
                    prefixes[ident] = prefix
                    if solved:
                        trace.proof = list(prefix)
                        trace.lean_source = theorem_source(task, trace.proof)
                        trace.verification = verify(task, trace.proof, min(20, remaining()), cancel)
                        trace.metrics.verification_s = trace.verification.elapsed_s
                        if trace.verification.verified:
                            trace.status = "verified"
                            trace.termination = "verified"
                            trace.metrics.proof_length = len(trace.proof)
                            trace.proof_origin = (
                                "native_automation"
                                if algorithm == "automation"
                                else "retrieved_lemma"
                                if len(prefix) == 1 and candidate.lemma
                                else "specialized_tactic"
                                if len(prefix) == 1 and candidate.category == "specialized"
                                else "constructed_derivation"
                            )
                            for path_id in path_to(trace.nodes, ident):
                                trace.nodes[path_id].on_proof_path = True
                        else:
                            trace.status = "execution_error"
                            trace.termination = "independent_verification_failed"
                            trace.error = trace.verification.error
                        return trace
                    if algorithm == "best_first":
                        assert state is not None
                        heapq.heappush(
                            priority, (policy.state_priority(state, successor.depth), ident)
                        )
                    else:
                        fifo.append(ident)
                if algorithm == "automation":
                    break
    except Cancelled as error:
        trace.status = "cancelled"
        trace.termination = "cancelled"
        trace.error = str(error)
    except LeanTimeout as error:
        trace.termination = "resource_limit:lean_timeout"
        trace.error = str(error)
    except (LeanError, OSError, ValueError) as error:
        trace.status = "execution_error"
        trace.termination = "execution_error"
        trace.error = str(error)
    finally:
        trace.metrics.elapsed_s = time.monotonic() - start
        trace.metrics.frontier = len(priority) if algorithm == "best_first" else len(fifo)
    return trace
