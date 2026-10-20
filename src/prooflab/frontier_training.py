"""Deterministic supervised state-cost training, strictly development-only."""

from __future__ import annotations

import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any, cast

from prooflab.continuations import DATA
from prooflab.dataset import get_task
from prooflab.frontier import MODELS, FrontierArtifact, Mode, state_features
from prooflab.lean import ROOT, theorem_source
from prooflab.models import ProofState
from prooflab.phase3_data import digest
from prooflab.phase4_data import DIRECTORY, check_freeze
from prooflab.search import metadata


def examples(allowed: set[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    collection = json.loads((DATA / "collection.json").read_text())
    rows = []
    ledger: Counter[str] = Counter()
    for path in sorted((DATA / "tasks").glob("*.json")):
        record = json.loads(path.read_text())
        ident = record["task_id"]
        if ident not in allowed or get_task(ident).split != "development":
            raise ValueError("Forbidden frontier training theorem")
        if not record["states"]:
            ledger["empty_development_source"] += 1
            continue
        if not record["source_verification"]["verified"] or record["split"] != "development":
            raise ValueError("Unaudited source trajectory")
        for row in record["states"]:
            parent = ProofState.model_validate(row["state"])
            for observation in row["observations"]:
                continuation = observation.get("continuation")
                if not continuation:
                    ledger[observation["status"]] += 1
                    continue
                ledger[continuation["status"]] += 1
                if continuation["status"] != "verified":
                    continue  # Never invent a numerical target for censored/unresolved evidence.
                proof = continuation["proof"]
                audit = continuation["verification"]
                prefix = [*row["prefix"], observation["candidate"]["tactic"]]
                import hashlib

                if (
                    not audit["verified"]
                    or proof[: len(prefix)] != prefix
                    or audit["source_sha256"]
                    != hashlib.sha256(theorem_source(get_task(ident), proof).encode()).hexdigest()
                    or continuation["nodes"][0]["state"] != observation["successor"]
                    or observation["status"] != "accepted"
                ):
                    raise ValueError("Unsubstantiated state-cost target")
                state = ProofState.model_validate(observation["successor"])
                cost = continuation["metrics"]["attempted_candidates"] - 1
                if cost != len(continuation["nodes"]) - 1 or cost < 0:
                    raise ValueError("Continuation cost inconsistent with actual transitions")
                if not state.goals:
                    ledger["terminal_excluded"] += 1
                    continue  # A solved state is verified immediately, never queued for expansion.
                rows.append(
                    dict(
                        task_id=ident,
                        split="development",
                        parent=parent.model_dump(),
                        state=state.model_dump(),
                        depth=len(prefix),
                        cost=cost,
                        target=math.log1p(cost),
                        prefix=prefix,
                        source=str(path.relative_to(ROOT)),
                        source_sha256=digest(path),
                    )
                )
    if not collection or not rows:
        raise ValueError("Missing genuine development trajectories")
    return rows, dict(ledger)


def encode(row: dict[str, Any], mode: Mode) -> dict[str, float]:
    return state_features(
        ProofState.model_validate(row["state"]),
        row["depth"],
        ProofState.model_validate(row["parent"]),
        mode,
    )


def fit(
    rows: list[dict[str, Any]],
    mode: Mode,
    l2: float,
    epochs: int = 400,
    learning_rate: float = 0.08,
) -> FrontierArtifact:
    fs = [encode(r, mode) for r in rows]
    names = sorted(fs[0])
    means = {n: 0.0 if n == "bias" else statistics.mean(f[n] for f in fs) for n in names}
    scales = {
        n: max(1.0e-4, statistics.pstdev(f[n] for f in fs)) if n != "bias" else 1.0 for n in names
    }
    x = [[(f[n] - means[n]) / scales[n] for n in names] for f in fs]
    counts = Counter(r["task_id"] for r in rows)
    factors = [1 / (len(counts) * counts[r["task_id"]]) for r in rows]
    weights = [0.0] * len(names)
    for epoch in range(epochs):
        gradient = [l2 * w if n != "bias" else 0.0 for n, w in zip(names, weights, strict=True)]
        for values, row, factor in zip(x, rows, factors, strict=True):
            error = sum(w * v for w, v in zip(weights, values, strict=True)) - row["target"]
            for j, v in enumerate(values):
                gradient[j] += factor * error * v
        rate = learning_rate / math.sqrt(1 + epoch / 30)
        weights = [w - rate * g for w, g in zip(weights, gradient, strict=True)]
    return FrontierArtifact(
        mode=mode,
        weights=dict(zip(names, weights, strict=True)),
        means=means,
        scales=scales,
        depth_penalty=0.15,
        provenance={},
    )


def mse(model: FrontierArtifact, rows: list[dict[str, Any]]) -> float:
    per_task: dict[str, list[float]] = {}
    for row in rows:
        f = encode(row, model.mode)
        estimate = math.fsum(
            w * (f[n] - model.means[n]) / model.scales[n] for n, w in model.weights.items()
        )
        per_task.setdefault(row["task_id"], []).append((estimate - row["target"]) ** 2)
    return statistics.mean(statistics.mean(errors) for errors in per_task.values())


def train(destination: Path = MODELS) -> dict[str, Any]:
    if destination.exists():
        raise ValueError(
            "Use a new frontier model destination; frozen artifacts cannot be overwritten"
        )
    frozen = check_freeze()
    protocol = json.loads((DIRECTORY / "protocol.json").read_text())
    config = protocol["models"]
    start, cpu = time.monotonic(), time.process_time()
    rows, ledger = examples(set(frozen["permitted_development_ids"]))
    validation_ids = set(frozen["validation_ids"])
    training = [r for r in rows if r["task_id"] not in validation_ids]
    validation = [r for r in rows if r["task_id"] in validation_ids]
    grid = []
    for mode in config["modes"]:
        for l2 in config["l2"]:
            model = fit(training, cast(Mode, mode), l2, config["epochs"], config["learning_rate"])
            grid.append(
                dict(
                    mode=mode,
                    l2=l2,
                    validation_mse=mse(model, validation),
                    train_mse=mse(model, training),
                )
            )
    selected = min(grid, key=lambda r: (r["validation_mse"], r["mode"], r["l2"]))
    linear = min([r for r in grid if r["mode"] == "linear"], key=lambda r: r["validation_mse"])
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, choice in [("selected", selected), ("linear", linear)]:
        model = fit(
            rows,
            cast(Mode, choice["mode"]),
            choice["l2"],
            config["epochs"],
            config["learning_rate"],
        )
        model.provenance = dict(
            training_ids=sorted({r["task_id"] for r in rows}),
            evaluation_accessed=False,
            objective=config["objective"],
            selection=choice,
            protocol_sha256=digest(DIRECTORY / "protocol.json"),
            collection_sha256=digest(DATA / "collection.json"),
            source_hashes={r["source"]: r["source_sha256"] for r in rows},
            training_mse=mse(model, rows),
            ledger=ledger,
        )
        path = destination / f"{name}.json"
        path.write_text(model.model_dump_json(indent=2) + "\n")
        hashes[name] = digest(path)
    (destination / "examples.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    report = dict(
        metadata=metadata(),
        training_rows=len(training),
        validation_rows=len(validation),
        final_rows=len(rows),
        theorems=len({r["task_id"] for r in rows}),
        ledger=ledger,
        grid=grid,
        selected=selected,
        linear=linear,
        wall_s=time.monotonic() - start,
        cpu_s=time.process_time() - cpu,
        models=hashes,
    )
    (destination / "training-report.json").write_text(json.dumps(report, indent=2) + "\n")
    (destination / "frozen.json").write_text(
        json.dumps(
            dict(
                models=hashes,
                protocol_sha256=digest(DIRECTORY / "protocol.json"),
                examples_sha256=digest(destination / "examples.jsonl"),
                report_sha256=digest(destination / "training-report.json"),
            ),
            indent=2,
        )
        + "\n"
    )
    return report
