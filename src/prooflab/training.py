"""Development-only Lean data collection and deterministic CPU pairwise learning."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from prooflab.candidates import generate_candidates
from prooflab.dataset import get_task
from prooflab.features import dot, extract_features
from prooflab.lean import ROOT, LeanSession, theorem_source, verify
from prooflab.learning import DEFAULT_MODEL, ModelArtifact, save_model
from prooflab.models import Candidate, ProofState, Trace
from prooflab.search import metadata
from prooflab.splits import PHASE2, check_freeze

DATA_DIR = ROOT / "experiments/phase2-training"
Pair = dict[str, float]


def demonstration(ident: str) -> tuple[Trace, Path] | None:
    task = get_task(ident)
    if task.split != "development":
        raise ValueError("Held-out data cannot enter collection")
    options = []
    for algorithm in ("bfs", "best_first"):
        path = ROOT / f"experiments/phase1-v3/traces/{ident}--{algorithm}.json"
        trace = Trace.model_validate_json(path.read_text())
        if trace.status == "verified" and trace.verification.verified:
            source = theorem_source(trace.task, trace.proof)
            if hashlib.sha256(source.encode()).hexdigest() != trace.verification.source_sha256:
                raise ValueError("Source/audit hash mismatch")
            options.append((trace, path))
    return (
        min(options, key=lambda item: (len(item[0].proof), item[0].algorithm)) if options else None
    )


def collect_task(ident: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    task = get_task(ident)
    chosen = demonstration(ident)
    if chosen is None:
        return [], {"task_id": ident, "status": "no_verified_development_demonstration"}
    trace, path = chosen
    audit = verify(task, trace.proof, timeout=30)
    if not audit.verified:
        raise ValueError(f"Fresh training demonstration audit failed: {ident}: {audit.error}")
    rows: list[dict[str, Any]] = []
    with LeanSession(task, timeout=30) as lean:
        state = lean.initial
        for depth, positive in enumerate(trace.proof):
            candidates = generate_candidates(state, 24, frozenset(task.forbidden_lemmas))
            if positive not in {c.tactic for c in candidates}:
                raise ValueError("Demonstration action absent from unchanged generator")
            observations = []
            successor = None
            for candidate in candidates:
                tick = time.monotonic()
                result = lean.step(state.state_id, candidate.tactic, 3)
                if result["status"] not in ("accepted", "invalid_candidate"):
                    raise ValueError("Training observation was not a completed Lean attempt")
                observations.append(
                    {
                        "candidate": candidate.model_dump(),
                        "status": result["status"],
                        "error": result.get("error"),
                        "elapsed_s": time.monotonic() - tick,
                        "label": "verified_path_preferred"
                        if candidate.tactic == positive
                        else "observed_invalid"
                        if result["status"] == "invalid_candidate"
                        else "valid_alternative_unlabeled",
                    }
                )
                if candidate.tactic == positive:
                    if result["status"] != "accepted":
                        raise ValueError("Positive action did not execute in actual Lean")
                    successor = ProofState(state_id=result["state_id"], goals=result["goals"])
            rows.append(
                {
                    "task_id": ident,
                    "split": "development",
                    "domain": task.domain,
                    "depth": depth,
                    "state": state.model_dump(),
                    "positive_tactic": positive,
                    "observations": observations,
                    "demonstration_trace": str(path.relative_to(ROOT)),
                    "demonstration_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "fresh_proof_audit": audit.model_dump(),
                }
            )
            assert successor is not None
            state = successor
        if state.goals:
            raise ValueError("Replayed development proof did not solve all goals")
    return rows, {
        "task_id": ident,
        "status": "collected",
        "states": len(rows),
        "tactic_calls": sum(len(r["observations"]) for r in rows),
    }


def collect_data(destination: Path = DATA_DIR) -> None:
    frozen = check_freeze()
    destination.mkdir(parents=True, exist_ok=False)
    rows = []
    logs = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(collect_task, ident): ident for ident in frozen["permitted_development_ids"]
        }
        for future in as_completed(futures):
            ident = futures[future]
            try:
                examples, log = future.result()
                rows.extend(examples)
            except Exception as error:
                log = {"task_id": ident, "status": "collection_error", "error": str(error)}
            logs.append(log)
            print(ident, log["status"], flush=True)
    rows.sort(key=lambda row: (row["task_id"], row["depth"]))
    logs.sort(key=lambda row: row["task_id"])
    with (destination / "examples.jsonl").open("w") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    (destination / "collection.json").write_text(
        json.dumps(
            {
                **metadata(),
                "freeze_sha256": hashlib.sha256((PHASE2 / "frozen.json").read_bytes()).hexdigest(),
                "allowed_ids": frozen["permitted_development_ids"],
                "tasks": logs,
                "states": len(rows),
                "positive_source": "shortest independently verified BFS/best-first development "
                "proof; deterministic tie-break",
                "label_policy": "only actual Lean-rejected siblings are contrasts; "
                "valid alternatives unlabeled; timeouts never negatives",
                "examples_sha256": hashlib.sha256(
                    (destination / "examples.jsonl").read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    if any(log["status"] == "collection_error" for log in logs):
        raise RuntimeError(
            "Incomplete collection; inspect retained collection errors before training"
        )


def training_pairs(rows: list[dict[str, Any]]) -> list[Pair]:
    frozen = check_freeze()
    allowed = set(frozen["permitted_development_ids"])
    pairs = []
    for row in rows:
        if row["task_id"] not in allowed or row["split"] != "development":
            raise ValueError("Forbidden training/held-out data")
        state = ProofState.model_validate(row["state"])
        observations = row["observations"]
        positives = [x for x in observations if x["label"] == "verified_path_preferred"]
        if len(positives) != 1 or positives[0]["status"] != "accepted":
            raise ValueError("Positive evidence must be an accepted, verified-path action")
        if not row["fresh_proof_audit"]["verified"]:
            raise ValueError("Unverified demonstration")
        positive = extract_features(state, Candidate.model_validate(positives[0]["candidate"]))
        for alternative in observations:
            if alternative["label"] != "observed_invalid":
                continue
            if alternative["status"] != "invalid_candidate":
                raise ValueError("Unknown/valid alternative was mislabeled as invalid")
            negative = extract_features(state, Candidate.model_validate(alternative["candidate"]))
            difference = {
                name: positive.get(name, 0) - negative.get(name, 0)
                for name in sorted(positive.keys() | negative.keys())
            }
            pairs.append({name: value for name, value in difference.items() if value})
    return pairs


def pair_loss(weights: dict[str, float], pairs: list[Pair]) -> float:
    if not pairs:
        raise ValueError("No permitted pairwise evidence")
    return math.fsum(
        max(0, -dot(weights, pair)) + math.log1p(math.exp(-abs(dot(weights, pair))))
        for pair in pairs
    ) / len(pairs)


def fit(
    pairs: list[Pair], l2: float, epochs: int = 200, learning_rate: float = 0.15, seed: int = 0
) -> dict[str, float]:
    if not pairs:
        raise ValueError("Cannot train without observed data")
    names = sorted({name for pair in pairs for name in pair})
    weights = {name: 0.0 for name in names}
    # Full-batch gradient descent: deterministic CPU floats, no BLAS or hidden GPU path.
    # The seed fixes permutation even though full-batch aggregation is essentially invariant.
    rng = random.Random(seed)
    order = list(range(len(pairs)))
    for epoch in range(epochs):
        rng.shuffle(order)
        gradient = {name: l2 * weights[name] for name in names}
        for index in order:
            pair = pairs[index]
            margin = dot(weights, pair)
            scale = -1 / (1 + math.exp(max(-50, min(50, margin)))) / len(pairs)
            for name, value in pair.items():
                gradient[name] += scale * value
        step = learning_rate / math.sqrt(1 + epoch / 30)
        for name in names:
            weights[name] -= step * gradient[name]
    return weights


def train(data: Path = DATA_DIR, model_path: Path = DEFAULT_MODEL) -> dict[str, Any]:
    frozen = check_freeze()
    protocol = json.loads((PHASE2 / "protocol.json").read_text())
    collection = json.loads((data / "collection.json").read_text())
    if (
        hashlib.sha256((data / "examples.jsonl").read_bytes()).hexdigest()
        != collection["examples_sha256"]
    ):
        raise ValueError("Collected training evidence changed")
    if (
        hashlib.sha256((PHASE2 / "frozen.json").read_bytes()).hexdigest()
        != collection["freeze_sha256"]
    ):
        raise ValueError("Collection used a different frozen split")
    if any(task["status"] == "collection_error" for task in collection["tasks"]):
        raise ValueError("Resolve collection errors before model selection")
    rows = [json.loads(line) for line in (data / "examples.jsonl").read_text().splitlines()]
    train_ids = set(frozen["selection_train_ids"])
    val_ids = set(frozen["selection_validation_ids"])
    train_pairs = training_pairs([r for r in rows if r["task_id"] in train_ids])
    val_pairs = training_pairs([r for r in rows if r["task_id"] in val_ids])
    config = protocol["hyperparameters"]
    trials = []
    for l2 in config["l2"]:
        weights = fit(train_pairs, l2, config["epochs"], config["learning_rate"], config["seed"])
        trials.append(
            {
                "l2": l2,
                "validation_pair_loss": pair_loss(weights, val_pairs),
                "training_pair_loss": pair_loss(weights, train_pairs),
            }
        )
    selected = min(trials, key=lambda trial: (trial["validation_pair_loss"], trial["l2"]))
    pairs = training_pairs(rows)
    weights = fit(pairs, selected["l2"], config["epochs"], config["learning_rate"], config["seed"])
    if all(abs(value) < 1e-12 for value in weights.values()):
        raise ValueError("Training produced no learned coefficients")
    provenance = {
        **metadata(),
        "evaluation_sha256": frozen["evaluation_sha256"],
        "protocol_sha256": frozen["protocol_sha256"],
        "training_data_sha256": hashlib.sha256((data / "examples.jsonl").read_bytes()).hexdigest(),
        "training_task_ids": sorted({r["task_id"] for r in rows}),
        "selection_train_ids": sorted(train_ids),
        "selection_validation_ids": sorted(val_ids),
        "evaluation_accessed_during_selection": False,
        "selection_trials": trials,
        "selected_l2": selected["l2"],
        "epochs": config["epochs"],
        "learning_rate": config["learning_rate"],
        "seed": config["seed"],
        "pair_count": len(pairs),
        "state_count": len(rows),
        "label_policy": "verified-path > observed invalid; valid/unexecuted alternatives unlabeled",
        "frontier": "same handcrafted state-priority as best_first; no learned value function",
        "full_refit_pair_loss": pair_loss(weights, pairs),
        "zero_weight_pair_loss": pair_loss({}, pairs),
    }
    save_model(model_path, ModelArtifact(weights=weights, provenance=provenance))
    report = {
        **provenance,
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "model_path": str(model_path),
        "parameter_count": len(weights),
        "selection_training_pairs": len(train_pairs),
        "selection_validation_pairs": len(val_pairs),
    }
    (data / "training-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report
