"""Actual equal-budget development counterfactuals; censored branches stay unknown."""

from __future__ import annotations

import gzip
import heapq
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from prooflab.adaptive import (
    CanonicalOutcomeRanking,
    HybridProvider,
    candidate_features,
)
from prooflab.adaptive_native import AdaptiveSession
from prooflab.lean import ROOT, LeanError, LeanSession, LeanTimeout, verify
from prooflab.models import Budget, Candidate, ProofState, Task, Trace
from prooflab.phase3_data import digest
from prooflab.phase6_data import DIRECTORY, check_freeze, read_tasks
from prooflab.phase6_execution import run_task
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.search import metadata

DATA = ROOT / "experiments/phase6/development-v1"


def save(path: Path, value: dict[str, Any]) -> None:
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    path.with_suffix(".json.gz").write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))


def continuation(
    lean: LeanSession,
    task: Task,
    prefix: list[str],
    first: Candidate,
    initial: ProofState,
    budget: Budget,
    audit_timeout: float,
) -> dict[str, Any]:
    tick = time.monotonic()
    deadline = tick + budget.timeout_s
    queue: list[tuple[float, int, ProofState, list[str]]] = [(0, 0, initial, [])]
    policy = CanonicalOutcomeRanking()
    provider = HybridProvider()
    attempted, expanded, ident = 1, 0, 0
    steps = []
    queries = []
    proof = []
    audit = None
    termination = "search_exhausted"
    status = "censored"
    try:
        while (
            queue
            and attempted < budget.max_attempts
            and expanded < budget.max_expansions
            and time.monotonic() < deadline
        ):
            _, _, state, suffix = heapq.heappop(queue)
            if not state.goals:
                proof = [*prefix, first.tactic, *suffix]
                break
            if len(suffix) >= budget.max_depth:
                continue
            expanded += 1
            candidates, record = provider.generate(
                lean,
                state,
                budget.max_candidates,
                frozenset(task.forbidden_lemmas),
                min(budget.tactic_timeout_s, max(0.001, deadline - time.monotonic())),
            )
            record["suffix"] = suffix
            queries.append(record)
            for c in policy.rank_candidates(state, candidates):
                if attempted >= budget.max_attempts or time.monotonic() >= deadline:
                    break
                attempted += 1
                message = lean.step(
                    state.state_id,
                    c.tactic,
                    min(budget.tactic_timeout_s, max(0.001, deadline - time.monotonic())),
                )
                steps.append(
                    dict(parent=state.state_id, tactic=c.tactic, response=message, suffix=suffix)
                )
                if message["status"] == "accepted":
                    successor = ProofState(state_id=message["state_id"], goals=message["goals"])
                    if not successor.goals:
                        proof = [*prefix, first.tactic, *suffix, c.tactic]
                        break
                    ident += 1
                    heapq.heappush(
                        queue,
                        (
                            policy.state_priority(successor, len(suffix) + 1),
                            ident,
                            successor,
                            [*suffix, c.tactic],
                        ),
                    )
            if proof:
                break
        if not initial.goals:
            proof = [*prefix, first.tactic]
        if proof:
            audit = verify(task, proof, audit_timeout)
            status = "verified" if audit.verified else "execution_error"
            termination = "verified" if audit.verified else "independent_verification_failed"
        else:
            termination = (
                "resource_limit:attempts"
                if attempted >= budget.max_attempts
                else "resource_limit:expansions"
                if expanded >= budget.max_expansions
                else "resource_limit:wall_time"
                if time.monotonic() >= deadline
                else "search_exhausted"
            )
    except LeanTimeout as e:
        termination = "resource_limit:lean_timeout"
        steps.append(dict(error=str(e)))
    except (LeanError, OSError, ValueError) as e:
        status = "execution_error"
        termination = str(e)
    return dict(
        status=status,
        termination=termination,
        proof=proof if audit and audit.verified else [],
        verification=audit.model_dump() if audit else None,
        metrics=dict(
            attempts=attempted,
            expanded=expanded,
            elapsed_s=time.monotonic() - tick,
            verification_s=audit.elapsed_s if audit else 0,
        ),
        steps=steps,
        queries=queries,
    )


def collect_actions(task: Task, source: Trace | None, config: dict[str, Any]) -> dict[str, Any]:
    states = []
    path = source.proof if source else []
    depths = sorted({0, len(path) - 1})[: config["max_source_states"]] if path else [0]
    with AdaptiveSession(task) as lean:
        state = lean.initial
        prefix: list[str] = []
        for depth in range(max(depths) + 1):
            positive = path[depth] if depth < len(path) else None
            if depth in depths:
                _, query = HybridProvider("fixed").generate(
                    lean, state, 24, frozenset(task.forbidden_lemmas), 2
                )
                pool = {r["candidate"]["tactic"]: r for r in query["pool"]}
                proposals: dict[str, Candidate] = {}
                if positive:
                    proposals[positive] = (
                        Candidate.model_validate(pool[positive]["candidate"])
                        if positive in pool
                        else Candidate(
                            tactic=positive,
                            category="goal",
                            reason="Actual independently verified development source action",
                        )
                    )
                # Prespecified counterfactual alternatives include actual symbolic
                # normalizers and the generic compatible rule implicated historically.
                for tactic in ("simp_all", "apply Or.elim"):
                    if tactic in pool:
                        proposals[tactic] = Candidate.model_validate(pool[tactic]["candidate"])
                for row in sorted(
                    pool.values(),
                    key=lambda r: (
                        r.get("family") != "normalizer",
                        -r.get("deterministic_score", 0),
                        r["candidate"]["tactic"],
                    ),
                ):
                    if len(proposals) >= config["max_executed_per_state"]:
                        break
                    proposals.setdefault(
                        row["candidate"]["tactic"], Candidate.model_validate(row["candidate"])
                    )
                observations: list[dict[str, Any]] = []
                state_record = dict(
                    depth=depth,
                    prefix=list(prefix),
                    state=state.model_dump(),
                    query=query,
                    observations=observations,
                )
                states.append(state_record)
                for c in proposals.values():
                    tick = time.monotonic()
                    try:
                        message = lean.step(state.state_id, c.tactic, 2)
                    except (LeanError, OSError) as interaction_error:
                        observations.append(
                            dict(
                                candidate=c.model_dump(),
                                features=candidate_features(state, c, pool.get(c.tactic, {})),
                                status="interaction_error",
                                label="resource_censored",
                                source_positive=False,
                                successor=None,
                                continuation=None,
                                error=str(interaction_error),
                                elapsed_s=time.monotonic() - tick,
                            )
                        )
                        return dict(
                            task_id=task.id,
                            source_verified=bool(source),
                            states=states,
                            status="session_error_censored",
                        )
                    successor = (
                        ProofState(state_id=message["state_id"], goals=message["goals"])
                        if message["status"] == "accepted"
                        else None
                    )
                    error = message.get("error", "")
                    resource = any(
                        s in error.lower() for s in ("heartbeats", "recursion", "memory", "timeout")
                    )
                    row = pool.get(c.tactic, dict(family="source"))
                    observations.append(
                        dict(
                            candidate=c.model_dump(),
                            features=candidate_features(state, c, row),
                            retrieval=row,
                            status=message["status"],
                            error=error,
                            successor=successor.model_dump() if successor else None,
                            elapsed_s=time.monotonic() - tick,
                            native_heartbeats=message.get("native_heartbeats"),
                            source_positive=c.tactic == positive,
                            label="verified_path"
                            if c.tactic == positive and successor
                            else "accepted_unknown"
                            if successor
                            else "resource_censored"
                            if resource
                            else "rejected_application",
                            continuation=None,
                        )
                    )
                accepted = [o for o in observations if o["successor"]]
                accepted.sort(
                    key=lambda o: (
                        not o["source_positive"],
                        bool(o["successor"]["goals"]),
                        o["retrieval"].get("family") != "normalizer",
                        o["candidate"]["tactic"] != "apply Or.elim",
                        o["candidate"]["tactic"],
                    )
                )
                for obs in accepted[: config["max_continuations_per_state"]]:
                    result = continuation(
                        lean,
                        task,
                        prefix,
                        Candidate.model_validate(obs["candidate"]),
                        ProofState.model_validate(obs["successor"]),
                        Budget.model_validate(config["continuation_budget"]),
                        config["audit_timeout_s"],
                    )
                    obs["continuation"] = result
                    if result["status"] == "verified":
                        obs["label"] = "verified_continuation"
                    elif not obs["source_positive"]:
                        obs["label"] = (
                            "accepted_censored"
                            if result["status"] == "censored"
                            else "tool_error_unknown"
                        )
                    # A timeout invalidates the live session: no later reuse.
                    if result["termination"] == "resource_limit:lean_timeout":
                        return dict(
                            task_id=task.id,
                            source_verified=bool(source),
                            states=states,
                            status="session_timeout_censored",
                        )
            if positive:
                msg = lean.step(state.state_id, positive, 2)
                if msg["status"] != "accepted":
                    raise LeanError("Verified source replay failed")
                state = ProofState(state_id=msg["state_id"], goals=msg["goals"])
                prefix.append(positive)
    return dict(task_id=task.id, source_verified=bool(source), states=states, status="collected")


def collect(destination: Path = DATA, resume: bool = False) -> None:
    frozen = check_freeze()
    config = read_json(DIRECTORY / "protocol.json")["training"]
    destination.mkdir(parents=True, exist_ok=resume)
    (destination / "traces").mkdir(exist_ok=resume)
    (destination / "actions").mkdir(exist_ok=resume)
    provenance = dict(
        **metadata(),
        freeze_sha256=digest(DIRECTORY / "frozen.json"),
        configuration=config,
        evaluation_accessed=False,
        source_sha256={
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                ROOT / "ProofLab/Adaptive.lean",
                *sorted((ROOT / "src/prooflab").glob("adaptive*.py")),
                ROOT / "src/prooflab/phase6_execution.py",
            ]
        },
    )
    old = destination / "provenance.json"
    if old.exists() and read_json(old)["source_sha256"] != provenance["source_sha256"]:
        raise ValueError("Cannot resume changed collection source")
    if not old.exists():
        old.write_text(json.dumps(provenance, indent=2) + "\n")
    families = read_json(DIRECTORY / "families.json")
    tasks = read_tasks("development")
    if set(t.id for t in tasks) != set(frozen["development_ids"]):
        raise ValueError("Development boundary")

    def one(task: Task) -> None:
        source = None
        modes = list(config["modes"])
        random.Random(task.id).shuffle(modes)
        for mode in modes:
            file = destination / "traces" / f"{task.id}--{mode}.json.gz"
            trace = (
                Trace.model_validate(read_json(file))
                if file.exists()
                else run_task(task, mode, Budget.model_validate(config["budget"]))
            )
            if not file.exists():
                trace.metadata.update(family=families[task.id], arm=mode, repeat="0")
                save(file, trace.model_dump())
            if trace.verification.verified and (
                source is None
                or trace.metrics.attempted_candidates < source.metrics.attempted_candidates
            ):
                source = trace
        actionfile = destination / "actions" / f"{task.id}.json.gz"
        if not actionfile.exists():
            try:
                actions = collect_actions(task, source, config)
            except (LeanError, OSError, ValueError) as e:
                actions = dict(task_id=task.id, status="collection_error", error=str(e), states=[])
            save(actionfile, actions)
        print(
            task.id,
            [
                (m, read_json(destination / "traces" / f"{task.id}--{m}.json.gz")["status"])
                for m in modes
            ],
            flush=True,
        )

    order = list(tasks)
    random.Random(606).shuffle(order)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(one, t) for t in order]
        for f in as_completed(futures):
            f.result()
    compact(destination)
    (destination / "action-storage.json").write_text(
        json.dumps(
            {
                p.name: dict(sha256=digest(p), bytes=p.stat().st_size)
                for p in trace_paths(destination / "actions")
            },
            indent=2,
        )
        + "\n"
    )


def preferences(rows: list[dict[str, Any]], applicability: bool = False) -> list[dict[str, Any]]:
    pairs = []
    for theorem in rows:
        for state in theorem["states"]:
            obs = state["observations"]
            local = []
            positives = [o for o in obs if o["label"] in ("verified_path", "verified_continuation")]
            rejected = [o for o in obs if o["label"] == "rejected_application"]
            if applicability:
                positives = [o for o in obs if o["status"] == "accepted"]
            for a in positives:
                for b in rejected[:8]:
                    local.append(
                        (
                            a,
                            b,
                            "accepted_over_rejected" if applicability else "verified_over_rejected",
                        )
                    )
            if not applicability:
                completed = [
                    o
                    for o in obs
                    if o.get("continuation") and o["continuation"]["status"] == "verified"
                ]
                for a in completed:
                    for b in completed:
                        if (
                            a["continuation"]["metrics"]["attempts"]
                            < b["continuation"]["metrics"]["attempts"]
                        ):
                            local.append((a, b, "verified_lower_continuation_cost"))
            for a, b, kind in local:
                names = sorted(set(a["features"]) | set(b["features"]))
                pairs.append(
                    dict(
                        task_id=theorem["task_id"],
                        depth=state["depth"],
                        positive=a["candidate"]["tactic"],
                        negative=b["candidate"]["tactic"],
                        kind=kind,
                        weight=1 / max(1, len(local)),
                        positive_features=a["features"],
                        negative_features=b["features"],
                        difference={
                            n: a["features"].get(n, 0) - b["features"].get(n, 0)
                            for n in names
                            if a["features"].get(n, 0) != b["features"].get(n, 0)
                        },
                    )
                )
    return pairs
