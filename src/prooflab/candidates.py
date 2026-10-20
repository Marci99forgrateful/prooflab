"""Bounded structural generation and inspectable, categorized Mathlib retrieval.

No task ID or benchmark answer is used here. Expressions are descriptions from
Lean; textual matching only proposes tactics, and never establishes correctness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from prooflab.models import Candidate, ProofState


@dataclass(frozen=True)
class Lemma:
    name: str
    domain: str
    tokens: tuple[str, ...]
    module: str
    action: str = "apply"


# A deliberately small, public retrieval corpus, independent of task definitions.
# Names and types are validated against the pinned environment by integration tests.
LEMMAS = (
    Lemma("le_refl", "order", ("≤",), "Mathlib.Order.Defs.PartialOrder"),
    Lemma("le_trans", "order", ("≤",), "Mathlib.Order.Defs.PartialOrder"),
    Lemma("le_antisymm", "order", ("=", "≤"), "Mathlib.Order.Defs.PartialOrder"),
    Lemma("lt_trans", "order", ("<",), "Mathlib.Order.Defs.PartialOrder"),
    Lemma("lt_of_lt_of_le", "order", ("<",), "Mathlib.Order.Defs.PartialOrder"),
    Lemma("lt_of_le_of_lt", "order", ("<",), "Mathlib.Order.Defs.PartialOrder"),
    Lemma("Eq.symm", "logic", ("=",), "Init.Prelude"),
    Lemma("Eq.trans", "logic", ("=",), "Init.Prelude"),
    Lemma("Set.Subset.antisymm", "sets", ("=", "Set"), "Mathlib.Data.Set.Basic"),
    Lemma("Set.Subset.trans", "sets", ("⊆",), "Mathlib.Data.Set.Basic"),
    Lemma("Set.inter_subset_left", "sets", ("⊆", "∩"), "Mathlib.Data.Set.Basic"),
    Lemma("Set.inter_subset_right", "sets", ("⊆", "∩"), "Mathlib.Data.Set.Basic"),
    Lemma("Set.subset_union_left", "sets", ("⊆", "∪"), "Mathlib.Data.Set.Basic"),
    Lemma("Set.subset_union_right", "sets", ("⊆", "∪"), "Mathlib.Data.Set.Basic"),
    Lemma("mul_one", "algebra", ("*", "1"), "Mathlib.Algebra.Group.Defs", "exact"),
    Lemma("one_mul", "algebra", ("*", "1"), "Mathlib.Algebra.Group.Defs", "exact"),
    Lemma("mul_assoc", "algebra", ("*",), "Mathlib.Algebra.Group.Defs", "apply"),
    Lemma("mul_comm", "algebra", ("*",), "Mathlib.Algebra.Group.Defs", "apply"),
    Lemma("add_zero", "algebra", ("+", "0"), "Mathlib.Algebra.Group.Defs", "exact"),
    Lemma("zero_add", "algebra", ("+", "0"), "Mathlib.Algebra.Group.Defs", "exact"),
    Lemma("add_assoc", "algebra", ("+",), "Mathlib.Algebra.Group.Defs"),
    Lemma("add_comm", "algebra", ("+",), "Mathlib.Algebra.Group.Defs"),
    Lemma("mul_add", "algebra", ("*", "+"), "Mathlib.Algebra.Ring.Defs"),
    Lemma("add_mul", "algebra", ("*", "+"), "Mathlib.Algebra.Ring.Defs"),
)


def safe_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9']*", name))


def generate_candidates(
    state: ProofState, limit: int = 24, forbidden: frozenset[str] = frozenset()
) -> list[Candidate]:
    if not state.goals:
        return []
    goal = state.goals[0]
    target = goal.target
    context = " ".join(h.type.text for h in goal.hypotheses)
    result: list[Candidate] = []
    occupied = {h.name for h in goal.hypotheses}
    fresh = [f"h{i}" for i in range(1000) if f"h{i}" not in occupied]

    def add(tactic: str, category: str, reason: str, prior: float) -> None:
        result.append(Candidate(tactic=tactic, category=category, reason=reason, prior=prior))  # type: ignore[arg-type]

    if target.forall or target.head in ("Not", "Set.Subset") or "⊆" in target.text:
        name = fresh[0]
        add(f"intro {name}", "goal", "Introduce a binder or implication premise", 9)
    if target.head in ("And", "Iff"):
        add("constructor", "goal", "Split the goal into its components", 8)
    if target.head == "Or":
        add("left", "goal", "Explore the left alternative", 6)
        add("right", "goal", "Explore the right alternative", 6)
    add("assumption", "goal", "Match the goal against the local context", 10)
    if target.head == "Eq" or "=" in target.text:
        add("rfl", "goal", "Check definitional equality", 8)
    for hypothesis in goal.hypotheses:
        name, typ = hypothesis.name, hypothesis.type
        if not safe_name(name) or not hypothesis.is_proof:
            continue
        # Do not apply arbitrary objects of a sort as if they were proof functions.
        if typ.forall or typ.head == "Not":
            add(f"apply {name}", "hypothesis", f"Use implication or function {name}", 7)
        if typ.head == "And":
            for side in (1, 2):
                add(f"exact {name}.{side}", "hypothesis", f"Project component {side}", 8)
                add(f"apply {name}.{side}", "hypothesis", "Apply a conjunction component", 5)
        if typ.head in ("And", "Exists"):
            add(
                f"rcases {name} with ⟨{fresh[0]}, {fresh[1]}⟩",
                "hypothesis",
                "Eliminate a structured hypothesis with fresh explicit names",
                4,
            )
        if typ.head == "Or":
            add(
                f"rcases {name} with {fresh[0]} | {fresh[1]}",
                "hypothesis",
                "Explore both cases of a disjunction",
                4,
            )
        if typ.head == "False":
            add(f"exact False.elim {name}", "hypothesis", "Eliminate contradiction", 10)
        if typ.head == "Eq":
            add(f"rw [{name}]", "hypothesis", "Rewrite using a local equality", 6)
            add(f"rw [← {name}]", "hypothesis", "Explore reverse equality rewriting", 3)
    # Retrieve by goal features, then bounded token overlap in the local context.
    for lemma in LEMMAS:
        if lemma.name in forbidden or any(lemma.name.endswith("." + x) for x in forbidden):
            continue
        if not all(t in target.text or (t == "Set" and "Set" in context) for t in lemma.tokens):
            continue
        # `apply` permits Lean's elaborator to infer implicit parameters.
        result.append(
            Candidate(
                tactic=f"apply {lemma.name}",
                category="lemma",
                reason=f"Type-feature match: {lemma.tokens}",
                prior=4,
                lemma=lemma.name,
                provenance=lemma.module,
            )
        )
    if target.head == "Eq" and any(t in target.text for t in ("+", "*", "^")):
        add("ring", "specialized", "Normalize a polynomial equality (Mathlib ring)", 2)
    if "Nat" in context and any(t in target.text for t in ("≤", "<", "=")):
        add("omega", "specialized", "Presburger arithmetic (Lean omega)", 2)
    if target.head == "Exists":
        terms = [
            h
            for h in goal.hypotheses
            if not h.is_proof
            and safe_name(h.name)
            and h.type.text not in ("Prop", "Type", "Type u", "Type*")
        ]
        for term in terms[:4]:
            add(f"exists {term.name}", "goal", "Try a witness from the local context", 3)
    # Stable de-duplication. Both search policies receive exactly the same bounded set.
    return list({c.tactic: c for c in result}.values())[:limit]


class RankingPolicy(Protocol):
    def rank_candidates(
        self, proof_state: ProofState, candidate_steps: list[Candidate]
    ) -> list[Candidate]: ...

    def state_priority(self, state: ProofState, depth: int) -> float: ...


class UniformRanking:
    def rank_candidates(
        self, proof_state: ProofState, candidate_steps: list[Candidate]
    ) -> list[Candidate]:
        return candidate_steps

    def state_priority(self, state: ProofState, depth: int) -> float:
        return float(depth)


class HeuristicRanking:
    def rank_candidates(
        self, proof_state: ProofState, candidate_steps: list[Candidate]
    ) -> list[Candidate]:
        return sorted(candidate_steps, key=lambda candidate: -candidate.prior)

    def state_priority(self, state: ProofState, depth: int) -> float:
        complexity = sum(len(g.target.text) for g in state.goals)
        # Best-first, not A*: no claim of admissibility or optimality.
        return 12 * len(state.goals) + complexity / 12 + depth * 0.8
