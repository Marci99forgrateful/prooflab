"""Pre-execution state/action features; text estimates never certify equality.

No successor-state values, rollout labels, theorem IDs, or extra Lean queries
are available to deployed scoring. Native successors are offline evidence only.
"""

from __future__ import annotations

import re

from prooflab.features import FEATURE_NAMES as OLD_NAMES
from prooflab.features import OPERATIONS, compact, extract_features, operation
from prooflab.models import Candidate, ProofState

VERSION = "prooflab-preaction-outcome-v1"
EXTRA = (
    "assumption_exact",
    "assumption_head_coverage",
    "projection_exact",
    "projection_head",
    "apply_conclusion_exact",
    "apply_premise_hits",
    "apply_repeats_goal",
    "apply_conclusion_overlap",
    "rewrite_occurrences",
    "rewrite_closes_text",
    "rewrite_reflexive_text",
    "rewrite_context_gain",
    "rewrite_size_delta",
    "intro_forall",
    "constructor_conjunction",
    "cases_target_overlap",
    "closing_multigoal",
    "estimated_goal_delta",
    "rfl_text_equal",
)
FEATURE_NAMES = (
    OLD_NAMES
    | frozenset("p3:" + n for n in EXTRA)
    | frozenset("p3:action_goals:" + o for o in OPERATIONS)
)


def strip_outer(text: str) -> str:
    text = text.strip()
    while text.startswith("(") and text.endswith(")"):
        depth = 0
        outer = True
        for i, c in enumerate(text):
            depth += (c == "(") - (c == ")")
            if depth == 0 and i < len(text) - 1:
                outer = False
                break
        if not outer:
            break
        text = text[1:-1].strip()
    return text


def top_split(text: str, token: str) -> list[str]:
    text = strip_outer(text)
    depth = 0
    positions = []
    for i, c in enumerate(text):
        depth += (c in "([{") - (c in ")]}")
        if depth == 0 and text.startswith(token, i):
            positions.append(i)
    if not positions:
        return [text]
    result = []
    start = 0
    for i in positions:
        result.append(strip_outer(text[start:i]))
        start = i + len(token)
    result.append(strip_outer(text[start:]))
    return result


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+|[∈≤∧∨=]", text))


def similarity(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    return len(a & b) / max(1, len(a | b))


def replace_term(text: str, left: str, right: str) -> tuple[str, int]:
    if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9']*", left):
        pattern = r"(?<![\w'])" + re.escape(left) + r"(?![\w'])"
        return re.subn(pattern, lambda _: right, text)
    # A syntactic estimate for compound pretty-printed terms, not Lean reduction.
    count = text.count(left) if left else 0
    return text.replace(left, right) if left else text, count


def features(state: ProofState, candidate: Candidate, mode: str = "full") -> dict[str, float]:
    result = extract_features(state, candidate)
    if mode == "old" or not state.goals:
        return result
    if mode != "full":
        raise ValueError("Unknown Phase 3 representation")
    goal = state.goals[0]
    target = goal.target.text
    op = operation(candidate)
    context = [h for h in goal.hypotheses if h.is_proof]
    types = {compact(h.type.text) for h in context}
    extra: dict[str, float] = {"action_goals:" + op: min(len(state.goals), 8) / 8}
    reference = re.search(
        r"(?:apply|exact|rcases)\s+([A-Za-z_][A-Za-z_0-9']*)(?:\.([12]))?", candidate.tactic
    )
    if op in ("rewrite", "reverse_rewrite"):
        reference = re.search(r"\[(?:←\s*)?([A-Za-z_][A-Za-z_0-9']*)\]", candidate.tactic)
    hyp = next((h for h in context if reference and h.name == reference.group(1)), None)
    if op == "assumption":
        extra["assumption_exact"] = float(compact(target) in types)
        extra["assumption_head_coverage"] = sum(
            h.type.head == goal.target.head for h in context
        ) / max(1, len(context))
        extra["closing_multigoal"] = float(compact(target) in types) * min(len(state.goals), 8) / 8
        extra["estimated_goal_delta"] = -float(compact(target) in types)
    if op == "rfl":
        sides = top_split(target, "=")
        equal = len(sides) == 2 and compact(sides[0]) == compact(sides[1])
        extra["rfl_text_equal"] = float(equal)
        extra["estimated_goal_delta"] = -float(equal)
    if op == "intro":
        extra["intro_forall"] = float(goal.target.forall)
    if op == "constructor":
        extra["constructor_conjunction"] = float(goal.target.head in ("And", "Iff"))
        extra["estimated_goal_delta"] = float(goal.target.head in ("And", "Iff"))
    if hyp is not None:
        typ = hyp.type.text
        if op == "hyp_apply" and reference and len(reference.groups()) > 1 and reference.group(2):
            components = top_split(typ, "∧")
            typ = components[0] if reference.group(2) == "1" else " ∧ ".join(components[1:])
        if op == "projection":
            side = int(reference.group(2) or 1) if reference else 1
            parts = top_split(typ, "∧")
            projected = parts[0] if side == 1 else " ∧ ".join(parts[1:])
            extra["projection_exact"] = float(compact(projected) == compact(target))
            extra["projection_head"] = float(hyp.type.head == goal.target.head)
            extra["estimated_goal_delta"] = -extra["projection_exact"]
        if op == "hyp_apply":
            parts = top_split(typ, "→")
            extra["apply_conclusion_exact"] = float(compact(parts[-1]) == compact(target))
            extra["apply_premise_hits"] = sum(compact(p) in types for p in parts[:-1]) / max(
                1, len(parts) - 1
            )
            extra["apply_repeats_goal"] = float(
                any(compact(p) == compact(target) for p in parts[:-1])
            )
            extra["apply_conclusion_overlap"] = similarity(parts[-1], target)
            extra["estimated_goal_delta"] = min(5, len(parts) - 2) / 5
        if op in ("rewrite", "reverse_rewrite"):
            sides = top_split(typ, "=")
            if len(sides) == 2:
                left, right = sides if op == "rewrite" else sides[::-1]
                rewritten, count = replace_term(target, left, right)
                eq = top_split(rewritten, "=")
                extra["rewrite_occurrences"] = min(count, 8) / 8
                extra["rewrite_closes_text"] = float(compact(rewritten) in types)
                extra["rewrite_reflexive_text"] = float(
                    len(eq) == 2 and compact(eq[0]) == compact(eq[1])
                )
                extra["rewrite_size_delta"] = max(-1, min(1, (len(rewritten) - len(target)) / 200))
                extra["rewrite_context_gain"] = max(
                    (
                        similarity(rewritten, h.type.text) - similarity(target, h.type.text)
                        for h in context
                    ),
                    default=0,
                )
        if op == "cases":
            extra["cases_target_overlap"] = similarity(typ, target)
    result.update({"p3:" + name: value for name, value in extra.items() if value})
    if not set(result) <= FEATURE_NAMES:
        raise ValueError("Unversioned Phase 3 feature")
    return result
