"""Budgeted completion is an operational outcome, never mathematical falsity."""

from __future__ import annotations

import math
from pathlib import Path

from prooflab.adaptive import context_features
from prooflab.adaptive_model import mode_features, predict
from prooflab.lean import ROOT
from prooflab.models import Budget, ProofState
from prooflab.phase3_data import digest
from prooflab.research_io import read_json

MODES = ("symbolic", "hybrid", "typed")
VERSION = "budget-completion-v1"
MODEL_DIR = ROOT / "models/phase7"


def features(
    state: ProofState, attempts: int, expansions: int, seconds: float, depth: int
) -> dict[str, float]:
    return {
        **context_features(state),
        "remaining_attempts": min(attempts, 10000) / 600,
        "remaining_expansions": min(expansions, 1000) / 80,
        "remaining_seconds": min(max(seconds, 0), 300) / 18,
        "depth": min(depth, 16) / 16,
        "attempts_per_second": min(attempts / max(seconds, 0.1), 200) / 200,
    }


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-40, min(40, value))))


def staged_mode(state: ProofState, nonexistential_stage: int) -> str:
    f = context_features(state)
    if not f["head:Exists"] and nonexistential_stage <= 2:
        return "symbolic"
    expressive = any(
        f[n]
        for n in (
            "head:Exists",
            "class:Group",
            "class:CommGroup",
            "class:Lattice",
            "class:PartialOrder",
            "sets",
        )
    )
    return "hybrid" if expressive else "symbolic"


class BudgetModel:
    def __init__(self, path: Path | None = None) -> None:
        path = path or MODEL_DIR / "selected.json"
        self.artifact = read_json(path)
        self.sha256 = digest(path)
        if self.artifact["feature_version"] != VERSION or self.artifact["evaluation_accessed"]:
            raise ValueError("Invalid budget-policy model or evaluation-trained artifact")
        if not self.artifact.get("training_ids"):
            raise ValueError("A trained development-only artifact is required")

    def predictions(self, f: dict[str, float]) -> dict[str, dict[str, float]]:
        result = {}
        for mode in MODES:
            x = mode_features(f, mode)
            p = sigmoid(predict(self.artifact["completion"], x))
            cost = math.expm1(max(0, min(12, predict(self.artifact["cost"], x))))
            result[mode] = {"completion_probability": p, "conditional_attempts": cost}
        return result


def choose(
    predictions: dict[str, dict[str, float]],
    baseline: str,
    variant: str,
    remaining_attempts: int,
    margin: float = 0.15,
) -> tuple[str, str, dict[str, float]]:
    """Choose success first; penalize spending the budget on incomplete runs."""
    if variant not in ("completion", "cost", "joint", "conservative", "root_only"):
        raise ValueError("Unknown budget policy")
    scores = {}
    for mode, row in predictions.items():
        p, cost = row["completion_probability"], row["conditional_attempts"]
        scores[mode] = (
            p
            if variant == "completion"
            else -cost
            if variant == "cost"
            else p - 0.25 * p * min(cost / max(remaining_attempts, 1), 2)
        )
    best = max(scores, key=lambda m: (scores[m], m == baseline, m))
    if variant == "conservative":
        delta = (
            predictions[best]["completion_probability"]
            - predictions[baseline]["completion_probability"]
        )
        if delta < margin or scores[best] <= scores[baseline]:
            return baseline, "staged fallback: insufficient predicted completion advantage", scores
        return (
            best,
            f"completion advantage {delta:.3f} exceeds development margin {margin:.3f}",
            scores,
        )
    return best, f"maximum development-trained {variant} decision score", scores


def budget_features(state: ProofState, budget: Budget, depth: int = 0) -> dict[str, float]:
    return features(state, budget.max_attempts, budget.max_expansions, budget.timeout_s, depth)
