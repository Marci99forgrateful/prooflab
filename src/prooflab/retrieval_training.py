"""Development-only executed retrieval evidence and deterministic CPU fitting."""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from prooflab.continuations import rollout
from prooflab.dataset import get_task
from prooflab.lean import ROOT, LeanError, verify
from prooflab.models import Budget, Candidate, ProofState
from prooflab.native_retrieval import RetrievalSession
from prooflab.phase3_data import digest
from prooflab.phase5_data import DIRECTORY, check_freeze
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.retrieval import VERSION, TypedProvider, features
from prooflab.search import metadata
from prooflab.training import demonstration

DATA = ROOT / "experiments/phase5/development-v1"
MODELS = ROOT / "models/phase5"


def collect_one(ident: str, config: dict[str, Any]) -> dict[str, Any]:
    task = get_task(ident)
    if task.split != "development":
        raise ValueError("Held-out training forbidden")
    chosen = demonstration(ident)
    if chosen is None:
        return dict(task_id=ident, states=[], status="no_verified_source")
    trace, source = chosen
    audit = verify(task, trace.proof, config["audit_timeout_s"])
    if not audit.verified:
        raise ValueError("Development proof failed independent audit")
    provider = TypedProvider("typed")
    states = []
    selected_depths = set(range(min(2, len(trace.proof)))) | {len(trace.proof) - 1}
    with RetrievalSession(task, timeout=30) as lean:
        state = lean.initial
        prefix: list[str] = []
        for depth, positive in enumerate(trace.proof):
            if depth not in selected_depths:
                msg = lean.step(state.state_id, positive, 3)
                if msg["status"] != "accepted":
                    raise LeanError("Source replay failed")
                state = ProofState(state_id=msg["state_id"], goals=msg["goals"])
                prefix.append(positive)
                continue
            candidates, observation = provider.generate(
                lean, state, 24, frozenset(task.forbidden_lemmas), 2
            )
            pool = {r["candidate"]["tactic"]: r for r in observation["pool"]}
            # Selected availability plus fixed first compatible novelty alternatives;
            # source path action is evidence even when displaced, marked explicitly.
            proposed = {c.tactic: c for c in candidates}
            for row in sorted(observation["pool"], key=lambda r: -r["deterministic_score"]):
                if len(proposed) >= config["max_executed_per_state"] - 1:
                    break
                c = Candidate.model_validate(row["candidate"])
                proposed.setdefault(c.tactic, c)
            proposed.setdefault(
                positive,
                Candidate(
                    tactic=positive,
                    category="goal",
                    reason="Verified source path outside capped pool",
                ),
            )
            observations = []
            successor_positive = None
            for c in proposed.values():
                tick = time.monotonic()
                msg = lean.step(state.state_id, c.tactic, 2)
                if msg["status"] not in ("accepted", "invalid_candidate"):
                    raise LeanError(str(msg))
                successor = (
                    ProofState(state_id=msg["state_id"], goals=msg["goals"])
                    if msg["status"] == "accepted"
                    else None
                )
                info = pool.get(c.tactic, dict(family="original"))
                observations.append(
                    dict(
                        candidate=c.model_dump(),
                        retrieval=info,
                        features=features(state, c, info),
                        status=msg["status"],
                        error=msg.get("error"),
                        successor=successor.model_dump() if successor else None,
                        elapsed_s=time.monotonic() - tick,
                        source_positive=c.tactic == positive,
                        selected_in_search=c.tactic in observation["selected"],
                        continuation=None,
                        label="rejected_application"
                        if successor is None
                        else "verified_path"
                        if c.tactic == positive
                        else "accepted_unknown",
                    )
                )
                if c.tactic == positive:
                    successor_positive = successor
            if successor_positive is None:
                raise LeanError("Positive action failed replay")
            accepted = [o for o in observations if o["successor"] is not None]
            accepted.sort(
                key=lambda o: (
                    not o["source_positive"],
                    bool(o["successor"]["goals"]),
                    -pool.get(o["candidate"]["tactic"], {}).get("deterministic_score", 0),
                )
            )
            for obs in accepted[: config["max_rollouts_per_state"]]:
                cont = rollout(
                    lean,
                    task,
                    list(prefix),
                    Candidate.model_validate(obs["candidate"]),
                    ProofState.model_validate(obs["successor"]),
                    Budget.model_validate(config["rollout_budget"]),
                    config["audit_timeout_s"],
                )
                obs["continuation"] = cont
                if cont["status"] == "verified":
                    obs["label"] = "verified_continuation"
                elif not obs["source_positive"]:
                    obs["label"] = (
                        "accepted_censored"
                        if cont["status"] == "censored"
                        else "tool_error_unknown"
                    )
            states.append(
                dict(
                    depth=depth,
                    prefix=list(prefix),
                    state=state.model_dump(),
                    positive_tactic=positive,
                    retrieval=observation,
                    observations=observations,
                )
            )
            prefix.append(positive)
            state = successor_positive
    return dict(
        task_id=ident,
        split=task.split,
        domain=task.domain,
        source=str(source.relative_to(ROOT)),
        source_sha256=digest(source),
        source_audit=audit.model_dump(),
        states=states,
        status="collected",
    )


def collect(destination: Path = DATA) -> None:
    frozen = check_freeze()
    protocol = read_json(DIRECTORY / "protocol.json")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = dict(
        **metadata(),
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        freeze_sha256=digest(DIRECTORY / "frozen.json"),
        training_ids=frozen["permitted_development_ids"],
        evaluation_accessed=False,
        configuration=protocol["training"],
    )
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(collect_one, i, protocol["training"]): i
            for i in frozen["permitted_development_ids"]
        }
        for future in as_completed(futures):
            row = future.result()
            (destination / "traces" / f"{row['task_id']}.json").write_text(
                json.dumps(row, indent=2) + "\n"
            )
            print(row["task_id"], row["status"], len(row["states"]), flush=True)
    compact(destination)


def pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for theorem in rows:
        for row in theorem["states"]:
            observations = row["observations"]
            positives = [
                o for o in observations if o["label"] in ("verified_path", "verified_continuation")
            ]
            invalid = [o for o in observations if o["status"] == "invalid_candidate"]
            local = []
            for p in positives:
                for n in invalid[:8]:
                    local.append((p, n, "verified_over_rejected_application"))
            verified = [
                o
                for o in positives
                if o["continuation"] and o["continuation"]["status"] == "verified"
            ]
            for p in verified:
                for n in verified:
                    if (
                        p["continuation"]["metrics"]["attempted_candidates"]
                        < n["continuation"]["metrics"]["attempted_candidates"]
                    ):
                        local.append((p, n, "verified_lower_continuation_cost"))
            for p, n, kind in local:
                a, b = p["features"], n["features"]
                names = set(a) | set(b)
                result.append(
                    dict(
                        task_id=theorem["task_id"],
                        depth=row["depth"],
                        positive=p["candidate"]["tactic"],
                        negative=n["candidate"]["tactic"],
                        kind=kind,
                        weight=1 / max(1, len(local)),
                        difference={
                            f: a.get(f, 0) - b.get(f, 0)
                            for f in sorted(names)
                            if a.get(f, 0) != b.get(f, 0)
                        },
                    )
                )
    return result


def loss(examples: list[dict[str, Any]], weights: dict[str, float]) -> float:
    total = sum(float(p["weight"]) for p in examples)
    if not total:
        return 0.0
    return (
        sum(
            float(p["weight"])
            * math.log1p(
                math.exp(
                    max(
                        -40,
                        min(40, -sum(weights.get(n, 0) * v for n, v in p["difference"].items())),
                    )
                )
            )
            for p in examples
        )
        / total
    )


def fit(examples: list[dict[str, Any]], l2: float, epochs: int, rate: float) -> dict[str, float]:
    weights = {n: 0.0 for p in examples for n in p["difference"]}
    total = sum(float(p["weight"]) for p in examples)
    for epoch in range(epochs):
        gradient = {n: l2 * v for n, v in weights.items()}
        for p in examples:
            x = p["difference"]
            score = sum(weights[n] * v for n, v in x.items())
            factor = -p["weight"] / (1 + math.exp(max(-40, min(40, score)))) / total
            for n, v in x.items():
                gradient[n] += factor * v
        step = rate / math.sqrt(1 + epoch / 50)
        for n, g in gradient.items():
            weights[n] -= step * g
    return dict(sorted(weights.items()))


def train(data: Path = DATA, destination: Path = MODELS) -> dict[str, Any]:
    frozen = check_freeze()
    protocol = read_json(DIRECTORY / "protocol.json")
    config = protocol["training"]
    rows = [read_json(p) for p in trace_paths(data / "traces")]
    if {r["task_id"] for r in rows} != set(frozen["permitted_development_ids"]):
        raise ValueError("Development corpus boundary mismatch")
    examples = pairs(rows)
    if (
        len(examples) < config["minimum_preferences"]
        or len({p["task_id"] for p in examples}) < config["minimum_training_theorems"]
    ):
        raise ValueError("Insufficient genuine retrieval evidence; deterministic fallback required")
    train_rows = [p for p in examples if p["task_id"] not in frozen["validation_ids"]]
    validation = [p for p in examples if p["task_id"] in frozen["validation_ids"]]
    trials = []
    for l2 in config["l2"]:
        weights = fit(train_rows, l2, config["epochs"], config["learning_rate"])
        trials.append(
            dict(
                l2=l2,
                train_loss=loss(train_rows, weights),
                validation_loss=loss(validation, weights),
            )
        )
    selected = min(trials, key=lambda t: (t["validation_loss"], t["l2"]))
    weights = fit(examples, selected["l2"], config["epochs"], config["learning_rate"])
    artifact = dict(
        schema_version=1,
        feature_version=VERSION,
        architecture=(
            "linear pairwise logistic CPU ranker, fixed native compatibility "
            "gate; shared symbolic and learned universe/quota"
        ),
        weights=weights,
        l2=selected["l2"],
        epochs=config["epochs"],
        learning_rate=config["learning_rate"],
        seed=0,
        training_ids=frozen["permitted_development_ids"],
        validation_ids=frozen["validation_ids"],
        evaluation_accessed=False,
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        index_sha256=digest(DIRECTORY / "declarations.json"),
        data_provenance_sha256=digest(data / "provenance.json"),
    )
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "retrieval.json").write_text(json.dumps(artifact, indent=2) + "\n")
    (destination / "preferences.json").write_text(json.dumps(examples, indent=2) + "\n")
    report = dict(
        preferences=len(examples),
        cost_preferences=sum(p["kind"] == "verified_lower_continuation_cost" for p in examples),
        theorems=len({p["task_id"] for p in examples}),
        selection_train_pairs=len(train_rows),
        selection_validation_pairs=len(validation),
        trials=trials,
        selected=selected,
        zero_weight_validation_loss=loss(validation, {}),
        feature_count=len(weights),
        labels={
            label: sum(
                o["label"] == label for r in rows for s in r["states"] for o in s["observations"]
            )
            for label in (
                "rejected_application",
                "verified_path",
                "verified_continuation",
                "accepted_unknown",
                "accepted_censored",
                "tool_error_unknown",
            )
        },
        limitations=(
            "Source-path/rejection and bounded-policy evidence, not "
            "mathematical incorrectness. Source traces overrepresent original "
            "actions; generic unification may admit useless branches. No "
            "superiority assumed."
        ),
    )
    (destination / "training-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
