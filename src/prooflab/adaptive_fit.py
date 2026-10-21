"""Reproducible full-batch linear and histogram-CART gradient boosting on CPU.

Training uses NumPy solely for bounded tabular arithmetic; inference is stdlib.
Trees fit pairwise logistic pseudo-responses, not finite-search-failure labels.
"""

from __future__ import annotations

import json
import math
import random
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from prooflab.adaptive import context_features
from prooflab.adaptive_model import MODELS, VERSION, mode_features, predict
from prooflab.adaptive_training import DATA, preferences
from prooflab.lean import ROOT
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.phase6_data import DIRECTORY, check_archive, check_freeze
from prooflab.research_io import read_json, trace_paths
from prooflab.retrieval_training import fit as linear_fit


def tree_fit(
    x: Any, y: Any, w: Any, names: list[str], depth: int, min_leaf: int, feature_indices: list[int]
) -> dict[str, Any]:
    total = float(w.sum())
    value = float(np.dot(y, w) / max(1e-12, total))
    result: dict[str, Any] = dict(value=value, observations=len(y))
    if depth == 0 or len(y) < 2 * min_leaf or float(np.ptp(y)) < 1e-12:
        return result
    best_gain = -1e-12
    best = None
    for col in feature_indices:
        values = x[:, col]
        unique = np.unique(values)
        if len(unique) < 2:
            continue
        cuts = (
            unique[:-1]
            if len(unique) <= 8
            else np.unique(np.quantile(values, [0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9]))
        )
        for threshold in cuts:
            mask = values <= threshold
            count = int(mask.sum())
            if count < min_leaf or len(y) - count < min_leaf:
                continue
            wl = float(w[mask].sum())
            wr = total - wl
            if min(wl, wr) <= 1e-12:
                continue
            sl = float(np.dot(w[mask], y[mask]))
            sr = float(np.dot(w[~mask], y[~mask]))
            gain = sl * sl / wl + sr * sr / wr - total * value * value
            if gain > best_gain:
                best_gain = gain
                best = (col, float(threshold), mask)
    if best is None:
        return result
    col, threshold, mask = best
    result.update(
        feature=names[col],
        threshold=threshold,
        gain=best_gain,
        left=tree_fit(x[mask], y[mask], w[mask], names, depth - 1, min_leaf, feature_indices),
        right=tree_fit(x[~mask], y[~mask], w[~mask], names, depth - 1, min_leaf, feature_indices),
    )
    return result


def tree_predict(tree: dict[str, Any], x: Any, index: dict[str, int]) -> Any:
    if "feature" not in tree:
        return np.full(len(x), tree["value"])
    mask = x[:, index[tree["feature"]]] <= tree["threshold"]
    out = np.empty(len(x))
    out[mask] = tree_predict(tree["left"], x[mask], index)
    out[~mask] = tree_predict(tree["right"], x[~mask], index)
    return out


def boosted_pairs(
    pairs: list[dict[str, Any]],
    depth: int,
    iterations: int,
    seed: int,
    rate: float = 0.1,
    min_leaf: int = 12,
) -> dict[str, Any]:
    vectors: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    a = []
    b = []
    weights = []
    for pair in pairs:
        indices = []
        for role in ("positive_features", "negative_features"):
            f = pair[role]
            key = json.dumps(f, sort_keys=True)
            if key not in vectors:
                vectors[key] = len(rows)
                rows.append(f)
            indices.append(vectors[key])
        a.append(indices[0])
        b.append(indices[1])
        weights.append(pair["weight"])
    names = sorted({n for f in rows for n in f})
    index = {n: i for i, n in enumerate(names)}
    x = np.array([[f.get(n, 0) for n in names] for f in rows])
    aa = np.array(a)
    bb = np.array(b)
    pw = np.array(weights)
    counts = np.bincount(
        np.concatenate([aa, bb]), weights=np.concatenate([pw, pw]), minlength=len(rows)
    )
    score = np.zeros(len(rows))
    trees = []
    rng = random.Random(seed)
    for _ in range(iterations):
        gradient = pw / (1 + np.exp(np.clip(score[aa] - score[bb], -40, 40)))
        total = np.bincount(aa, weights=gradient, minlength=len(rows)) - np.bincount(
            bb, weights=gradient, minlength=len(rows)
        )
        residual = total / np.maximum(counts, 1e-12)
        columns = sorted(
            rng.sample(range(len(names)), min(len(names), max(2, int(len(names) * 0.85))))
        )
        tree = tree_fit(x, residual, counts, names, depth, min_leaf, columns)
        score += rate * tree_predict(tree, x, index)
        trees.append(tree)
    return dict(
        architecture="pairwise logistic gradient boosting with histogram CART",
        depth=depth,
        iterations=iterations,
        rate=rate,
        min_leaf=min_leaf,
        seed=seed,
        feature_names=names,
        trees=trees,
        bias=0,
    )


def regression(
    rows: list[dict[str, Any]], nonlinear: bool, depth: int = 2, iterations: int = 48, seed: int = 0
) -> dict[str, Any]:
    names = sorted({n for r in rows for n in r["features"]})
    x = np.array([[r["features"].get(n, 0) for n in names] for r in rows])
    y = np.array([r["target"] for r in rows])
    w = np.ones(len(rows))
    bias = float(y.mean())
    if not nonlinear:
        weights = np.zeros(len(names))
        for epoch in range(500):
            gradient = x.T @ (x @ weights + bias - y) / len(y) + 0.1 * weights
            weights -= 0.1 / math.sqrt(1 + epoch / 50) * gradient
        return dict(
            architecture="ridge linear conditional log continuation cost",
            bias=bias,
            weights={n: float(v) for n, v in zip(names, weights, strict=True)},
        )
    score = np.full(len(y), bias)
    trees = []
    rng = random.Random(seed)
    index = {n: i for i, n in enumerate(names)}
    for _ in range(iterations):
        columns = sorted(
            rng.sample(range(len(names)), min(len(names), max(2, int(len(names) * 0.85))))
        )
        tree = tree_fit(x, y - score, w, names, depth, 12, columns)
        score += 0.1 * tree_predict(tree, x, index)
        trees.append(tree)
    return dict(
        architecture="gradient boosted conditional log continuation cost",
        bias=bias,
        rate=0.1,
        depth=depth,
        iterations=iterations,
        seed=seed,
        feature_names=names,
        trees=trees,
    )


def pair_loss(pairs: list[dict[str, Any]], model: dict[str, Any]) -> float:
    return float(
        sum(
            p["weight"]
            * math.log1p(
                math.exp(
                    max(
                        -40,
                        min(
                            40,
                            predict(model, p["negative_features"])
                            - predict(model, p["positive_features"]),
                        ),
                    )
                )
            )
            for p in pairs
        )
        / sum(p["weight"] for p in pairs)
    )


def mse(rows: list[dict[str, Any]], model: dict[str, Any]) -> float:
    return float(
        sum((predict(model, r["features"]) - r["target"]) ** 2 for r in rows) / max(1, len(rows))
    )


def train(data: Path = DATA, output: Path = MODELS) -> dict[str, Any]:
    start = time.monotonic()
    frozen = check_freeze()
    check_archive(data)
    config = read_json(DIRECTORY / "protocol.json")["training"]
    validation = set(frozen["validation_ids"])
    if output.exists():
        raise ValueError("Refuse to overwrite model artifacts")
    output.mkdir(parents=True)
    actions = [read_json(p) for p in trace_paths(data / "actions")]
    if {r["task_id"] for r in actions} != set(frozen["development_ids"]):
        raise ValueError("Incomplete or contaminated development collection")
    examples = preferences(actions)
    applicable = preferences(actions, True)
    training = [p for p in examples if p["task_id"] not in validation]
    valid = [p for p in examples if p["task_id"] in validation]
    if len(training) < 50 or len(valid) < 10:
        raise ValueError("Insufficient family-separated preferences; retain deterministic policy")
    candidates: list[dict[str, Any]] = []
    for l2 in config["linear_l2"]:
        model = dict(
            architecture="pairwise logistic linear",
            weights=linear_fit(training, l2, config["linear_epochs"], config["linear_rate"]),
            l2=l2,
        )
        candidates.append(
            dict(
                kind="linear",
                configuration=dict(l2=l2),
                model=model,
                validation_loss=pair_loss(valid, model),
            )
        )
    linear = min(candidates, key=lambda x: x["validation_loss"])
    for depth in config["tree_depths"]:
        for iterations in config["tree_iterations"]:
            losses = []
            for seed in config["seeds"]:
                m = boosted_pairs(
                    training, depth, iterations, seed, config["tree_rate"], config["min_leaf"]
                )
                losses.append(pair_loss(valid, m))
            candidates.append(
                dict(
                    kind="boosted",
                    configuration=dict(depth=depth, iterations=iterations),
                    validation_loss=sum(losses) / len(losses),
                    seed_losses=losses,
                )
            )
    winner = min(candidates, key=lambda x: (x["validation_loss"], x["kind"]))
    # Selector fitting is a later stage using exactly matched fixed-mode searches
    # with this fitted relevance model. A provisional artifact cannot run adaptive
    # evaluation; it can only be used under an explicitly forced development mode.
    selected_selector = dict(architecture="unfitted; forced development mode only", bias=0)
    # Keep the relevance expert trained on the 120 selection-training tasks.
    # Refitting it on the 40 validation families before mode-cost collection
    # would contaminate downstream family-level selector validation.
    linear_model = linear["model"]
    selected = (
        linear_model
        if winner["kind"] == "linear"
        else boosted_pairs(
            training,
            **winner["configuration"],
            seed=0,
            rate=config["tree_rate"],
            min_leaf=config["min_leaf"],
        )
    )
    app_model = dict(
        architecture="pairwise logistic applicability only",
        weights=linear_fit(
            [p for p in applicable if p["task_id"] not in validation],
            linear["configuration"]["l2"],
            config["linear_epochs"],
            config["linear_rate"],
        ),
    )
    provenance = dict(
        feature_version=VERSION,
        selector_ready=False,
        selector_protocol_sha256=digest(DIRECTORY / "selector-protocol.json"),
        evaluation_accessed=False,
        training_ids=frozen["training_ids"],
        permitted_development_ids=frozen["development_ids"],
        validation_ids=frozen["validation_ids"],
        validation_families=frozen["validation_families"],
        freeze_sha256=digest(DIRECTORY / "frozen.json"),
        collection_sha256=digest(data / "provenance.json"),
        training_trace_manifest_sha256=digest(data / "trace-storage.json"),
        training_action_manifest_sha256=digest(data / "action-storage.json"),
        fit_source_sha256=digest(ROOT / "src/prooflab/adaptive_fit.py"),
        selection=(
            "family-level validation; relevance retains 120-task selection-training fit; "
            "seed 0 fixed; seed sensitivity recorded"
        ),
        selector_semantics=(
            "log attempt cost conditional on independently verified equal-budget "
            "development completion; censored modes not mathematical negatives; "
            "missingness/selection bias explicit"
        ),
    )
    for name, model in [
        ("learned", selected),
        ("linear", linear_model),
        ("applicability", app_model),
    ]:
        (output / f"{name}.json").write_text(
            json.dumps(
                dict(**provenance, relevance=model, selector=selected_selector),
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    # Seed robustness retained, never selected by final-test results.
    if winner["kind"] == "boosted":
        for seed in (1, 2):
            m = boosted_pairs(
                training,
                **winner["configuration"],
                seed=seed,
                rate=config["tree_rate"],
                min_leaf=config["min_leaf"],
            )
            (output / f"learned-seed{seed}.json").write_text(
                json.dumps(
                    dict(**provenance, relevance=m, selector=selected_selector),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
    report = dict(
        **provenance,
        development_tasks=len(actions),
        contributing_tasks=len({p["task_id"] for p in examples}),
        source_states=sum(len(t["states"]) for t in actions),
        labels=dict(
            Counter(o["label"] for t in actions for s in t["states"] for o in s["observations"])
        ),
        preferences=len(examples),
        preference_kinds=dict(Counter(p["kind"] for p in examples)),
        final_relevance_training_tasks=len({p["task_id"] for p in training}),
        final_relevance_training_pairs=len(training),
        training_preference_kinds=dict(Counter(p["kind"] for p in training)),
        selection_train_pairs=len(training),
        selection_validation_pairs=len(valid),
        validation_zero_loss=math.log(2),
        candidates=[{k: v for k, v in c.items() if k != "model"} for c in candidates],
        winner={k: v for k, v in winner.items() if k != "model"},
        selector_candidates=[],
        mode_outcomes={},
        verified_selector_rows=0,
        training_wall_s=time.monotonic() - start,
        model_hashes={p.name: digest(p) for p in output.glob("*.json")},
    )
    (output / "training-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (output / "preferences.json.gz").write_bytes(
        __import__("gzip").compress((json.dumps(examples, sort_keys=True) + "\n").encode(), mtime=0)
    )
    return report


def fit_selector(
    data: Path = ROOT / "experiments/phase6/selector-v1", output: Path = MODELS
) -> dict[str, Any]:
    """Finalize adaptive artifacts only after actual fixed-mode counterfactuals."""
    import hashlib

    frozen = check_freeze()
    validation = set(frozen["validation_ids"])
    rows = []
    outcomes: Counter[tuple[str, str]] = Counter()
    provenance = read_json(data / "provenance.json")
    check_archive(data)
    if provenance["selector_protocol_sha256"] != digest(DIRECTORY / "selector-protocol.json"):
        raise ValueError("Selector protocol mismatch")
    expected = {(i, m) for i in frozen["development_ids"] for m in ("symbolic", "hybrid", "typed")}
    observed = set()
    for p in trace_paths(data / "traces"):
        t = Trace.model_validate(read_json(p))
        mode = t.metadata["arm"]
        if any(
            q.get("decision") != mode
            or q.get("decision_source") != "forced development counterfactual"
            for q in t.retrievals
        ):
            raise ValueError("Counterfactual did not execute its forced strategy")
        observed.add((t.task.id, mode))
        outcomes[(mode, t.status)] += 1
        if t.verification.verified:
            state = t.nodes[0].state
            assert state is not None
            rows.append(
                dict(
                    task_id=t.task.id,
                    features=mode_features(context_features(state), mode),
                    target=math.log1p(t.metrics.attempted_candidates),
                )
            )
    if observed != expected:
        raise ValueError("Incomplete or contaminated matched selector matrix")
    training = [r for r in rows if r["task_id"] not in validation]
    valid = [r for r in rows if r["task_id"] in validation]
    if len(training) < 30 or len(valid) < 10:
        raise ValueError("Insufficient verified family-separated selector costs")
    candidates: list[dict[str, Any]] = []
    for nonlinear in (False, True):
        m = regression(training, nonlinear)
        candidates.append(dict(nonlinear=nonlinear, validation_mse=mse(valid, m)))
    winner = min(candidates, key=lambda c: c["validation_mse"])
    selected = regression(rows, winner["nonlinear"])
    artifact = read_json(output / "learned.json")
    fingerprint = hashlib.sha256(
        json.dumps(artifact["relevance"], sort_keys=True).encode()
    ).hexdigest()
    if fingerprint != provenance["relevance_sha256"]:
        raise ValueError("Relevance changed after matched counterfactuals")
    for name in ("learned", "linear", "applicability", "learned-seed1", "learned-seed2"):
        path = output / f"{name}.json"
        if not path.exists():
            continue
        model = read_json(path)
        if model.get("selector_ready"):
            raise ValueError("Do not replace an already finalized selector")
        model.update(
            selector=selected,
            selector_ready=True,
            selector_training_ids=frozen["development_ids"],
            selector_collection_sha256=digest(data / "provenance.json"),
            selector_trace_manifest_sha256=digest(data / "trace-storage.json"),
            selector_training_relevance_sha256=fingerprint,
            selector_semantics=(
                "Conditional log attempt cost under fixed symbolic/hybrid/typed "
                "mode continuations with canonical P3 ties and fitted selected "
                "relevance. Greedy adaptive switching is a new rollout policy; "
                "censored costs excluded, success-conditioned missingness explicit. "
                "Shared fixed selector isolates linear/applicability relevance ablations."
            ),
        )
        path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    seed_diagnostics = []
    # The seed supplement is registered before selector architecture selection.
    # It never changes the fixed primary seed or chooses a model by final tests.
    for seed in (1, 2):
        validation_model = regression(training, True, seed=seed)
        seed_diagnostics.append(dict(seed=seed, validation_mse=mse(valid, validation_model)))
        if winner["nonlinear"]:
            variant = read_json(output / "learned.json")
            variant.update(
                selector=regression(rows, True, seed=seed),
                controller_seed=seed,
                role="Preregistered controller-seed sensitivity; not primary model",
            )
            (output / f"controller-seed{seed}.json").write_text(
                json.dumps(variant, indent=2, sort_keys=True) + "\n"
            )
    previous = output / "training-report.json"
    report = read_json(previous)
    (output / "relevance-training-report.json").write_text(previous.read_text())
    report.update(
        selector_ready=True,
        selector_candidates=candidates,
        selector_selected=winner,
        selector_seed_diagnostics=seed_diagnostics,
        seed_protocol_sha256=digest(DIRECTORY / "seed-protocol.json"),
        verified_selector_rows=len(rows),
        selector_train_rows=len(training),
        selector_validation_rows=len(valid),
        selector_mode_outcomes={f"{m}:{s}": v for (m, s), v in sorted(outcomes.items())},
        selector_collection_sha256=digest(data / "provenance.json"),
        model_hashes={
            p.name: digest(p)
            for p in output.glob("*.json")
            if p.name not in ("training-report.json", "relevance-training-report.json")
        },
    )
    previous.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
