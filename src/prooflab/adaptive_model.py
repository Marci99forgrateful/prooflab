"""Inspectable CPU-only linear/boosted depth-two utility and mode-cost models."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.research_io import read_json

MODELS = ROOT / "models/phase6"
VERSION = "adaptive-hybrid-v1"


def tree_value(tree: dict[str, Any], features: dict[str, float]) -> float:
    while "feature" in tree:
        tree = (
            tree["left"] if features.get(tree["feature"], 0) <= tree["threshold"] else tree["right"]
        )
    return float(tree["value"])


def predict(model: dict[str, Any], features: dict[str, float]) -> float:
    value = float(model.get("bias", 0))
    value += sum(float(w) * features.get(n, 0) for n, w in model.get("weights", {}).items())
    value += float(model.get("rate", 1)) * sum(
        tree_value(t, features) for t in model.get("trees", [])
    )
    if not math.isfinite(value):
        raise ValueError("Nonfinite CPU prediction")
    return value


def mode_features(features: dict[str, float], mode: str) -> dict[str, float]:
    return {**features, **{f"mode:{mode}:{n}": v for n, v in features.items()}}


class AdaptiveModel:
    def __init__(self, path: Path | None = None, variant: str = "learned") -> None:
        path = path or MODELS / f"{variant}.json"
        self.artifact = read_json(path)
        self.sha256 = digest(path)
        if self.artifact["feature_version"] != VERSION or self.artifact["evaluation_accessed"]:
            raise ValueError("Invalid adaptive artifact or test-trained model")

    def candidate_score(self, features: dict[str, float]) -> float:
        return predict(self.artifact["relevance"], features)

    def mode_costs(self, features: dict[str, float]) -> dict[str, float]:
        return {
            m: predict(self.artifact["selector"], mode_features(features, m))
            for m in ("symbolic", "hybrid", "typed")
        }

    def explain(self, features: dict[str, float]) -> list[tuple[str, float]]:
        model = self.artifact["relevance"]
        if "weights" in model:
            terms = [(n, w * features.get(n, 0)) for n, w in model["weights"].items()]
        else:
            # Exact prediction components, not falsely presented as Shapley values.
            terms = [
                (f"boosted tree {i + 1}", model["rate"] * tree_value(t, features))
                for i, t in enumerate(model.get("trees", []))
            ]
        return sorted(terms, key=lambda x: -abs(x[1]))[:8]
