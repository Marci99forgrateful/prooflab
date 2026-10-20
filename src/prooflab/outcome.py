"""Safe CPU outcome-aware ranking; no Lean lookahead at inference time."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from prooflab.candidates import HeuristicRanking
from prooflab.features import dot
from prooflab.lean import ROOT
from prooflab.models import Candidate, Model, ProofState
from prooflab.outcome_features import FEATURE_NAMES, VERSION, features

MODELS = ROOT / "models/phase3"


class OutcomeArtifact(Model):
    schema_version: int = 1
    feature_version: str = VERSION
    architecture: str = (
        "multitask pairwise linear applicability and verified-continuation cost ranker"
    )
    feature_mode: str = "full"
    variant: str = "outcome"
    weights: dict[str, float]
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_model(self) -> OutcomeArtifact:
        if (
            self.schema_version != 1
            or self.feature_version != VERSION
            or self.feature_mode not in ("full", "old")
        ):
            raise ValueError("Unsupported outcome model schema/features")
        if (
            not self.weights
            or not set(self.weights) <= FEATURE_NAMES
            or not all(math.isfinite(v) for v in self.weights.values())
        ):
            raise ValueError("Invalid outcome weights")
        if self.variant not in ("outcome", "applicability_only", "old_features_outcome"):
            raise ValueError("Unknown model variant")
        return self


class OutcomeRanking(HeuristicRanking):
    def __init__(self, path: Path = MODELS / "outcome.json") -> None:
        raw = path.read_bytes()
        self.model = OutcomeArtifact.model_validate_json(raw)
        self.model_hash = hashlib.sha256(raw).hexdigest()

    def score(self, state: ProofState, candidate: Candidate) -> float:
        return dot(self.model.weights, features(state, candidate, self.model.feature_mode))

    def contributions(self, state: ProofState, candidate: Candidate) -> list[tuple[str, float]]:
        products = [
            (n, v * self.model.weights.get(n, 0))
            for n, v in features(state, candidate, self.model.feature_mode).items()
        ]
        return sorted(products, key=lambda p: -abs(p[1]))[:7]

    def rank_candidates(
        self, proof_state: ProofState, candidate_steps: list[Candidate]
    ) -> list[Candidate]:
        return sorted(candidate_steps, key=lambda c: -self.score(proof_state, c))


def save(path: Path, model: OutcomeArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(), sort_keys=True, indent=2) + "\n")
