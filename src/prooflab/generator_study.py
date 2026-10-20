"""Exploratory generator arm, never used in the primary scheduling experiment."""

from __future__ import annotations

from prooflab.candidates import generate_candidates
from prooflab.models import Candidate, ProofState


def extended_candidates(
    state: ProofState, limit: int = 24, forbidden: frozenset[str] = frozenset()
) -> list[Candidate]:
    original = generate_candidates(state, limit, forbidden)
    if not state.goals:
        return original
    target = state.goals[0].target.text
    additions = [
        Candidate(
            tactic="simp_all",
            category="specialized",
            prior=9,
            reason=(
                "Separate generator study: installed general local simplification; "
                "internal work is not one primitive inference"
            ),
        )
    ]
    # Fixed public local corpus, filtered by visible mathematical structure.
    for token, lemmas in [
        ("⊓", ("inf_le_left", "inf_le_right")),
        ("⊔", ("le_sup_left", "le_sup_right")),
    ]:
        if token in target:
            additions.extend(
                Candidate(
                    tactic=f"apply {lemma}",
                    category="lemma",
                    lemma=lemma,
                    provenance="Mathlib lattice order (installed)",
                    prior=5,
                    reason="Separate type/head-relevance corpus expansion",
                )
                for lemma in lemmas
                if lemma not in forbidden
            )
    if any(token in target for token in ("*", "⁻¹")):
        additions.append(
            Candidate(
                tactic="simp only [mul_assoc, mul_one, one_mul] at *",
                category="specialized",
                prior=7,
                reason="Separate rewriting-normalization alternative",
            )
        )
    return list({c.tactic: c for c in [*additions, *original]}.values())[:limit]
