"""Versioned state/action features; no theorem IDs, Lean IDs or answer access."""

from __future__ import annotations

import math
import re

from prooflab.candidates import LEMMAS
from prooflab.models import Candidate, ProofState

FEATURE_VERSION = "prooflab-state-action-v1"
SHAPES = ("And", "Or", "Eq", "Exists", "Iff", "False", "forall", "order", "other")
OPERATIONS = (
    "intro",
    "constructor",
    "left",
    "right",
    "assumption",
    "rfl",
    "hyp_apply",
    "lemma_apply",
    "projection",
    "cases",
    "rewrite",
    "reverse_rewrite",
    "ring",
    "omega",
    "exists",
    "other",
)
NUMERIC = (
    "bias",
    "goals",
    "target_length",
    "context_size",
    "proof_context",
    "target_overlap",
    "hyp_conclusion_match",
    "hyp_exact_match",
    "hyp_premise_present",
    "hyp_is_forall",
    "rewrite_occurs",
    "rewrite_reverse_occurs",
    "assumption_available",
    "reflexive_text",
    "conjunction_context",
    "existential_context",
)
FEATURE_NAMES = frozenset(
    [
        *NUMERIC,
        *["shape:" + s for s in SHAPES],
        *["op:" + o for o in OPERATIONS],
        *[f"cross:{s}|{o}" for s in SHAPES for o in OPERATIONS],
        *["lemma:" + lemma.name for lemma in LEMMAS],
    ]
)


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text).strip("()")


def operation(candidate: Candidate) -> str:
    text = candidate.tactic
    first = text.split()[0] if text.split() else "other"
    if first == "rw":
        return "reverse_rewrite" if "←" in text else "rewrite"
    if first == "apply":
        return "lemma_apply" if candidate.lemma else "hyp_apply"
    if first == "exact" and re.search(r"\.[12]$", text):
        return "projection"
    if first in ("rcases", "cases"):
        return "cases"
    return first if first in OPERATIONS else "other"


def extract_features(state: ProofState, candidate: Candidate) -> dict[str, float]:
    if not state.goals:
        return {"bias": 1.0}
    goal = state.goals[0]
    target = goal.target
    shape = (
        target.head
        if target.head in SHAPES
        else (
            "forall"
            if target.forall
            else "order"
            if any(x in target.text for x in ("≤", "<"))
            else "other"
        )
    )
    op = operation(candidate)
    context = [h for h in goal.hypotheses if h.is_proof]
    types = {compact(h.type.text) for h in context}
    result = {
        "bias": 1.0,
        "shape:" + shape: 1.0,
        "op:" + op: 1.0,
        f"cross:{shape}|{op}": 1.0,
        "goals": min(len(state.goals), 8) / 8,
        "target_length": min(len(target.text), 200) / 200,
        "context_size": min(len(goal.hypotheses), 24) / 24,
        "proof_context": min(len(context), 16) / 16,
        "assumption_available": float(compact(target.text) in types),
        "conjunction_context": float(any(h.type.head == "And" for h in context)),
        "existential_context": float(any(h.type.head == "Exists" for h in context)),
    }
    if candidate.lemma:
        result["lemma:" + candidate.lemma] = 1.0
    # Resolve only a local name into its actual Lean-returned type. The name
    # itself never enters the feature vector or artifact vocabulary.
    words = candidate.tactic.split()
    name = (words[1] if len(words) > 1 else "").strip("[]").split(".")[0]
    if op in ("rewrite", "reverse_rewrite"):
        match = re.search(r"\[(?:←\s*)?([A-Za-z_][A-Za-z_0-9']*)\]", candidate.tactic)
        name = match.group(1) if match else ""
    hyp = next((h for h in context if h.name == name), None)
    if hyp is not None:
        typ = hyp.type.text
        conclusion = typ.rsplit("→", 1)[-1]
        result["hyp_conclusion_match"] = float(compact(conclusion) == compact(target.text))
        result["hyp_exact_match"] = float(compact(typ) == compact(target.text))
        result["hyp_is_forall"] = float(hyp.type.forall)
        premise = typ.rsplit("→", 1)[0] if "→" in typ else ""
        result["hyp_premise_present"] = float(compact(premise) in types)
        tokens = set(re.findall(r"\w+|[≤∧∨=]", typ))
        target_tokens = set(re.findall(r"\w+|[≤∧∨=]", target.text))
        result["target_overlap"] = len(tokens & target_tokens) / max(1, len(tokens | target_tokens))
        if "=" in typ:
            left, right = typ.split("=", 1)
            result["rewrite_occurs"] = float(compact(left) in compact(target.text))
            result["rewrite_reverse_occurs"] = float(compact(right) in compact(target.text))
    if "=" in target.text:
        left, right = target.text.split("=", 1)
        result["reflexive_text"] = float(compact(left) == compact(right))
    if not set(result) <= FEATURE_NAMES or not all(math.isfinite(v) for v in result.values()):
        raise ValueError("Invalid feature extraction")
    return {name: value for name, value in result.items() if value != 0}


def dot(weights: dict[str, float], features: dict[str, float]) -> float:
    return math.fsum(weights.get(name, 0) * value for name, value in features.items())
