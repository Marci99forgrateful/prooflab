"""Pre-decision state-value features and independently trained CPU frontier model.

Predicts the cost of one fixed continuation policy conditional on observed success,
not provability, shortest proof length, or an admissible A* heuristic.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from prooflab.candidates import HeuristicRanking, generate_candidates
from prooflab.lean import ROOT
from prooflab.models import Model, ProofState

VERSION = "prooflab-frontier-state-v1"
MODELS = ROOT / "models/phase4"
Mode = Literal["linear", "quadratic"]


def state_features(
    state: ProofState, depth: int, parent: ProofState | None, mode: Mode = "linear"
) -> dict[str, float]:
    goals = state.goals
    count = max(1, len(goals))
    length = sum(len(g.target.text) for g in goals)
    hyps = sum(len(g.hypotheses) for g in goals)
    exact = sum(any(h.type.text == g.target.text for h in g.hypotheses) for g in goals)
    covered = sum(any(h.type.head == g.target.head for h in g.hypotheses) for g in goals)
    context = " ".join(h.type.text for g in goals for h in g.hypotheses if h.is_proof)
    tokens = set(re.findall(r"\w+", " ".join(g.target.text for g in goals)))
    operations = generate_candidates(state, 24)
    previous = parent or state
    previous_length = sum(len(g.target.text) for g in previous.goals)
    result = {
        "bias": 1.0,
        "goals": len(goals) / 8,
        "target_size": min(length / 400, 4),
        "largest_goal": min(max((len(g.target.text) for g in goals), default=0) / 200, 4),
        "context_size": min(len(context) / 1500, 4),
        "hypotheses": min(hyps / 40, 4),
        "exact_fraction": exact / count,
        "head_coverage": covered / count,
        "context_overlap": len(tokens & set(re.findall(r"\w+", context))) / max(1, len(tokens)),
        "equality_hypotheses": context.count("=") / 10,
        "implication_hypotheses": context.count("→") / 10,
        "depth": depth / 12,
        "path_transitions": math.log1p(depth) / 3,
        "parent_goal_reduction": (len(previous.goals) - len(goals)) / 8,
        "parent_size_reduction": (previous_length - length) / 400,
        "relative_simplification": (previous_length - length) / max(1, previous_length),
        "available_operations": len(operations) / 24,
        "available_rewrites": sum(c.tactic.startswith("rw ") for c in operations) / 24,
        "available_applications": sum(c.tactic.startswith("apply ") for c in operations) / 24,
        "available_normalizers": sum(c.category == "specialized" for c in operations) / 4,
        "visible_metavariables": sum(g.target.text.count("?") for g in goals) / 8,
    }
    for head in ("And", "Or", "Eq", "Not", "Exists", "Set.Subset"):
        result["head:" + head] = sum(g.target.head == head for g in goals) / count
    result["forall_fraction"] = sum(g.target.forall for g in goals) / count
    if mode == "quadratic":
        names = ("goals", "target_size", "context_size", "exact_fraction", "head_coverage", "depth")
        for index, a in enumerate(names):
            for b in names[index:]:
                result[f"interaction:{a}*{b}"] = result[a] * result[b]
    return result


class FrontierArtifact(Model):
    schema_version: Literal[1] = 1
    feature_version: Literal["prooflab-frontier-state-v1"] = "prooflab-frontier-state-v1"
    mode: Mode
    weights: dict[str, float]
    means: dict[str, float]
    scales: dict[str, float]
    depth_penalty: float = Field(ge=0, le=10)
    provenance: dict[str, object]

    @field_validator("weights", "means", "scales")
    @classmethod
    def finite(cls, values: dict[str, float]) -> dict[str, float]:
        if not values or any(not math.isfinite(v) for v in values.values()):
            raise ValueError("Finite nonempty state model required")
        return values


class FrontierModel:
    def __init__(self, path: Path = MODELS / "selected.json") -> None:
        raw = path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.artifact = FrontierArtifact.model_validate_json(raw)
        a = self.artifact
        if a.weights.keys() != a.means.keys() or a.weights.keys() != a.scales.keys():
            raise ValueError("State model feature schema mismatch")
        if any(s <= 0 for s in a.scales.values()):
            raise ValueError("State model normalization must be positive")

    def explain(
        self, state: ProofState, depth: int, parent: ProofState | None
    ) -> tuple[float, list[tuple[str, float]]]:
        a = self.artifact
        f = state_features(state, depth, parent, a.mode)
        if f.keys() != a.weights.keys():
            raise ValueError("State features differ from trained schema")
        terms = [(n, a.weights[n] * (f[n] - a.means[n]) / a.scales[n]) for n in f]
        value = math.fsum(v for _, v in terms)
        return value, sorted(terms, key=lambda x: -abs(x[1]))[:8]

    def score(self, state: ProofState, depth: int, parent: ProofState | None) -> float:
        value, _ = self.explain(state, depth, parent)
        return value

    def priority(self, value: float, depth: int) -> float:
        return max(0.0, min(math.log1p(600), value)) + self.artifact.depth_penalty * depth


def handcrafted_priority(state: ProofState, depth: int) -> float:
    return HeuristicRanking().state_priority(state, depth)
