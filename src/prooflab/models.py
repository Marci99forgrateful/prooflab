"""Shared, validated wire and research schemas. Lean is the mathematical authority."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SearchAlgorithm = Literal[
    "bfs",
    "best_first",
    "learned",
    "outcome",
    "automation",
    "applicability_only",
    "old_features_outcome",
]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Expression(Model):
    text: str
    head: str
    forall: bool


class Hypothesis(Model):
    name: str
    id: str
    type: Expression
    is_proof: bool = True


class Goal(Model):
    id: str
    target: Expression
    hypotheses: list[Hypothesis]


class ProofState(Model):
    state_id: int
    goals: list[Goal]


class Task(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    title: str
    domain: Literal["logic", "order", "algebra", "sets"]
    difficulty: Literal["easy", "moderate", "challenge"]
    split: Literal["development", "held_out"]
    binders: str
    target: str
    display: str
    description: str
    origin: str = "Original benchmark statement; mathematical result is not claimed novel."
    forbidden_lemmas: list[str] = Field(default_factory=list)


class Candidate(Model):
    tactic: str
    category: Literal["goal", "hypothesis", "lemma", "specialized", "reference"]
    reason: str
    prior: float = 0
    lemma: str | None = None
    provenance: str | None = None


class Budget(Model):
    max_depth: int = Field(default=6, ge=1, le=16)
    max_expansions: int = Field(default=80, ge=1, le=1000)
    max_candidates: int = Field(default=24, ge=1, le=64)
    max_attempts: int = Field(default=600, ge=1, le=10000)
    timeout_s: float = Field(default=30, ge=0.05, le=300)
    tactic_timeout_s: float = Field(default=3, ge=0.05, le=15)


class Node(Model):
    id: int
    parent: int | None
    depth: int
    state: ProofState | None
    tactic: str | None
    category: str | None = None
    lemma: str | None = None
    provenance: str | None = None
    reason: str = "Initial Lean goal"
    status: Literal["root", "accepted", "rejected", "solved", "error"]
    error: str | None = None
    elapsed_ms: float = 0
    on_proof_path: bool = False


class Metrics(Model):
    attempted_candidates: int = 0
    accepted_transitions: int = 0
    rejected_candidates: int = 0
    expanded_states: int = 0
    frontier: int = 0
    max_depth: int = 0
    proof_length: int = 0
    elapsed_s: float = 0
    lean_execution_s: float = 0
    initialization_s: float = 0
    verification_s: float = 0
    planning_s: float = 0
    model_inference_s: float = 0


class CandidateRanking(Model):
    tactic: str
    category: str
    generated_order: int
    actual_rank: int
    heuristic_score: float
    learned_score: float | None = None
    contributions: list[tuple[str, float]] = Field(default_factory=list)
    outcome_score: float | None = None
    outcome_contributions: list[tuple[str, float]] = Field(default_factory=list)
    policy_score: float | None = None


class StateRanking(Model):
    node_id: int
    candidates: list[CandidateRanking]


class Verification(Model):
    verified: bool = False
    axioms: list[str] = Field(default_factory=list)
    error: str | None = None
    elapsed_s: float = 0
    source_sha256: str | None = None


class Trace(Model):
    schema_version: int = 1
    task: Task
    algorithm: SearchAlgorithm
    budget: Budget
    status: Literal[
        "verified", "not_found_within_budget", "execution_error", "cancelled", "unsupported"
    ] = "not_found_within_budget"
    termination: str = "search_exhausted"
    nodes: list[Node] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    proof: list[str] = Field(default_factory=list)
    lean_source: str | None = None
    verification: Verification = Field(default_factory=Verification)
    metadata: dict[str, str] = Field(default_factory=dict)
    error: str | None = None
    proof_origin: str | None = None
    rankings: list[StateRanking] = Field(default_factory=list)
