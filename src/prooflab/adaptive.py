"""Explicit Phase 6 availability allocation and independent canonical scheduling.

No proof-state ID, theorem ID, future outcome or learned score enters tie breaks.
Symbolic automation remains labelled; all proposals require actual Lean execution.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from prooflab.generator_study import extended_candidates
from prooflab.lean import LeanSession
from prooflab.models import Candidate, ProofState
from prooflab.outcome import OutcomeRanking
from prooflab.retrieval import TypedProvider

MODES = (
    "symbolic",
    "naive",
    "fixed",
    "deterministic",
    "staged",
    "linear",
    "learned",
    "applicability",
)


def context_features(state: ProofState) -> dict[str, float]:
    goal = state.goals[0] if state.goals else None
    hypotheses = goal.hypotheses if goal else []
    heads = {h.type.head for h in hypotheses}
    text = goal.target.text if goal else ""
    f = {
        "bias": 1.0,
        "goals": min(len(state.goals), 8) / 8,
        "target_size": min(len(text), 600) / 600,
        "hypotheses": min(len(hypotheses), 40) / 40,
        "proof_hypotheses": sum(h.is_proof for h in hypotheses) / 40,
        "functions": min(sum(h.type.forall and not h.is_proof for h in hypotheses), 8) / 8,
        "local_equalities": min(sum(h.is_proof and h.type.head == "Eq" for h in hypotheses), 8) / 8,
        "sets": float(any(x in text for x in ("∈", "⊆", "∩", "∪", "⁻¹'", "''", "ᶜ"))),
        "inverse": float("⁻¹" in text and "⁻¹'" not in text),
        "product": float("×" in text or ".1" in text or ".2" in text),
        "metavariables": min(text.count("?"), 8) / 8,
    }
    for c in (
        "Group",
        "CommGroup",
        "Monoid",
        "CommMonoid",
        "CommRing",
        "CommSemiring",
        "Lattice",
        "PartialOrder",
    ):
        f["class:" + c] = float(c in heads)
    for head in ("Exists", "And", "Or", "Eq", "Not", "Set.Subset", "LE.le"):
        f["head:" + head] = float(goal is not None and goal.target.head == head)
    f["forall"] = float(goal is not None and goal.target.forall)
    return f


def candidate_features(
    state: ProofState, candidate: Candidate, row: dict[str, Any]
) -> dict[str, float]:
    from prooflab.retrieval import features

    # Historical symbolic proposals have no native compatibility observation.
    # Encode missingness separately; never change the recorded unknown to false.
    normalized = {**row, "compatible": bool(row.get("compatible"))}
    result = features(state, candidate, normalized)
    result["compatibility_observed"] = float(row.get("compatible") is not None)
    result.update({"context:" + k: v for k, v in context_features(state).items()})
    result["baseline"] = float(row.get("baseline", False))
    result["simp_all"] = float(candidate.tactic == "simp_all")
    result["group_normalizer"] = float("mul_inv_cancel" in candidate.tactic)
    result["generic_elimination"] = float(
        candidate.tactic
        in ("apply Or.elim", "apply And.left", "apply And.right", "apply Exists.elim")
    )
    result["obligation_load"] = (
        min(len(row.get("premises", [])) + row.get("unresolved_explicit_data", 0), 12) / 12
    )
    return result


class CanonicalOutcomeRanking(OutcomeRanking):
    """P3 scores and frontier unchanged; explicit tactic-string tie rule."""

    def rank_candidates(
        self, proof_state: ProofState, candidate_steps: list[Candidate]
    ) -> list[Candidate]:
        return sorted(candidate_steps, key=lambda c: (-self.score(proof_state, c), c.tactic))


class HybridProvider:
    def __init__(
        self,
        mode: str = "deterministic",
        model_path: Path | None = None,
        forced_mode: str | None = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError("Unknown hybrid policy")
        self.mode = mode
        if forced_mode not in (None, "symbolic", "hybrid", "typed"):
            raise ValueError("Unregistered development counterfactual mode")
        self.forced_mode = forced_mode
        self.calls = 0
        self.nonexistential_calls = 0
        self.typed = TypedProvider("typed")
        self.model = None
        if mode in ("learned", "linear", "applicability"):
            from prooflab.adaptive_model import AdaptiveModel

            self.model = AdaptiveModel(model_path, mode, allow_provisional=forced_mode is not None)

    def generate(
        self,
        lean: LeanSession,
        state: ProofState,
        limit: int,
        forbidden: frozenset[str],
        timeout: float,
    ) -> tuple[list[Candidate], dict[str, Any]]:
        self.calls += 1
        baseline = extended_candidates(state, limit, forbidden)
        f = context_features(state)
        if not f["head:Exists"]:
            self.nonexistential_calls += 1
        expressive = bool(
            f["head:Exists"]
            or f["class:Group"]
            or f["class:CommGroup"]
            or f["class:Lattice"]
            or f["class:PartialOrder"]
            or f["sets"]
        )
        decision = "hybrid" if expressive else "symbolic"
        predicted = {}
        selector_terms: list[tuple[str, float]] = []
        inference_s = 0.0
        if self.mode == "naive":
            decision = "hybrid"
        if self.mode == "symbolic":
            decision = "symbolic"
        if self.mode == "staged" and not f["head:Exists"] and self.nonexistential_calls <= 2:
            decision = "symbolic"
        if self.forced_mode is not None:
            decision = self.forced_mode
        elif self.model is not None:
            tick = time.monotonic()
            predicted = self.model.mode_costs(f)
            decision = min(predicted, key=lambda m: (predicted[m], m))
            selector_terms = self.model.mode_explain(f, decision)
            inference_s += time.monotonic() - tick
        record: dict[str, Any] = dict(
            mode=self.mode,
            phase=6,
            recognized_structures=[k[6:] for k, v in f.items() if k.startswith("class:") and v],
            context_features=f,
            decision=decision,
            decision_source="forced development counterfactual" if self.forced_mode else "policy",
            predicted_log_costs=predicted,
            selector_contributions=selector_terms,
            selector_bias=self.model.artifact.get("selector", {}).get("bias")
            if self.model and not self.forced_mode
            else None,
            stage=self.calls,
            nonexistential_stage=self.nonexistential_calls,
            scheduling=(
                "unchanged P3 score; explicit tactic-string tie rule "
                "independent of retrieval score/order"
            ),
            query_wall_s=0.0,
            model_inference_s=inference_s,
            original=[c.tactic for c in baseline],
            model_sha256=self.model.sha256 if self.model else None,
        )
        if decision == "symbolic":
            selected = sorted(baseline, key=lambda c: c.tactic)
            record.update(
                selected=[c.tactic for c in selected],
                entered=[],
                displaced=[],
                pool=[
                    dict(
                        candidate=c.model_dump(),
                        family="symbolic",
                        baseline=True,
                        protected=True,
                        selected=True,
                        deterministic_score=c.prior,
                        learned_score=None,
                        selection_reason="symbolic strategy; no retrieval query",
                    )
                    for c in baseline
                ],
                allocation=dict(baseline=len(baseline), novelty=0, cap=limit),
                potential_complete=False,
            )
            return selected, record
        typed, observation = self.typed.generate(lean, state, limit, forbidden, timeout)
        record.update(
            native=observation["native"],
            query_wall_s=observation["query_wall_s"],
            index_sha256=observation["index_sha256"],
            potential_complete=True,
        )
        base_map = {c.tactic: c for c in baseline}
        pool = {r["candidate"]["tactic"]: dict(r) for r in observation["pool"]}
        for c in baseline:
            pool.setdefault(
                c.tactic,
                dict(
                    candidate=c.model_dump(),
                    family="symbolic",
                    compatible=None,
                    deterministic_score=c.prior,
                ),
            )
            pool[c.tactic]["candidate"] = c.model_dump()
        for tactic, row in pool.items():
            row["baseline"] = tactic in base_map
            c = Candidate.model_validate(row["candidate"])
            # Generic projection/elimination and unresolved term guesses are a
            # separate potential universe, not mathematically incorrect actions.
            row["eligible_novelty"] = bool(
                row.get("compatible")
                and not row.get("unresolved_explicit_data", 0)
                and tactic
                not in ("apply Or.elim", "apply And.left", "apply And.right", "apply Exists.elim")
            )
            tick = time.monotonic()
            row["learned_score"] = (
                self.model.candidate_score(candidate_features(state, c, row))
                if self.model
                else None
            )
            row["learned_contributions"] = (
                self.model.explain(candidate_features(state, c, row)) if self.model else []
            )
            inference_s += time.monotonic() - tick if self.model else 0
        novelty = [
            Candidate.model_validate(r["candidate"])
            for t, r in pool.items()
            if t not in base_map and r["eligible_novelty"]
        ]
        novelty.sort(
            key=lambda c: (
                -(
                    pool[c.tactic]["learned_score"]
                    if self.model
                    else pool[c.tactic]["deterministic_score"]
                ),
                c.tactic,
            )
        )
        quota = min(8 if f["head:Exists"] else 4, limit)
        if self.mode == "fixed":
            quota = min(4, limit)
        if self.mode == "naive":
            # Named concatenation/truncation control: retain baseline order.
            selected = list({c.tactic: c for c in [*baseline, *typed]}.values())[:limit]
            protected: set[str] = set()
        elif decision == "typed":
            selected = typed
            protected = set()
        else:
            # Baseline normalizers and structural actions have explicit protection.
            order = sorted(
                enumerate(baseline),
                key=lambda p: (p[1].category not in ("specialized", "goal"), p[0]),
            )
            keep = max(0, limit - min(quota, len(novelty)))
            original_lane = [c for _, c in order[:keep]]
            protected = {c.tactic for c in original_lane}
            selected = [*original_lane, *novelty[: limit - len(original_lane)]]
        # A shared tactic has one canonical Candidate schema across all new
        # modes, including the typed strategy. Otherwise legacy prior/category
        # differences could silently alter P3 scores despite identical membership.
        selected = sorted(
            [Candidate.model_validate(pool[c.tactic]["candidate"]) for c in selected],
            key=lambda c: c.tactic,
        )
        chosen = {c.tactic for c in selected}
        for tactic, row in pool.items():
            row["selected"] = tactic in chosen
            row["protected"] = tactic in protected
            row["selection_reason"] = (
                "protected symbolic capability"
                if tactic in protected
                else "selected novelty"
                if tactic in chosen and tactic not in base_map
                else "selected by strategy"
                if tactic in chosen
                else "ineligible novelty (not a mathematical negative)"
                if not row["eligible_novelty"] and tactic not in base_map
                else "outside fixed cap"
            )
        record.update(
            pool=list(pool.values()),
            selected=[c.tactic for c in selected],
            entered=sorted(chosen - base_map.keys()),
            displaced=sorted(base_map.keys() - chosen),
            allocation=dict(
                baseline=len(chosen & base_map.keys()),
                novelty=len(chosen - base_map.keys()),
                hybrid_novelty_reserve=quota if decision == "hybrid" else None,
                borrowed_baseline_capacity=(
                    max(0, len(chosen - base_map.keys()) - quota) if decision == "hybrid" else 0
                ),
                cap=limit,
            ),
            model_inference_s=inference_s,
        )
        return selected, record
