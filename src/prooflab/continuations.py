"""Real valid-alternative rollouts; unresolved finite searches remain censored."""

from __future__ import annotations

import heapq
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prooflab.candidates import HeuristicRanking, generate_candidates
from prooflab.dataset import get_task
from prooflab.lean import ROOT, LeanError, LeanSession, LeanTimeout, verify
from prooflab.models import Budget, Candidate, Node, ProofState, Task, Verification
from prooflab.phase3_data import DIRECTORY, check_freeze, digest
from prooflab.search import metadata, path_to
from prooflab.training import demonstration

DATA = ROOT / "experiments/phase3/continuations-v1"


def rollout(
    lean: LeanSession,
    task: Task,
    prefix: list[str],
    first: Candidate,
    successor: ProofState,
    budget: Budget,
    audit_timeout: float,
) -> dict[str, Any]:
    """Search one actual successor with fixed handcrafted scheduling.

    The first accepted action costs one attempt. Audit time is reported separately
    from the downstream search-time budget. Every successful full path is rechecked.
    """
    start = time.monotonic()
    deadline = start + budget.timeout_s
    nodes = [Node(id=0, parent=None, depth=0, state=successor, tactic=None, status="root")]
    pools = []
    heap = [(0.0, 0)]
    suffixes: dict[int, list[str]] = {0: []}
    attempts, expanded, lean_s = 1, 0, 0.0
    status, termination = "censored", "search_exhausted"
    proof: list[str] = []
    audit = Verification()
    policy = HeuristicRanking()
    solved_id: int | None = 0 if not successor.goals else None
    try:
        while heap and solved_id is None:
            if time.monotonic() >= deadline:
                termination = "resource_limit:wall_time"
                break
            if attempts >= budget.max_attempts:
                termination = "resource_limit:attempts"
                break
            if expanded >= budget.max_expansions:
                termination = "resource_limit:expansions"
                break
            current = heapq.heappop(heap)[1]
            node = nodes[current]
            assert node.state is not None
            if node.depth >= budget.max_depth:
                termination = "resource_limit:depth"
                continue
            expanded += 1
            candidates = generate_candidates(
                node.state, budget.max_candidates, frozenset(task.forbidden_lemmas)
            )
            ordered = policy.rank_candidates(node.state, candidates)
            pools.append(
                {
                    "node_id": current,
                    "generated": [c.model_dump() for c in candidates],
                    "actual_order": [c.tactic for c in ordered],
                }
            )
            for candidate in ordered:
                if attempts >= budget.max_attempts or time.monotonic() >= deadline:
                    termination = (
                        "resource_limit:attempts"
                        if attempts >= budget.max_attempts
                        else "resource_limit:wall_time"
                    )
                    break
                attempts += 1
                tick = time.monotonic()
                try:
                    message = lean.step(
                        node.state.state_id,
                        candidate.tactic,
                        min(budget.tactic_timeout_s, max(0.001, deadline - time.monotonic())),
                    )
                except (LeanError, OSError) as error:
                    elapsed = time.monotonic() - tick
                    lean_s += elapsed
                    nodes.append(
                        Node(
                            id=len(nodes),
                            parent=current,
                            depth=node.depth + 1,
                            state=None,
                            tactic=candidate.tactic,
                            status="error",
                            error=str(error),
                            elapsed_ms=1000 * elapsed,
                        )
                    )
                    raise
                elapsed = time.monotonic() - tick
                lean_s += elapsed
                if message["status"] not in ("accepted", "invalid_candidate"):
                    raise LeanError(str(message))
                accepted = message["status"] == "accepted"
                state = (
                    ProofState(state_id=message["state_id"], goals=message["goals"])
                    if accepted
                    else None
                )
                ident = len(nodes)
                solved = state is not None and not state.goals
                nodes.append(
                    Node(
                        id=ident,
                        parent=current,
                        depth=node.depth + 1,
                        state=state,
                        tactic=candidate.tactic,
                        category=candidate.category,
                        status="solved" if solved else "accepted" if accepted else "rejected",
                        error=message.get("error"),
                        elapsed_ms=1000 * elapsed,
                    )
                )
                if accepted:
                    suffixes[ident] = [*suffixes[current], candidate.tactic]
                    if solved:
                        solved_id = ident
                        break
                    assert state is not None
                    heapq.heappush(heap, (policy.state_priority(state, node.depth + 1), ident))
        if solved_id is not None:
            proof = [*prefix, first.tactic, *suffixes[solved_id]]
            audit = verify(task, proof, timeout=audit_timeout)
            if audit.verified:
                status, termination = "verified", "verified"
                for ident in path_to(nodes, solved_id):
                    nodes[ident].on_proof_path = True
            else:
                status, termination = "execution_error", "independent_verification_failed"
    except LeanTimeout:
        termination = "resource_limit:lean_timeout"
    except (LeanError, OSError) as error:
        status, termination = "execution_error", str(error)
    return {
        "status": status,
        "termination": termination,
        "first_action": first.tactic,
        "prefix": prefix,
        "nodes": [n.model_dump() for n in nodes],
        "pools": pools,
        "proof": proof if audit.verified else [],
        "verification": audit.model_dump(),
        "metrics": {
            "attempted_candidates": attempts,
            "expanded_states": expanded,
            "proof_length": len(proof) if audit.verified else 0,
            "suffix_length": len(proof) - len(prefix) if audit.verified else 0,
            "elapsed_s": time.monotonic() - start,
            "lean_execution_s": lean_s,
            "verification_s": audit.elapsed_s,
            "search_s": time.monotonic() - start - audit.elapsed_s,
        },
        "label_policy": (
            "Only verified-vs-verified cost differences are preferences; unresolved is censored"
        ),
    }


def collect_task(ident: str, config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    start = time.monotonic()
    task = get_task(ident)
    if task.split != "development":
        raise ValueError("Forbidden held-out collection")
    chosen = demonstration(ident)
    if chosen is None:
        return {"task_id": ident, "split": task.split, "domain": task.domain, "states": []}, {
            "task_id": ident,
            "status": "no_verified_demonstration",
        }
    trace, source = chosen
    audit = verify(task, trace.proof, timeout=config["audit_timeout_s"])
    if not audit.verified:
        raise ValueError("Development source failed fresh audit")
    rows: list[dict[str, Any]] = []
    with LeanSession(task, timeout=30) as lean:
        state = lean.initial
        prefix: list[str] = []
        for depth, positive in enumerate(trace.proof):
            observations = []
            positive_state = None
            for candidate in generate_candidates(state, 24, frozenset(task.forbidden_lemmas)):
                tick = time.monotonic()
                message = lean.step(state.state_id, candidate.tactic, 3)
                if message["status"] not in ("accepted", "invalid_candidate"):
                    raise LeanError(str(message))
                successor = (
                    ProofState(state_id=message["state_id"], goals=message["goals"])
                    if message["status"] == "accepted"
                    else None
                )
                observations.append(
                    {
                        "candidate": candidate.model_dump(),
                        "status": message["status"],
                        "successor": successor.model_dump() if successor else None,
                        "elapsed_s": time.monotonic() - tick,
                        "error": message.get("error"),
                        "continuation": None,
                        "exploration": "not_selected",
                    }
                )
                if candidate.tactic == positive:
                    positive_state = successor
            if positive_state is None:
                raise ValueError("Verified development path did not replay")
            rows.append(
                {
                    "task_id": ident,
                    "split": "development",
                    "domain": task.domain,
                    "depth": depth,
                    "prefix": list(prefix),
                    "positive_tactic": positive,
                    "state": state.model_dump(),
                    "observations": observations,
                }
            )
            prefix.append(positive)
            state = positive_state
        if state.goals:
            raise ValueError("Development demonstration remains incomplete")
        eligible = [
            r for r in rows if sum(o["status"] == "accepted" for o in r["observations"]) >= 2
        ]
        eligible.sort(
            key=lambda r: (
                -int(
                    sum(
                        o["successor"] is not None and bool(o["successor"]["goals"])
                        for o in r["observations"]
                    )
                    >= 2
                ),
                r["depth"],
            )
        )
        for row in eligible[: config["max_states_per_task"]]:
            valid = [o for o in row["observations"] if o["status"] == "accepted"]
            selected = valid[: config["max_continuations_per_state"]]
            positive = next(o for o in valid if o["candidate"]["tactic"] == row["positive_tactic"])
            if positive not in selected:
                selected[-1] = positive
            for observation in selected:
                first = Candidate.model_validate(observation["candidate"])
                successor = ProofState.model_validate(observation["successor"])
                observation["continuation"] = rollout(
                    lean,
                    task,
                    row["prefix"],
                    first,
                    successor,
                    Budget.model_validate(config["budget"]),
                    config["audit_timeout_s"],
                )
                observation["continuation"]["metrics"]["initial_action_s"] = observation[
                    "elapsed_s"
                ]
                observation["continuation"]["metrics"]["lean_execution_s"] += observation[
                    "elapsed_s"
                ]
                observation["exploration"] = "bounded_rollout"
                if observation["continuation"]["termination"] == "resource_limit:lean_timeout":
                    # A timed-out FIFO request must not be followed by another request.
                    # Remaining alternatives stay unexplored; the timeout is not a negative.
                    return _record(task, source, audit, rows, start, "session_timeout_censored")
    return _record(task, source, audit, rows, start, "collected")


def _record(
    task: Task,
    source: Path,
    audit: Verification,
    rows: list[dict[str, Any]],
    start: float,
    status: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    record = {
        "task_id": task.id,
        "split": task.split,
        "domain": task.domain,
        "demonstration_trace": str(source.relative_to(ROOT)),
        "demonstration_sha256": digest(source),
        "source_verification": audit.model_dump(),
        "states": rows,
    }
    log = {
        "task_id": task.id,
        "status": status,
        "states": len(rows),
        "rollouts": sum(o["continuation"] is not None for r in rows for o in r["observations"]),
        "elapsed_s": time.monotonic() - start,
    }
    return record, log


def collect(destination: Path = DATA) -> dict[str, Any]:
    frozen = check_freeze()
    protocol = json.loads((DIRECTORY / "protocol.json").read_text())
    config = protocol["collection"]
    start = time.monotonic()
    started_at = datetime.now(UTC).isoformat()
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "tasks").mkdir()
    logs = []
    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        futures = {
            pool.submit(collect_task, ident, config): ident
            for ident in frozen["permitted_development_ids"]
        }
        for future in as_completed(futures):
            ident = futures[future]
            try:
                record, log = future.result()
                (destination / "tasks" / f"{ident}.json").write_text(
                    json.dumps(record, indent=2, ensure_ascii=False) + "\n"
                )
            except Exception as error:
                log = {"task_id": ident, "status": "collection_error", "error": str(error)}
            logs.append(log)
            print(ident, log["status"], log.get("rollouts", 0), flush=True)
    logs.sort(key=lambda log: log["task_id"])
    report = {
        **metadata(),
        "started_at": started_at,
        "config": config,
        "freeze_sha256": digest(DIRECTORY / "frozen.json"),
        "tasks": logs,
        "elapsed_s": time.monotonic() - start,
        "task_files": {p.name: digest(p) for p in sorted((destination / "tasks").glob("*.json"))},
    }
    (destination / "collection.json").write_text(json.dumps(report, indent=2) + "\n")
    if any(log["status"] == "collection_error" for log in logs):
        raise RuntimeError("Collection errors retained; resolve before training")
    return report
