"""Bounded typed availability selection, separate from unchanged action scheduling.

Native compatibility is a proposal check, never a successful tactic or proof.
Every row, including incompatible/unselected proposals, remains inspectable.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from prooflab.candidates import generate_candidates
from prooflab.generator_study import extended_candidates
from prooflab.lean import ROOT, LeanSession
from prooflab.models import Candidate, ProofState
from prooflab.native_retrieval import INDEX, RetrievalSession, declarations
from prooflab.outcome_features import compact, features as old_features, similarity
from prooflab.phase3_data import digest

MODEL = ROOT / "models/phase5/retrieval.json"
VERSION = "native-retrieval-v1"
MODES = (
    "original",
    "phase4",
    "broad",
    "type_filtered",
    "typed",
    "learned",
    "no_witness",
    "no_normalize",
)


def features(state: ProofState, candidate: Candidate, row: dict[str, Any]) -> dict[str, float]:
    result = old_features(state, candidate)
    if not state.goals:
        return result
    target = state.goals[0].target.text
    context = [h.type.text for h in state.goals[0].hypotheses if h.is_proof]
    premises = row.get("premises", [])
    extra = {
        "compatible": float(row.get("compatible", False)),
        "premises": min(len(premises), 6) / 6,
        "unresolved_data": min(row.get("unresolved_explicit_data", 0), 6) / 6,
        "missing_instances": min(row.get("missing_instances", 0), 3) / 3,
        "premise_exact": sum(compact(p) in {compact(h) for h in context} for p in premises)
        / max(1, len(premises)),
        "premise_overlap": sum(
            max((similarity(p, h) for h in context), default=0) for p in premises
        )
        / max(1, len(premises)),
        "repeats_target": float(any(compact(p) == compact(target) for p in premises)),
        "witness_depth": min(row.get("construction_depth", 0), 2) / 2,
        "rewrite_obligations": min(row.get("rewrite_obligations", 0), 6) / 6,
        "rewrite_delta": max(
            -1, min(1, (len(target) - len(row.get("rewritten_target", target))) / 100)
        ),
        "implicit_parameters": min(row.get("implicit_parameters", 0), 10) / 10,
        "instance_parameters": min(row.get("instance_parameters", 0), 4) / 4,
    }
    extra.update(
        {
            "family:" + f: float(row.get("family") == f)
            for f in ("lemma", "rewrite", "witness", "normalizer", "original")
        }
    )
    result.update({"retrieval:" + k: float(v) for k, v in extra.items()})
    return result


def relevance(state: ProofState, candidate: Candidate, row: dict[str, Any]) -> float:
    f = features(state, candidate, row)
    r = lambda name: f.get("retrieval:" + name, 0)  # noqa: E731
    return (
        8 * r("compatible")
        + 5 * r("family:witness")
        + 4 * r("family:normalizer")
        + 3 * r("premise_exact")
        + r("premise_overlap")
        + 2 * r("rewrite_delta")
        - 8 * r("unresolved_data")
        - 3 * r("premises")
        - 5 * r("repeats_target")
        - 2 * r("rewrite_obligations")
    )


class RetrievalRanker:
    def __init__(self, path: Path = MODEL) -> None:
        self.artifact: dict[str, Any] = json.loads(path.read_text())
        if self.artifact["feature_version"] != VERSION or self.artifact["evaluation_accessed"]:
            raise ValueError("Invalid or test-trained retrieval artifact")
        self.sha256 = digest(path)
        self.weights: dict[str, float] = self.artifact["weights"]

    def explain(
        self, state: ProofState, candidate: Candidate, row: dict[str, Any]
    ) -> list[tuple[str, float]]:
        terms = [
            (n, v * self.weights.get(n, 0)) for n, v in features(state, candidate, row).items()
        ]
        return sorted(terms, key=lambda x: -abs(x[1]))[:8]

    def score(self, state: ProofState, candidate: Candidate, row: dict[str, Any]) -> float:
        score = sum(v * self.weights.get(n, 0) for n, v in features(state, candidate, row).items())
        if not math.isfinite(score):
            raise ValueError("Nonfinite retrieval score")
        return score


class TypedProvider:
    def __init__(self, mode: str = "typed", ranker: RetrievalRanker | None = None) -> None:
        if mode not in MODES:
            raise ValueError("Unknown retrieval mode")
        self.mode, self.ranker = mode, ranker
        if mode == "learned" and ranker is None:
            self.ranker = RetrievalRanker()
        self.index = {r["name"]: r for r in declarations()}
        self.index_hash = digest(INDEX)

    def generate(
        self,
        lean: LeanSession,
        state: ProofState,
        limit: int,
        forbidden: frozenset[str],
        timeout: float,
    ) -> tuple[list[Candidate], dict[str, Any]]:
        original = generate_candidates(state, limit, forbidden)
        if self.mode in ("original", "phase4"):
            chosen = (
                original
                if self.mode == "original"
                else extended_candidates(state, limit, forbidden)
            )
            return chosen, dict(
                mode=self.mode,
                selected=[c.tactic for c in chosen],
                original=[c.tactic for c in original],
                displaced=[
                    c.tactic for c in original if c.tactic not in {x.tactic for x in chosen}
                ],
                query_wall_s=0,
                pool=[],
            )
        if not isinstance(lean, RetrievalSession):
            raise TypeError("Typed retrieval requires a native RetrievalSession")
        tick = time.monotonic()
        names = [
            n
            for n in self.index
            if n not in forbidden and not any(n.endswith("." + x) for x in forbidden)
        ]
        native = lean.retrieve(state.state_id, names, timeout)
        query_wall = time.monotonic() - tick
        rows = []
        for item in native["rows"]:
            if "tactic" not in item:
                continue
            info = self.index.get(item.get("declaration"), {})
            rows.append({**info, **item})
        # Strong symbolic work is explicit and separately ablated. No Aesop/grind.
        classes = native["classes"]
        if (
            state.goals
            and state.goals[0].target.head == "Eq"
            and any(c in classes for c in ("Group", "CommGroup"))
        ):
            rows.append(
                dict(
                    tactic="simp only [mul_assoc, mul_one, one_mul, mul_inv_cancel, inv_mul_cancel, mul_inv_cancel_left, mul_inv_cancel_right] at *",
                    family="normalizer",
                    compatible=True,
                    compatibility_kind="structure-gated proposal; actual tactic may reject",
                    source_module="Mathlib.Algebra.Group.Defs",
                )
            )
        if state.goals and any(
            t in state.goals[0].target.text for t in ("∩", "∪", "⁻¹'", "\\", "∈")
        ):
            rows.append(
                dict(
                    tactic="simp only [Set.mem_inter_iff, Set.mem_union, Set.mem_diff] at *",
                    family="normalizer",
                    compatible=True,
                    compatibility_kind="visible set structure proposal; actual tactic may reject",
                    source_module="Mathlib.Data.Set.Defs",
                )
            )
        all_rows = {r["tactic"]: r for r in rows}
        # Protect up to 16 original actions, with all structural/specialized actions
        # considered first. Fixed novelty lanes use only the remaining cap.
        protected_order = sorted(
            enumerate(original), key=lambda x: (x[1].category not in ("goal", "specialized"), x[0])
        )
        protected = [c for _, c in protected_order[: min(16, limit)]]
        protected_set = {c.tactic for c in protected}
        additions = []
        for row in rows:
            tactic, family = row["tactic"], row["family"]
            if tactic in protected_set:
                continue
            if self.mode != "broad" and not row.get("compatible", False):
                continue
            if self.mode == "no_witness" and family == "witness":
                continue
            if self.mode == "no_normalize" and family == "normalizer":
                continue
            candidate = next((c for c in original if c.tactic == tactic), None) or Candidate(
                tactic=tactic,
                category="goal"
                if family == "witness"
                else "specialized"
                if family == "normalizer"
                else "lemma",
                lemma=row.get("declaration"),
                provenance=row.get("source_module", "native context construction"),
                prior=7
                if family == "witness"
                else 8
                if family == "normalizer"
                else 5
                if family == "rewrite"
                else 4,
                reason=f"Native {family} proposal; compatibility does not certify usefulness",
            )
            additions.append(candidate)
        additions = list({c.tactic: c for c in additions}.values())
        scored = []
        for candidate in [*original, *additions]:
            row = all_rows.get(candidate.tactic, dict(family="original"))
            score = relevance(state, candidate, row)
            learned = self.ranker.score(state, candidate, row) if self.ranker else None
            scored.append(
                dict(
                    candidate=candidate.model_dump(),
                    **row,
                    deterministic_score=score,
                    learned_score=learned,
                    learned_contributions=self.ranker.explain(state, candidate, row)
                    if self.ranker
                    else [],
                )
            )
        score_map = {r["candidate"]["tactic"]: r for r in scored}
        if self.mode not in ("broad", "type_filtered"):
            additions.sort(
                key=lambda c: (
                    -(
                        score_map[c.tactic]["learned_score"]
                        if self.mode == "learned"
                        else score_map[c.tactic]["deterministic_score"]
                    )
                )
            )
        chosen = [*protected, *additions[: max(0, limit - len(protected))]]
        # If few eligible novel proposals exist, preserve unused original actions.
        occupied = {c.tactic for c in chosen}
        chosen.extend(c for c in original if c.tactic not in occupied)
        chosen = chosen[:limit]
        selected = {c.tactic for c in chosen}
        for r in scored:
            r["selected"] = r["candidate"]["tactic"] in selected
            r["protected"] = r["candidate"]["tactic"] in protected_set
            r["selection_reason"] = (
                "protected original lane"
                if r["protected"]
                else "novelty lane under cap"
                if r["selected"]
                else "outside capped selection"
            )
        return chosen, dict(
            mode=self.mode,
            index_sha256=self.index_hash,
            model_sha256=self.ranker.sha256 if self.ranker else None,
            native=native,
            query_wall_s=query_wall,
            pool=scored,
            selected=[c.tactic for c in chosen],
            original=[c.tactic for c in original],
            displaced=[c.tactic for c in original if c.tactic not in selected],
            entered=[c.tactic for c in chosen if c.tactic not in {x.tactic for x in original}],
            allocation="up to 16 original structural/specialized-first; remaining novelty; original backfill; stable ties",
        )
