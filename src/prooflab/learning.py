"""A real locally fitted linear policy. JSON weights, no executable model format."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from prooflab.candidates import HeuristicRanking
from prooflab.features import FEATURE_NAMES, FEATURE_VERSION, dot, extract_features
from prooflab.lean import ROOT
from prooflab.models import Candidate, Model, ProofState

DEFAULT_MODEL = ROOT / "models/phase2/ranker.json"


class ModelArtifact(Model):
    schema_version: int = 1
    feature_version: str = FEATURE_VERSION
    architecture: str = "pairwise logistic linear state-action ranker"
    weights: dict[str, float]
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_artifact(self) -> ModelArtifact:
        if self.schema_version != 1 or self.feature_version != FEATURE_VERSION:
            raise ValueError("Unsupported model format/feature version")
        if not self.weights or not set(self.weights) <= FEATURE_NAMES:
            raise ValueError("Unknown or missing model feature weights")
        if not all(math.isfinite(w) for w in self.weights.values()):
            raise ValueError("Non-finite learned weight")
        return self


class LearnedRanking(HeuristicRanking):
    """Only candidate priorities are learned; the frontier score is held fixed."""

    def __init__(self, path: Path = DEFAULT_MODEL) -> None:
        self.path = path
        raw = path.read_bytes()
        self.model = ModelArtifact.model_validate_json(raw)
        self.model_hash = hashlib.sha256(raw).hexdigest()

    def score(self, state: ProofState, candidate: Candidate) -> float:
        return dot(self.model.weights, extract_features(state, candidate))

    def contributions(self, state: ProofState, candidate: Candidate) -> list[tuple[str, float]]:
        products = [
            (name, value * self.model.weights.get(name, 0))
            for name, value in extract_features(state, candidate).items()
        ]
        return sorted(products, key=lambda item: -abs(item[1]))[:5]

    def rank_candidates(
        self, proof_state: ProofState, candidate_steps: list[Candidate]
    ) -> list[Candidate]:
        # Python's stable sort preserves the common generation order on ties.
        return sorted(candidate_steps, key=lambda step: -self.score(proof_state, step))


def save_model(path: Path, artifact: ModelArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.model_dump(), sort_keys=True, indent=2) + "\n")
