"""CPU logistic completion and success-conditional cost; whole-family validation."""

from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, cast

import numpy as np

from prooflab.adaptive_fit import regression, tree_fit, tree_predict
from prooflab.adaptive_model import mode_features, predict
from prooflab.budget_policy import MODEL_DIR, VERSION, choose, sigmoid
from prooflab.phase3_data import digest
from prooflab.phase7_data import DATA, DIRECTORY, check_freeze, protocol, save
from prooflab.research_io import read_json


def completion_fit(rows: list[dict[str, Any]], nonlinear: bool) -> dict[str, Any]:
    vectors = [mode_features(r["features"], r["mode"]) for r in rows]
    names = sorted({n for f in vectors for n in f})
    x = np.array([[f.get(n, 0) for n in names] for f in vectors])
    y = np.array([r["completion"] for r in rows], dtype=float)
    counts = Counter(r["task_id"] for r in rows)
    w = np.array([1 / counts[r["task_id"]] for r in rows])
    w = w / w.sum() * len(w)
    mean = float(np.clip(np.dot(w, y) / w.sum(), 0.01, 0.99))
    bias = math.log(mean / (1 - mean))
    if not nonlinear:
        coefficients = np.zeros(len(names))
        for epoch in range(800):
            p = 1 / (1 + np.exp(np.clip(-(x @ coefficients + bias), -40, 40)))
            residual = w * (p - y)
            rate = 0.15 / math.sqrt(1 + epoch / 100)
            coefficients -= rate * (x.T @ residual / w.sum() + 0.01 * coefficients)
            bias -= rate * float(residual.sum() / w.sum())
        return dict(
            architecture="L2 logistic completion",
            bias=bias,
            weights={n: float(v) for n, v in zip(names, coefficients, strict=True)},
        )
    scores = np.full(len(y), bias)
    trees = []
    index = {n: i for i, n in enumerate(names)}
    for _ in range(48):
        p = 1 / (1 + np.exp(np.clip(-scores, -40, 40)))
        tree = tree_fit(x, y - p, w, names, 2, 12, list(range(len(names))))
        trees.append(tree)
        scores += 0.15 * tree_predict(tree, x, index)
    return dict(
        architecture="depth-two logistic gradient boosting", bias=bias, rate=0.15, trees=trees
    )


def family_loss(rows: list[dict[str, Any]], model: dict[str, Any], completion: bool) -> float:
    grouped: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        value = predict(model, mode_features(r["features"], r["mode"]))
        error = (
            (sigmoid(value) - r["completion"]) ** 2
            if completion
            else (value - math.log1p(r["conditional_attempts"])) ** 2
        )
        grouped[r["family"]].append(error)
    return float(np.mean([np.mean(v) for v in grouped.values()])) if grouped else float("inf")


def select_margin(
    rows: list[dict[str, Any]], completion: dict[str, Any], cost: dict[str, Any]
) -> tuple[float, list[dict[str, Any]]]:
    groups: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["task_id"], row["source_state"], row["budget_level"])].append(row)
    report = []
    for margin in protocol()["conservative_margins"]:
        losses: dict[str, list[float]] = defaultdict(list)
        for matched in groups.values():
            if len(matched) != 3 or any(r["completion"] is None for r in matched):
                continue
            predictions = {
                r["mode"]: dict(
                    completion_probability=sigmoid(
                        predict(completion, mode_features(r["features"], r["mode"]))
                    ),
                    conditional_attempts=math.expm1(
                        max(0, min(12, predict(cost, mode_features(r["features"], r["mode"]))))
                    ),
                )
                for r in matched
            }
            baseline = matched[0]["baseline"]
            mode, _, _ = choose(
                predictions,
                baseline,
                "conservative",
                round(matched[0]["features"]["remaining_attempts"] * 600),
                margin,
            )
            outcome = next(r["completion"] for r in matched if r["mode"] == mode)
            losses[matched[0]["family"]].append(outcome)
        report.append(
            dict(
                margin=margin,
                validation_completion=float(np.mean([np.mean(v) for v in losses.values()]))
                if losses
                else 0,
                matched_states=sum(map(len, losses.values())),
            )
        )
    chosen = max(report, key=lambda r: (r["validation_completion"], r["margin"]))
    return float(chosen["margin"]), report


def fit(
    destination: Path = MODEL_DIR, data: Path = DATA, root_only: bool = False
) -> dict[str, Any]:
    check_freeze()
    started = time.monotonic()
    rows = cast(list[dict[str, Any]], read_json(data / "rows.json.gz"))
    if digest(data / "rows.json.gz") != read_json(data / "manifest.json")["rows_sha256"]:
        raise ValueError("Collection rows changed")
    for name, sha in read_json(data / "manifest.json")["files"].items():
        if digest(data / name) != sha:
            raise ValueError("Native continuation archive changed")
    usable = [
        r
        for r in rows
        if r["completion"] is not None
        and r["features"] is not None
        and (not root_only or r["source_state"] == 0)
    ]
    val_families = set(protocol()["validation_families"])
    training = [r for r in usable if r["family"] not in val_families]
    validation = [r for r in usable if r["family"] in val_families]
    if not training or not validation:
        raise ValueError("Both training and whole-family validation required")
    candidates = {}
    scores = {}
    for nonlinear in (False, True):
        name = "boosted" if nonlinear else "linear"
        cm = completion_fit(training, nonlinear)
        costs = [
            dict(
                features=mode_features(r["features"], r["mode"]),
                target=math.log1p(r["conditional_attempts"]),
            )
            for r in training
            if r["completion"] == 1
        ]
        if not costs:
            raise ValueError("No independently verified successful training costs")
        cost = regression(costs, nonlinear)
        candidates[name] = (cm, cost)
        scores[name] = dict(
            completion_brier=family_loss(validation, cm, True),
            conditional_log_cost_mse=family_loss(
                [r for r in validation if r["completion"] == 1], cost, False
            ),
        )
    winner_c = min(scores, key=lambda n: (scores[n]["completion_brier"], n != "linear"))
    winner_k = min(scores, key=lambda n: (scores[n]["conditional_log_cost_mse"], n != "linear"))
    cm, cost = candidates[winner_c][0], candidates[winner_k][1]
    margin, margin_report = select_margin(validation, cm, cost)
    artifact = dict(
        feature_version=VERSION,
        evaluation_accessed=False,
        root_only_training=root_only,
        training_ids=sorted({r["task_id"] for r in training}),
        validation_ids=sorted({r["task_id"] for r in validation}),
        completion=cm,
        cost=cost,
        conservative_margin=margin,
        collection_sha256=digest(data / "manifest.json"),
        data_freeze_sha256=digest(DIRECTORY / "frozen.json"),
        label_semantics=protocol()["labels"],
        selection=protocol()["selection"],
    )
    filename = "root-trained.json" if root_only else "selected.json"
    if (destination / filename).exists():
        raise ValueError("Refusing to overwrite selected model")
    save(destination / filename, artifact)
    if not root_only:
        for name, (c, k) in candidates.items():
            save(destination / f"{name}.json", {**artifact, "completion": c, "cost": k})
    report = dict(
        rows=len(rows),
        usable=len(usable),
        training_rows=len(training),
        validation_rows=len(validation),
        training_intermediate_rows=sum(r["source_state"] > 0 for r in training),
        training_successes=sum(r["completion"] == 1 for r in training),
        bounded_noncompletion=sum(r["completion"] == 0 for r in training),
        missing=len(rows) - len([r for r in rows if r["completion"] is not None]),
        validation_scores=scores,
        selected_completion=winner_c,
        selected_cost=winner_k,
        conservative_margins=margin_report,
        selected_margin=margin,
        wall_s=time.monotonic() - started,
        root_only_training=root_only,
        evaluation_accessed=False,
    )
    save(
        destination / ("root-training-report.json" if root_only else "training-report.json"), report
    )
    print(report, flush=True)
    return report
