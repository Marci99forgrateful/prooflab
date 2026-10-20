"""Train on observed valid-success cost preferences, never censored negatives."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

from prooflab.continuations import DATA
from prooflab.dataset import get_task
from prooflab.features import dot
from prooflab.lean import ROOT, theorem_source
from prooflab.models import Candidate, ProofState
from prooflab.outcome import MODELS, OutcomeArtifact, save
from prooflab.outcome_features import features
from prooflab.phase3_data import DIRECTORY, check_freeze, digest
from prooflab.search import metadata

Pair = dict[str, Any]


def difference(
    state: ProofState, positive: Candidate, negative: Candidate, mode: str
) -> dict[str, float]:
    a, b = features(state, positive, mode), features(state, negative, mode)
    return {
        name: a.get(name, 0) - b.get(name, 0)
        for name in sorted(a.keys() | b.keys())
        if a.get(name, 0) != b.get(name, 0)
    }


def outcome_pairs(
    records: list[dict[str, Any]], allowed: set[str], mode: str = "full"
) -> list[Pair]:
    result = []
    for record in records:
        if record["task_id"] not in allowed:
            raise ValueError("Forbidden outcome training theorem/split")
        if not record["states"]:
            if get_task(record["task_id"]).split != "development":
                raise ValueError("Forbidden empty held-out record")
            continue  # Explicit unsolved source ledger, with no examples or labels.
        if record.get("split") != "development":
            raise ValueError("Forbidden outcome training theorem/split")
        if not record.get("source_verification", {}).get("verified"):
            if record["states"]:
                raise ValueError("Unaudited source evidence")
            continue
        task = get_task(record["task_id"])
        for row in record["states"]:
            if row["task_id"] != task.id or row["split"] != "development":
                raise ValueError("Mismatched outcome-state identity")
            state = ProofState.model_validate(row["state"])
            successful = []
            for observation in row["observations"]:
                continuation = observation.get("continuation")
                if not continuation or continuation["status"] != "verified":
                    continue  # Invalid, unexplored, censored, or errored is NEVER a losing label.
                if observation["status"] != "accepted" or observation["successor"] is None:
                    raise ValueError("Successful continuation must start from an accepted action")
                audit = continuation["verification"]
                proof = continuation["proof"]
                expected_prefix = [*row["prefix"], observation["candidate"]["tactic"]]
                if (
                    not audit["verified"]
                    or continuation["prefix"] != row["prefix"]
                    or proof[: len(expected_prefix)] != expected_prefix
                    or continuation["first_action"] != observation["candidate"]["tactic"]
                ):
                    raise ValueError("Continuation path/audit mismatch")
                source = theorem_source(task, proof)

                if hashlib.sha256(source.encode()).hexdigest() != audit["source_sha256"]:
                    raise ValueError("Continuation proof hash mismatch")
                if continuation["nodes"][0]["state"] != observation["successor"]:
                    raise ValueError("Actual successor does not match rollout root")
                cost = continuation["metrics"]["attempted_candidates"]
                if cost != len(continuation["nodes"]) or cost < 1:
                    raise ValueError("Unsubstantiated continuation cost")
                successful.append(observation)
            for a, b in itertools.combinations(successful, 2):
                ca = a["continuation"]["metrics"]["attempted_candidates"]
                cb = b["continuation"]["metrics"]["attempted_candidates"]
                if ca == cb:
                    continue
                better, worse = (a, b) if ca < cb else (b, a)
                result.append(
                    {
                        "task_id": task.id,
                        "kind": "verified_valid_cost",
                        "depth": row["depth"],
                        "prefix": row["prefix"],
                        "better": better["candidate"]["tactic"],
                        "worse": worse["candidate"]["tactic"],
                        "better_cost": min(ca, cb),
                        "worse_cost": max(ca, cb),
                        "both_nonterminal": bool(
                            a["successor"]["goals"] and b["successor"]["goals"]
                        ),
                        "difference": difference(
                            state,
                            Candidate.model_validate(better["candidate"]),
                            Candidate.model_validate(worse["candidate"]),
                            mode,
                        ),
                    }
                )
    return result


def applicability_pairs(allowed: set[str], mode: str = "full") -> list[Pair]:
    rows = [
        json.loads(line)
        for line in (ROOT / "experiments/phase2-training/examples.jsonl").read_text().splitlines()
    ]
    result = []
    for row in rows:
        if row["task_id"] not in allowed or row["split"] != "development":
            raise ValueError("Forbidden applicability source")
        if not row["fresh_proof_audit"]["verified"]:
            raise ValueError("Unaudited applicability source")
        positive = next(o for o in row["observations"] if o["label"] == "verified_path_preferred")
        if positive["status"] != "accepted":
            raise ValueError("Invalid positive evidence")
        state = ProofState.model_validate(row["state"])
        for o in row["observations"]:
            if o["label"] != "observed_invalid":
                continue
            if o["status"] != "invalid_candidate":
                raise ValueError("Valid/unresolved alternative mislabeled as invalid")
            result.append(
                {
                    "task_id": row["task_id"],
                    "kind": "applicability",
                    "difference": difference(
                        state,
                        Candidate.model_validate(positive["candidate"]),
                        Candidate.model_validate(o["candidate"]),
                        mode,
                    ),
                }
            )
    return result


def loss(weights: dict[str, float], pairs: list[Pair]) -> float:
    if not pairs:
        raise ValueError("Insufficient actual preference evidence; no evaluation fallback")
    return math.fsum(
        max(0, -dot(weights, p["difference"]))
        + math.log1p(math.exp(-abs(dot(weights, p["difference"]))))
        for p in pairs
    ) / len(pairs)


def fit(
    app: list[Pair],
    outcomes: list[Pair],
    l2: float,
    outcome_weight: float,
    epochs: int = 200,
    learning_rate: float = 0.15,
    seed: int = 0,
) -> dict[str, float]:
    active = [*app, *(outcomes if outcome_weight else [])]
    if not app or (outcome_weight and not outcomes):
        raise ValueError("Missing real training signal")
    names = sorted({name for pair in active for name in pair["difference"]})
    weights = {name: 0.0 for name in names}
    rng = random.Random(seed)
    groups = [(app, 1.0), (outcomes, outcome_weight)]
    for epoch in range(epochs):
        gradient = {n: l2 * w for n, w in weights.items()}
        for pairs, group_weight in groups:
            if not group_weight:
                continue
            order = list(range(len(pairs)))
            rng.shuffle(order)
            for i in order:
                d = pairs[i]["difference"]
                margin = dot(weights, d)
                scale = -group_weight / (len(pairs) * (1 + math.exp(max(-50, min(50, margin)))))
                for name, value in d.items():
                    gradient[name] += scale * value
        step = learning_rate / math.sqrt(1 + epoch / 30)
        for name in names:
            weights[name] -= step * gradient[name]
    return weights


def load_records(data: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    collection = json.loads((data / "collection.json").read_text())
    if collection["freeze_sha256"] != digest(DIRECTORY / "frozen.json"):
        raise ValueError("Collected against a different frozen protocol")
    if any(t["status"] == "collection_error" for t in collection["tasks"]):
        raise ValueError("Resolve retained collection errors before selection")
    records = []
    for filename, sha in collection["task_files"].items():
        path = data / "tasks" / filename
        if path.name != filename or digest(path) != sha:
            raise ValueError("Collected evidence changed")
        records.append(json.loads(path.read_text()))
    return records, collection


def train(data: Path = DATA, destination: Path = MODELS) -> dict[str, Any]:
    started = time.monotonic()
    cpu_started = time.process_time()
    frozen = check_freeze()
    protocol = json.loads((DIRECTORY / "protocol.json").read_text())
    records, collection = load_records(data)
    allowed = set(frozen["permitted_development_ids"])
    validation = set(frozen["validation_ids"])
    app = applicability_pairs(allowed)
    outcomes = outcome_pairs(records, allowed)
    train_app = [p for p in app if p["task_id"] not in validation]
    val_app = [p for p in app if p["task_id"] in validation]
    train_outcomes = [p for p in outcomes if p["task_id"] not in validation]
    val_outcomes = [p for p in outcomes if p["task_id"] in validation]
    config = protocol["hyperparameters"]
    trials = []
    for l2 in config["l2"]:
        for strength in config["outcome_weight"]:
            weights = fit(
                train_app,
                train_outcomes,
                l2,
                strength,
                config["epochs"],
                config["learning_rate"],
                config["seed"],
            )
            trials.append(
                {
                    "l2": l2,
                    "outcome_weight": strength,
                    "validation_outcome_loss": loss(weights, val_outcomes),
                    "validation_applicability_loss": loss(weights, val_app),
                }
            )
    selected = min(
        trials, key=lambda t: (t["validation_outcome_loss"], t["l2"], t["outcome_weight"])
    )
    sources = Counter(
        o["continuation"]["status"]
        if o["continuation"]
        else ("invalid" if o["status"] == "invalid_candidate" else "unexplored_valid")
        for r in records
        for row in r["states"]
        for o in row["observations"]
    )
    provenance = {
        **metadata(),
        "freeze_sha256": digest(DIRECTORY / "frozen.json"),
        "collection_sha256": digest(data / "collection.json"),
        "task_file_hashes": collection["task_files"],
        "training_ids": sorted(allowed),
        "validation_ids": sorted(validation),
        "selection_excludes_validation_tasks": True,
        "final_refit": "All permitted development",
        "evaluation_accessed": False,
        "phase2_weights_used_as_feature": False,
        "trials": trials,
        "selected": selected,
        "config": config,
        "applicability_pairs": len(app),
        "outcome_pairs": len(outcomes),
        "nonterminal_outcome_pairs": sum(p["both_nonterminal"] for p in outcomes),
        "outcome_task_count": len({p["task_id"] for p in outcomes}),
        "training_outcome_pairs": len(train_outcomes),
        "validation_outcome_pairs": len(val_outcomes),
        "observations": dict(sources),
        "label_policy": (
            "Only unequal-cost verified valid alternatives; censored observations never negative"
        ),
        "deployment_features": "Pre-action only; no native successor/lookahead access",
    }
    destination.mkdir(parents=True, exist_ok=True)
    models = {}
    for variant, mode, strength in [
        ("outcome", "full", selected["outcome_weight"]),
        ("applicability_only", "full", 0),
        ("old_features_outcome", "old", selected["outcome_weight"]),
    ]:
        a = app if mode == "full" else applicability_pairs(allowed, "old")
        o = outcomes if mode == "full" else outcome_pairs(records, allowed, "old")
        tick = time.monotonic()
        weights = fit(
            a,
            o,
            selected["l2"],
            strength,
            config["epochs"],
            config["learning_rate"],
            config["seed"],
        )
        fit_s = time.monotonic() - tick
        model = OutcomeArtifact(
            weights=weights,
            feature_mode=mode,
            variant=variant,
            provenance={**provenance, "outcome_weight": strength},
        )
        path = destination / f"{variant}.json"
        save(path, model)
        models[variant] = {
            "sha256": digest(path),
            "parameters": len(weights),
            "fit_wall_s": fit_s,
            "applicability_loss": loss(weights, a),
            "outcome_loss": loss(weights, o),
        }
    report = {
        **provenance,
        "models": models,
        "training_wall_s": time.monotonic() - started,
        "training_cpu_s": time.process_time() - cpu_started,
        "collection_wall_s": collection["elapsed_s"],
    }
    (destination / "training-report.json").write_text(json.dumps(report, indent=2) + "\n")
    with (destination / "outcome-pairs.jsonl").open("w") as out:
        for pair in outcomes:
            out.write(json.dumps(pair, sort_keys=True) + "\n")
    (destination / "frozen.json").write_text(
        json.dumps(
            {
                "models": {v: m["sha256"] for v, m in models.items()},
                "protocol_sha256": digest(DIRECTORY / "protocol.json"),
                "data_sha256": digest(data / "collection.json"),
                "note": "Freeze artifacts before any final evaluation search",
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ("task_file_hashes", "training_ids", "validation_ids")
            },
            indent=2,
        )
    )
    return report
