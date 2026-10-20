"""Bounded breadth-first / heuristic best-first search over authentic Lean states."""

from __future__ import annotations

import heapq
import platform
import subprocess
import time
from collections import deque
from collections.abc import Callable
from threading import Event
from typing import Any, Protocol

from prooflab.candidates import (
    HeuristicRanking,
    RankingPolicy,
    UniformRanking,
    generate_candidates,
)
from prooflab.frontier import FrontierModel, handcrafted_priority
from prooflab.lean import (
    ROOT,
    Cancelled,
    LeanError,
    LeanSession,
    LeanTimeout,
    theorem_source,
    verify,
)
from prooflab.learning import LearnedRanking
from prooflab.models import (
    Budget,
    Candidate,
    CandidateRanking,
    FrontierDecision,
    FrontierValue,
    Node,
    ProofState,
    SearchAlgorithm,
    StateRanking,
    Task,
    Trace,
)
from prooflab.outcome import MODELS, OutcomeRanking


class CandidateProvider(Protocol):
    def generate(
        self,
        lean: LeanSession,
        state: ProofState,
        limit: int,
        forbidden: frozenset[str],
        timeout: float,
    ) -> tuple[list[Candidate], dict[str, Any]]: ...


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
    algorithm: SearchAlgorithm = "bfs",
    budget: Budget | None = None,
    cancel: Event | None = None,
    ranking: RankingPolicy | None = None,
    comparison_ranker: LearnedRanking | None = None,
    comparison_outcome: OutcomeRanking | None = None,
    comparison_frontier: FrontierModel | None = None,
    beam_width: int = 12,
    generator: Callable[[ProofState, int, frozenset[str]], list[Candidate]] = generate_candidates,
    provider: CandidateProvider | None = None,
    session_factory: type[LeanSession] = LeanSession,
) -> Trace:
    budget = budget or Budget()
    trace = Trace(task=task, algorithm=algorithm, budget=budget, metadata=metadata())
    start = time.monotonic()
    cpu_start = time.thread_time()
    lean_ref: LeanSession | None = None
    deadline = start + budget.timeout_s
    policy: RankingPolicy = ranking or (
        HeuristicRanking() if algorithm in ("best_first", "learned") else UniformRanking()
    )
    outcome_algorithms = ("outcome", "applicability_only", "old_features_outcome")
    frontier_algorithms = ("frontier", "joint", "beam", "linear_frontier")
    use_heap = algorithm in ("best_first", "learned", *outcome_algorithms, *frontier_algorithms)
    if beam_width < 1:
        raise ValueError("Positive beam width required")
    fifo: deque[int] = deque([0])
    priority: list[tuple[float, int]] = [(0, 0)]
    prefixes: dict[int, tuple[str, ...]] = {0: ()}
    visited: set[tuple[str, ...]] = {()}

    def remaining() -> float:
        return max(0.001, deadline - time.monotonic())

    try:
        if algorithm in frontier_algorithms:
            comparison_frontier = comparison_frontier or FrontierModel()
            if algorithm == "frontier":
                policy = HeuristicRanking()
            else:
                policy = ranking if isinstance(ranking, OutcomeRanking) else OutcomeRanking()
            comparison_ranker = comparison_ranker or LearnedRanking()
            comparison_outcome = comparison_outcome or OutcomeRanking()
        if comparison_frontier is not None:
            trace.metadata["frontier_model_sha256"] = comparison_frontier.sha256
            trace.metadata["frontier_lookahead_calls"] = "0: observed native descriptions only"
        if algorithm in outcome_algorithms:
            if ranking is not None and not isinstance(ranking, OutcomeRanking):
                raise ValueError("An outcome run requires an exported OutcomeRanking")
            policy = (
                ranking
                if isinstance(ranking, OutcomeRanking)
                else OutcomeRanking(MODELS / f"{algorithm}.json")
            )
            if policy.model.variant != algorithm:
                raise ValueError("Outcome model variant differs from requested algorithm")
            comparison_ranker = comparison_ranker or LearnedRanking()
            comparison_outcome = comparison_outcome or policy
            trace.metadata["policy_model_sha256"] = policy.model_hash
        if comparison_outcome is not None:
            trace.metadata["outcome_model_sha256"] = comparison_outcome.model_hash
            trace.metadata["outcome_feature_version"] = comparison_outcome.model.feature_version
            trace.metadata["outcome_lookahead_calls"] = "0: pre-execution features only"
        if algorithm == "learned":
            if ranking is not None and not isinstance(ranking, LearnedRanking):
                raise ValueError("A learned run requires a genuinely trained LearnedRanking")
            policy = ranking if isinstance(ranking, LearnedRanking) else LearnedRanking()
            comparison_ranker = policy
        if comparison_ranker is not None:
            trace.metadata.update(
                {
                    "model_sha256": comparison_ranker.model_hash,
                    "feature_version": comparison_ranker.model.feature_version,
                    "learned_scores_used_for_scheduling": str(algorithm == "learned").lower(),
                    "frontier_policy": "handcrafted state score; stable insertion-ID ties",
                }
            )
        if algorithm in frontier_algorithms:
            trace.metadata["frontier_policy"] = (
                "fitted log continuation cost + .15 depth; insertion scores; node-ID ties"
            )
            trace.metadata["beam_width"] = (
                str(beam_width) if algorithm == "beam" else "unbounded within budget"
            )
        if algorithm in ("automation", "grind"):
            trace.metadata["frontier_policy"] = (
                "Native external reference; internal scheduler opaque"
            )
        elif algorithm == "bfs":
            trace.metadata["frontier_policy"] = "FIFO breadth-first; model values are annotations"
        trace.metadata["generator"] = generator.__module__ + "." + generator.__name__

        def record_value(
            state: ProofState, depth: int, parent: ProofState | None, ident: int
        ) -> float:
            tick = time.monotonic()
            heuristic = handcrafted_priority(state, depth)
            value, contributions = (
                comparison_frontier.explain(state, depth, parent)
                if comparison_frontier
                else (0.0, [])
            )
            state_priority = (
                comparison_frontier.priority(value, depth)
                if comparison_frontier and algorithm in frontier_algorithms
                else policy.state_priority(state, depth)
            )
            if comparison_frontier:
                trace.state_values.append(
                    FrontierValue(
                        node_id=ident,
                        priority=state_priority,
                        learned_value=value,
                        heuristic_priority=heuristic,
                        contributions=contributions,
                    )
                )
                trace.metrics.model_inference_s += time.monotonic() - tick
            trace.metrics.planning_s += time.monotonic() - tick
            return state_priority

        init_start = time.monotonic()
        with session_factory(task, timeout=min(20, remaining()), cancel=cancel) as lean:
            lean_ref = lean
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
            root_priority = record_value(lean.initial, 0, None, 0)
            priority = [(root_priority, 0)]
            while priority if use_heap else fifo:
                if cancel is not None and cancel.is_set():
                    raise Cancelled("Search cancelled")
                if time.monotonic() >= deadline:
                    trace.termination = "resource_limit:wall_time"
                    break
                if trace.metrics.expanded_states >= budget.max_expansions:
                    trace.termination = "resource_limit:expansions"
                    break
                if comparison_frontier:
                    trace.frontier_decisions.append(
                        FrontierDecision(
                            selected=priority[0][1] if use_heap else fifo[0],
                            attempted_candidates=trace.metrics.attempted_candidates,
                            frontier=sorted(priority)
                            if use_heap
                            else [(float(trace.nodes[i].depth), i) for i in fifo],
                        )
                    )
                current = heapq.heappop(priority)[1] if use_heap else fifo.popleft()
                node = trace.nodes[current]
                assert node.state is not None
                if node.depth >= budget.max_depth:
                    trace.termination = "resource_limit:depth"
                    continue
                trace.metrics.expanded_states += 1
                plan_start = time.monotonic()
                retrieval_wall = 0.0
                if provider is not None and algorithm not in ("automation", "grind"):
                    candidates, observation = provider.generate(
                        lean,
                        node.state,
                        budget.max_candidates,
                        frozenset(task.forbidden_lemmas),
                        min(budget.tactic_timeout_s, remaining()),
                    )
                    observation["node_id"] = current
                    trace.retrievals.append(observation)
                    retrieval_wall = observation.get("query_wall_s", 0.0)
                    trace.metrics.retrieval_s += retrieval_wall
                    trace.metrics.lean_execution_s += retrieval_wall
                    trace.metrics.retrieval_queries += int(bool(observation.get("native")))
                    native = observation.get("native", {})
                    for field in ("declaration_probes", "rewrite_probes", "term_constructions"):
                        setattr(
                            trace.metrics,
                            field,
                            getattr(trace.metrics, field) + native.get(field, 0),
                        )
                    trace.metrics.retrieval_heartbeats += native.get("heartbeats", 0)
                else:
                    candidates = generator(
                        node.state,
                        budget.max_candidates,
                        frozenset(task.forbidden_lemmas),
                    )
                if algorithm in ("automation", "grind"):
                    candidates = [
                        Candidate(
                            tactic="aesop" if algorithm == "automation" else "grind",
                            category="reference",
                            reason="Native symbolic reference; internal work differs from ProofLab",
                        )
                    ]
                availability = sorted(c.model_dump_json() for c in candidates)
                generated_order = {c.tactic: i for i, c in enumerate(candidates)}
                ranking_tick = time.monotonic()
                candidates = policy.rank_candidates(node.state, candidates)
                if isinstance(policy, (LearnedRanking, OutcomeRanking)):
                    trace.metrics.model_inference_s += time.monotonic() - ranking_tick
                if sorted(c.model_dump_json() for c in candidates) != availability:
                    raise ValueError("Ranking policy altered candidate availability")
                if comparison_ranker is not None and algorithm not in ("automation", "grind"):
                    inference_tick = time.monotonic()
                    trace.rankings.append(
                        StateRanking(
                            node_id=current,
                            candidates=[
                                CandidateRanking(
                                    tactic=c.tactic,
                                    category=c.category,
                                    generated_order=generated_order[c.tactic],
                                    actual_rank=i + 1,
                                    heuristic_score=c.prior,
                                    learned_score=comparison_ranker.score(node.state, c),
                                    contributions=comparison_ranker.contributions(node.state, c),
                                    outcome_score=(
                                        comparison_outcome.score(node.state, c)
                                        if comparison_outcome is not None
                                        else None
                                    ),
                                    outcome_contributions=(
                                        comparison_outcome.contributions(node.state, c)
                                        if comparison_outcome is not None
                                        else []
                                    ),
                                    policy_score=(
                                        policy.score(node.state, c)
                                        if isinstance(policy, (LearnedRanking, OutcomeRanking))
                                        else None
                                    ),
                                )
                                for i, c in enumerate(candidates)
                            ],
                        )
                    )
                    trace.metrics.model_inference_s += time.monotonic() - inference_tick
                trace.metrics.planning_s += max(0, time.monotonic() - plan_start - retrieval_wall)
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
                    trace.metrics.tactic_heartbeats += message.get("native_heartbeats", 0)
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
                        native_heartbeats=message.get("native_heartbeats"),
                        native_elapsed_s=(
                            message["native_elapsed_ns"] / 1e9
                            if "native_elapsed_ns" in message
                            else None
                        ),
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
                                if algorithm in ("automation", "grind")
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
                    assert state is not None
                    insertion_priority = record_value(state, successor.depth, node.state, ident)
                    if use_heap:
                        heapq.heappush(priority, (insertion_priority, ident))
                        if algorithm == "beam" and len(priority) > beam_width:
                            worst = max(priority)
                            priority.remove(worst)
                            heapq.heapify(priority)
                            trace.beam_evictions.append(worst[1])
                    else:
                        fifo.append(ident)
                if algorithm in ("automation", "grind"):
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
        trace.metrics.coordinator_cpu_s = time.thread_time() - cpu_start
        if lean_ref is not None:
            usage = getattr(lean_ref, "resource_usage", {})
            trace.metrics.session_cpu_s = usage.get("cpu_s")
            trace.metrics.session_peak_rss_kib = usage.get("peak_rss_kib")
        trace.metrics.elapsed_s = time.monotonic() - start
        trace.metrics.frontier = len(priority) if use_heap else len(fifo)
    return trace
