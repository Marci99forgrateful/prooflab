"""A retained native frontier with budget-conditioned strategy decisions.

The historical engine and all Phase 1–6 executable sources remain unchanged.
Every success is independently checked on the original theorem and full prefix.
"""

from __future__ import annotations

import heapq
import json
import time
from pathlib import Path
from threading import Event
from typing import Any

from prooflab.adaptive import CanonicalOutcomeRanking, HybridProvider, context_features
from prooflab.budget_policy import BudgetModel, choose, features, staged_mode
from prooflab.lean import Cancelled, LeanError, LeanTimeout, theorem_source, verify
from prooflab.models import Budget, Node, ProofState, Task, Trace
from prooflab.phase6_metering import MeteredAdaptive
from prooflab.search import metadata, path_to


def run(
    task: Task,
    budget: Budget,
    variant: str = "conservative",
    *,
    prefix: list[str] | None = None,
    forced_mode: str | None = None,
    model_path: Path | None = None,
    cancel: Event | None = None,
) -> Trace:
    if forced_mode not in (None, "symbolic", "hybrid", "typed"):
        raise ValueError("Unknown forced strategy")
    if variant not in ("completion", "cost", "joint", "conservative", "root_only", "staged"):
        raise ValueError("Unknown policy")
    started, cpu_started = time.monotonic(), time.thread_time()
    deadline = started + budget.timeout_s
    model = BudgetModel(model_path) if forced_mode is None and variant != "staged" else None
    ranker = CanonicalOutcomeRanking()
    providers = {
        m: HybridProvider("deterministic", forced_mode=m) for m in ("symbolic", "hybrid", "typed")
    }
    trace = Trace(task=task, algorithm="outcome", budget=budget, metadata=metadata())
    prefix = list(prefix or [])
    trace.metadata.update(
        phase="7",
        policy=variant,
        prefix=json.dumps(prefix),
        budget_model_sha256=model.sha256 if model else "not used",
    )
    queue: list[tuple[float, int]] = []
    paths: dict[int, list[str]] = {0: []}
    seen: set[tuple[str, ...]] = {()}
    last_mode: str | None = None
    root_mode: str | None = None
    nonexistential = 0
    switches = 0
    lean_ref = None

    def remaining() -> float:
        return max(0.001, deadline - time.monotonic())

    try:
        tick = time.monotonic()
        with MeteredAdaptive(task, timeout=min(20, remaining()), cancel=cancel) as lean:
            lean_ref = lean
            state = lean.initial
            for tactic in prefix:
                msg = lean.step(state.state_id, tactic, min(budget.tactic_timeout_s, remaining()))
                if msg["status"] != "accepted":
                    raise LeanError("Development prefix could not be replayed: " + tactic)
                state = ProofState(state_id=msg["state_id"], goals=msg["goals"])
            trace.metrics.initialization_s = time.monotonic() - tick
            if not state.goals:
                raise ValueError("Continuation must start from a nonterminal Lean state")
            trace.nodes.append(
                Node(id=0, parent=None, depth=0, state=state, tactic=None, status="root")
            )
            queue.append((0, 0))
            while queue:
                if cancel is not None and cancel.is_set():
                    raise Cancelled("Search cancelled")
                if time.monotonic() >= deadline:
                    trace.termination = "resource_limit:wall_time"
                    break
                if trace.metrics.expanded_states >= budget.max_expansions:
                    trace.termination = "resource_limit:expansions"
                    break
                if trace.metrics.attempted_candidates >= budget.max_attempts:
                    trace.termination = "resource_limit:attempts"
                    break
                _, ident = heapq.heappop(queue)
                node = trace.nodes[ident]
                assert node.state is not None
                if node.depth >= budget.max_depth:
                    trace.termination = "resource_limit:depth"
                    continue
                trace.metrics.expanded_states += 1
                f = features(
                    node.state,
                    budget.max_attempts - trace.metrics.attempted_candidates,
                    budget.max_expansions - trace.metrics.expanded_states,
                    remaining(),
                    node.depth + len(prefix),
                )
                if not context_features(node.state)["head:Exists"]:
                    nonexistential += 1
                baseline = staged_mode(node.state, nonexistential)
                inference_tick = time.monotonic()
                predictions = model.predictions(f) if model else {}
                scores: dict[str, float] = {}
                decision, reason = baseline, "deterministic staged policy"
                if forced_mode:
                    decision, reason = forced_mode, "matched development continuation"
                elif model:
                    decision, reason, scores = choose(
                        predictions,
                        baseline,
                        variant,
                        budget.max_attempts - trace.metrics.attempted_candidates,
                        float(model.artifact["conservative_margin"]),
                    )
                    if variant == "root_only":
                        root_mode = root_mode or decision
                        decision, reason = (
                            root_mode,
                            "root-only strategy ablation; no later switching",
                        )
                inference_s = time.monotonic() - inference_tick
                switches += int(last_mode is not None and last_mode != decision)
                last_mode = decision
                tick = time.monotonic()
                candidates, record = providers[decision].generate(
                    lean,
                    node.state,
                    budget.max_candidates,
                    frozenset(task.forbidden_lemmas),
                    min(budget.tactic_timeout_s, remaining()),
                )
                trace.metrics.planning_s += time.monotonic() - tick
                record.update(
                    phase=7,
                    node_id=ident,
                    decision=decision,
                    baseline_decision=baseline,
                    decision_reason=reason,
                    predictions=predictions,
                    decision_scores=scores,
                    budget_features=f,
                    strategy_switches=switches,
                    retained_frontier=len(queue),
                    policy=variant,
                    attempts_before=trace.metrics.attempted_candidates,
                    model_inference_s=record.get("model_inference_s", 0) + inference_s,
                )
                trace.retrievals.append(record)
                trace.metrics.model_inference_s += record["model_inference_s"]
                for candidate in ranker.rank_candidates(node.state, candidates):
                    if cancel is not None and cancel.is_set():
                        raise Cancelled("Search cancelled")
                    if trace.metrics.attempted_candidates >= budget.max_attempts:
                        trace.termination = "resource_limit:attempts"
                        return trace
                    if time.monotonic() >= deadline:
                        trace.termination = "resource_limit:wall_time"
                        return trace
                    suffix = [*paths[ident], candidate.tactic]
                    if tuple(suffix) in seen:
                        continue
                    seen.add(tuple(suffix))
                    tick = time.monotonic()
                    trace.metrics.attempted_candidates += 1
                    try:
                        msg = lean.step(
                            node.state.state_id,
                            candidate.tactic,
                            min(budget.tactic_timeout_s, remaining()),
                        )
                    except (LeanError, OSError) as error:
                        trace.nodes.append(
                            Node(
                                id=len(trace.nodes),
                                parent=ident,
                                depth=node.depth + 1,
                                state=None,
                                tactic=candidate.tactic,
                                status="error",
                                error=str(error),
                                elapsed_ms=(time.monotonic() - tick) * 1000,
                            )
                        )
                        raise
                    elapsed = time.monotonic() - tick
                    trace.metrics.lean_execution_s += elapsed
                    trace.metrics.tactic_heartbeats += msg.get("native_heartbeats", 0)
                    accepted = msg["status"] == "accepted"
                    if msg["status"] == "execution_error":
                        raise LeanError(str(msg))
                    successor = (
                        ProofState(state_id=msg["state_id"], goals=msg["goals"])
                        if accepted
                        else None
                    )
                    child = len(trace.nodes)
                    solved = successor is not None and not successor.goals
                    trace.nodes.append(
                        Node(
                            id=child,
                            parent=ident,
                            depth=node.depth + 1,
                            state=successor,
                            tactic=candidate.tactic,
                            category=candidate.category,
                            reason=candidate.reason,
                            status="solved" if solved else "accepted" if accepted else "rejected",
                            error=msg.get("error"),
                            elapsed_ms=elapsed * 1000,
                            native_heartbeats=msg.get("native_heartbeats"),
                        )
                    )
                    trace.metrics.max_depth = max(trace.metrics.max_depth, node.depth + 1)
                    if not accepted:
                        trace.metrics.rejected_candidates += 1
                        continue
                    trace.metrics.accepted_transitions += 1
                    paths[child] = suffix
                    if solved:
                        trace.proof = [*prefix, *suffix]
                        trace.lean_source = theorem_source(task, trace.proof)
                        trace.verification = verify(task, trace.proof, min(20, remaining()), cancel)
                        trace.metrics.verification_s = trace.verification.elapsed_s
                        trace.status = (
                            "verified" if trace.verification.verified else "execution_error"
                        )
                        trace.termination = (
                            "verified"
                            if trace.verification.verified
                            else "independent_verification_failed"
                        )
                        trace.error = trace.verification.error
                        if trace.verification.verified:
                            trace.metrics.proof_length = len(trace.proof)
                            trace.proof_origin = "constructed_derivation"
                            for path_id in path_to(trace.nodes, child):
                                trace.nodes[path_id].on_proof_path = True
                        return trace
                    assert successor is not None
                    heapq.heappush(queue, (ranker.state_priority(successor, node.depth + 1), child))
    except Cancelled as error:
        trace.status, trace.termination, trace.error = "cancelled", "cancelled", str(error)
    except LeanTimeout as error:
        trace.termination, trace.error = "resource_limit:lean_timeout", str(error)
    except (LeanError, OSError, ValueError) as error:
        trace.status, trace.termination, trace.error = (
            "execution_error",
            "execution_error",
            str(error),
        )
    finally:
        trace.metrics.elapsed_s = time.monotonic() - started
        trace.metrics.coordinator_cpu_s = time.thread_time() - cpu_started
        trace.metrics.frontier = len(queue)
        trace.metadata["strategy_switches"] = str(switches)
        if lean_ref is not None:
            events: list[dict[str, Any]] = getattr(lean_ref, "retrieval_events", [])
            trace.metadata["native_query_events"] = json.dumps(events)
            trace.metrics.retrieval_queries = len(events)
            trace.metrics.retrieval_s = sum(e["elapsed_s"] for e in events)
            trace.metrics.lean_execution_s += trace.metrics.retrieval_s
            for field in ("declaration_probes", "rewrite_probes", "term_constructions"):
                setattr(
                    trace.metrics, field, sum(e.get("native", {}).get(field, 0) for e in events)
                )
            trace.metrics.retrieval_heartbeats = sum(
                e.get("native", {}).get("heartbeats", 0) for e in events
            )
            usage = getattr(lean_ref, "resource_usage", {})
            trace.metrics.session_cpu_s = usage.get("cpu_s")
            trace.metrics.session_peak_rss_kib = usage.get("peak_rss_kib")
    return trace
