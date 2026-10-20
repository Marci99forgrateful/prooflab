# ruff: noqa: E501
"""Render actual factorial evidence; no assumed performance improvement."""

from __future__ import annotations

import json
from typing import Any

from prooflab.lean import ROOT
from prooflab.phase5_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def interval(values: list[float], scale: float = 1) -> str:
    return "[" + ", ".join(f"{v * scale:+.3f}" for v in values) + "]" if values else "unavailable"


def point(row: dict[str, Any], scale: float = 1) -> str:
    value = row["mean_difference"]
    return f"{value * scale:+.3f}" if value is not None else "unavailable"


def main() -> None:
    summary = read_json(EXPERIMENT / "summary-canonical.json")
    analysis = read_json(EXPERIMENT / "analysis.json")
    training = read_json(ROOT / "models/phase5/training-report.json")
    frozen = read_json(ROOT / "models/phase5/frozen.json")
    storage = read_json(EXPERIMENT / "trace-storage.json")
    results = summary["results"]
    comparisons = summary["comparisons"]
    lines = [
        "# Phase 5 experimental results",
        "",
        "All values below derive from 1120 saved genuine searches on forty original held-out statements in ten families. Every reported success includes a fresh Lean kernel check and transitive axiom audit. No model, generator, index or budget was changed after test access.",
        "",
        "The outer cap is 24 candidates, 600 attempts, eighty expanded states, depth twelve and eighteen seconds, with two seconds per tactic/query. Primary arms repeat twice; ablations once. Aesop/grind receive one external call with that same **two-second per-call cap**, not eighteen seconds of internal engine search. Their internal attempt/state units differ.",
        "",
        "| Generator × scheduler | Verified runs | Success % (theorem bootstrap 95% interval) | Mean attempts | Mean expanded | Mean wall s | Mean retrieval s | Resource-limit runs | Execution errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, row in results.items():
        m = row["metrics"]
        reference = arm in ("automation", "grind")
        success = interval(row["success_ci95"], 100).replace("+", "")
        attempts = "1 external call" if reference else f"{m['attempted_candidates']['mean']:.3f}"
        expanded = "internal separate" if reference else f"{m['expanded_states']['mean']:.3f}"
        limits = sum(v for k, v in row["terminations"].items() if k.startswith("resource_limit:"))
        errors = sum(
            v
            for k, v in row["terminations"].items()
            if k in ("execution_error", "independent_verification_failed")
        )
        lines.append(
            f"| {arm} | {row['verified']}/{row['runs']} | {100 * row['success_rate']:.1f} {success} | {attempts} | {expanded} | {m['elapsed_s']['mean']:.3f} | {m['retrieval_s']['mean']:.4f} | {limits} | {errors} |"
        )
    lines += [
        "",
        "All-run effort mixes verified and bounded-failure executions. A smaller attempt mean is not automatically a success/efficiency improvement. Full per-run time, native allocation counters, partial CPU/RSS measurements and proof lengths are in `results.csv` and `summary.json`. The initial regression log completed 0.350s before campaign start; its duration was not overlap. The host was shared with light engineering work. Timing is observational, not a controlled hardware speedup experiment.",
        "",
        "A reporting-only reproducibility correction preserves the raw frozen `summary.json` and writes `summary-canonical.json`: family identifiers are sorted before the seeded bootstrap. The raw intermediate set was hash-order dependent. All run outcomes, metrics, theorem bootstrap and training/search decisions are unchanged; `statistics-correction.json` links the reports.",
        "",
        "## Predeclared paired comparisons",
        "",
        "Success differences use theorem averages across repetitions, with paired theorem resampling and equal-family cluster sensitivity (10,000 draws, seed 2718). Effort is also reported on the common-verified subset. When this subset has uneven family sizes, the equal-family sensitivity interval has a different point estimand; `analysis.json/family_sensitivity` records both points. It must not be interpreted as a second interval for the same theorem-weighted mean.",
        "",
        "| Left minus right | Verified-success difference pp | Theorem interval | Family sensitivity interval | Common-verified theorems | Common-success attempts difference | Theorem interval |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, c in comparisons.items():
        effort = c["common_verified"]["attempted_candidates"]
        success = c["success"]
        lines.append(
            f"| {name} | {point(success, 100)} | {interval(success['ci95_theorem'], 100)} | {interval(success['ci95_family'], 100)} | {effort['theorems']} | {point(effort)} | {interval(effort['ci95_theorem'])} |"
        )
    lines += [
        "",
        "These are finite-benchmark estimates, not proof of general superiority. Common-success effort is conditioned on success and can change its theorem population between comparisons. Secondary contrasts are descriptive; the primary ML contrast is learned retrieval versus deterministic typed retrieval with Phase 3 scheduling.",
        "",
        "## Actual applicability and partial useful availability",
        "",
        "The following native-compatible acceptance ratio concerns **actually attempted** proposals with a native compatibility annotation. It excludes structure-gated normalizers and excludes resource/tool errors from its acceptance denominator. Unselected actions and selected-but-unexecuted actions have unknown outcomes. Compatibility and Lean acceptance are not downstream usefulness.",
        "",
        "| Arm | Compatible accepted / attempted excluding errors | Compatible rejected | Incompatible but accepted | Selected actions left unexplored | Entered / displaced occurrences |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm, count in analysis["applications"].items():
        a = count.get("compatible_accepted", 0)
        b = count.get("compatible_rejected", 0)
        lines.append(
            f"| {arm} | {a}/{a + b} | {b} | {count.get('incompatible_accepted', 0)} | {count.get('selected_unexplored', 0)} | {count.get('entered', 0)} / {count.get('displaced', 0)} |"
        )
    lines += [
        "",
        "Useful-action availability is partial witnessed recall: collect next actions from audited complete ProofLab paths, then compare capped pools only at the identical theorem and exact tactic prefix. Printed-state similarity is never used to transport a proof. The `availability` record links every matched state and actual action; `analysis.json/stratified_partial_availability` separates witnesses, normalization, broad `simp_all` and other structural/lemma actions. Strong simplifier actions must not be mistaken for learned retrieval gains. Unmatched/unexplored states have no mathematical-negative label.",
        "",
        "## Family results",
        "",
        "| Family | Original P3 | Expanded P3 | Typed P3 | Learned P3 | Typed joint | Aesop | grind |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    primary = [
        "original_p3",
        "phase4_p3",
        "typed_p3",
        "learned_p3",
        "typed_joint",
        "automation",
        "grind",
    ]
    for family in sorted(next(iter(results.values()))["families"]):
        values = [results[a]["families"][family] for a in primary]
        lines.append(
            "| "
            + family
            + " | "
            + " | ".join(f"{v['verified']}/{v['runs']}" for v in values)
            + " |"
        )
    lines += [
        "",
        "## Per-theorem results",
        "",
        "Entries are verified repetitions / recorded repetitions. Attempt pairs remain in the per-theorem JSON and per-run CSV, including all unsolved tasks.",
        "",
        "| Theorem | Original P3 | Expanded P3 | Typed P3 | Learned P3 | Typed joint | Aesop | grind |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    table = {(r["task_id"], r["arm"]): r for r in summary["per_theorem"]}
    for task in sorted({r["task_id"] for r in summary["per_theorem"]}):
        values = [table[(task, a)] for a in primary]
        lines.append(
            "| "
            + task
            + " | "
            + " | ".join(f"{v['verified']}/{v['repetitions']}" for v in values)
            + " |"
        )
    lines += [
        "",
        "## Repetition, resources and provenance",
        "",
        f"There are **{len(analysis['repeat_disagreements'])}** task/arm pairs with a repeated-run difference in success, termination, proof, attempt count or expanded states. The exact disagreements and trace hashes are retained in `analysis.json`; wall-time differences alone are not counted as structural disagreements.",
        "",
        f"Matched native error-message term counts: `{json.dumps(analysis['native_resource_error_messages'], sort_keys=True)}`. Outer resource limits are separately counted above; a resource limit is neither a mathematical counterexample nor automatically a code failure.",
        "",
        f"Canonical archive: {len(storage['traces'])} exact JSON traces; {storage['raw_bytes'] / 1e9:.3f} GB uncompressed / {storage['stored_bytes'] / 1e6:.3f} MB retained gzip. Raw and compressed SHA-256 hashes are indexed. Static export reuses gzip archives rather than duplicating gigabytes of unpacked JSON.",
        "",
        f"Execution freeze source commit `{frozen['code_commit']}`; test runner commit is in `provenance.json`. Lean 4.24.0, Mathlib `f897ebcf72cd16f89ab4577d0c826cd14afaafc7`. Model, index, dataset, protocol, old policy artifacts and executable sources are hash-addressed. Earlier Phase 1–4 evidence is unchanged.",
        "",
        "Live session-tree CPU plus coordinator CPU are partial resource accounting; fresh verifier CPU/RSS and post-run serialization are excluded. Summed process high-water RSS is a bound, not simultaneous peak physical memory. Allocation heartbeats are resource proxies, never primitive inference counts. See the reproducibility document for measurement scopes and limitations.",
        "",
        "![Actual verified success, conditional effort and time components](assets/phase5-results.png)",
        "",
        "[Standalone SVG](assets/phase5-results.svg) · [PDF](assets/phase5-results.pdf) · [Canonical statistics](../experiments/phase5/evaluation-v1/summary-canonical.json) · [Raw frozen summary](../experiments/phase5/evaluation-v1/summary.json) · [Analysis](../experiments/phase5/evaluation-v1/analysis.json) · [Per-run CSV](../experiments/phase5/evaluation-v1/results.csv)",
    ]
    (ROOT / "docs/phase-5-results.md").write_text("\n".join(lines) + "\n")
    report = [
        "# ProofLab v0.5.0 — Phase 5 final report",
        "",
        "Phase 5 implements bounded native type-directed retrieval, structured witness generation and development-trained local retrieval ranking. It separates candidate expressiveness, pool selection, action order, frontier scheduling and external automation. The numerical findings below are the actual frozen experiment, not a required improvement target.",
        "",
        "**Main finding:** the learned retriever does not improve verified success over deterministic typed retrieval (15/40 each in both repeats), and its common-success effort is worse on one group-context theorem. The stronger Phase 4 expanded generator solves 29/40, while native Aesop solves 31/40. The new typed component improves expressiveness in real witness cases but fails to control branching well enough to establish broad search improvement.",
        "",
        "## Delivered functionality",
        "",
        "- A focused extension of the 29-system Phase 4 survey, including individually pinned Lean/Aesop/Mathlib modules and seven additional/revisited ReProver, LeanHammer, Duper and TacticToe source checks. No external implementation, pretrained model or solution archive is copied.",
        "- A native index of 116 declarations beyond the original 24-lemma corpus, with exact types, implicit/instance/premise information, source modules, compatibility probes, rewrite direction checks and bounded cost accounting.",
        "- Typed local-function witnesses including `f a` and unary compositions, bounded product constructors and Nat literals. Explicit noncommutative group/set normalizers; original logic, local hypotheses, order/set/algebra rules and old specialized tactics remain available.",
        "- Fixed-cap protected original lanes, novelty selection, backfill and actual entered/displaced candidate records; broad, type-filtered, deterministic, learned, witness and normalization controls.",
        f"- A real 130-coefficient CPU pairwise model: {training['preferences']} observed preferences, {training['cost_preferences']} verified continuation-cost preferences, {training['theorems']} contributing development theorems. Accepted unknown/censored alternatives are never mathematical negatives. Development validation selects L2=0.01 before final testing; saved-data refitting is byte-identical.",
        "- Forty original frozen tests in ten families; 212 native typed structural audit trees, no duplicate pairs, explicit semantic-audit limits and immutable earlier evidence.",
        "- 1120 actual searches: four generators crossed with handcrafted/Phase 3 scheduling, a frozen Phase 4 joint-frontier subset, separate Aesop/grind references and four single-run ablations.",
        "- Premise & Candidate Explorer integrated into the existing Architecture Explorer: native states/types, lemma provenance, witnesses, compatibility, retrieval/scheduler ranks and contributions, actual outcomes, pool displacement, costs, real trees/proofs, static replay, mobile layout, local computation and JSON exports.",
        "",
        "## Verified quantitative evidence",
        "",
    ]
    for arm in (
        "original_p3",
        "phase4_p3",
        "typed_p3",
        "learned_p3",
        "typed_joint",
        "learned_joint",
        "automation",
        "grind",
    ):
        row = results[arm]
        report.append(
            f"- `{arm}`: **{row['verified']}/{row['runs']}** independently verified runs; mean {row['metrics']['attempted_candidates']['mean']:.3f} calls/attempts, {row['metrics']['elapsed_s']['mean']:.3f}s wall. External references have incomparable internal work units."
        )
    main_comparison = comparisons["learned_p3 minus typed_p3"]
    effort = main_comparison["common_verified"]["attempted_candidates"]
    report += [
        "",
        f"The primary ML success difference is **{point(main_comparison['success'], 100)} percentage points**, theorem interval {interval(main_comparison['success']['ci95_theorem'], 100)}, family sensitivity {interval(main_comparison['success']['ci95_family'], 100)}. On {effort['theorems']} common-verified theorems, the observed mean attempt difference is {point(effort)} with theorem interval {interval(effort['ci95_theorem'])}. This conditional comparison is not an unconditional efficiency claim.",
        "",
        "The [complete results](phase-5-results.md) include every arm, per-family/per-theorem outcomes, repeated-run stability, actual applicability, partial witnessed availability, uncertainty and raw trace links. The following descriptive gains/regressions were selected after evaluation for explanation; they never changed training or search.",
        "",
    ]
    for name, cases in analysis["case_studies"].items():
        gains = [r["task_id"] for r in cases["success_gains"]]
        bad = [r["task_id"] for r in cases["success_regressions"]]
        report.append(
            f"- `{name}`: success gains {', '.join(gains) or 'none'}; regressions {', '.join(bad) or 'none'}. Complete actual proofs, failed traces and effort differences are in the case-study artifact."
        )
    report += [
        "",
        "[Detailed error/intervention analysis](phase-5-error-analysis.md) identifies the exact Group normalizer displaced by `Or.elim`: 157 versus 485 attempts. At 2736/2738 matched P3 prefixes the candidate set is identical and only stable downstream ties change; the two membership changes are this same regression in the two repeats. The development corpus contains no Group/Lattice states. These facts limit any pure-availability attribution.",
        "",
        "## Mechanisms and limits",
        "",
        "The reused Phase 4 witness failure is repaired by native `f a` construction and an audited three-step proof. The cubic regression persists; typed root original actions are retained, while extra generic/rewrite branches consume the finite search budget. Lattice indexing alone does not guarantee an efficient transitivity/projection sequence. Group normalization supplies symbolic mathematical power and is explicitly ablated. These diagnostic observations are excluded from fresh test scores and training.",
        "",
        "A type-compatible rule can create irrelevant or underconstrained subgoals. An accepted step may remain unproductive or unknown. The small development corpus mostly follows old source paths, and only eighty preferences compare completed continuation costs. The model learns finite-policy evidence, not optimal mathematical relevance. The index is bounded, some image/preimage declarations are unavailable in the unchanged imports, witness functions/terms/depth are capped, and constructed partial applications are not promoted to a callable bank. No arbitrary-equivalence pruning, complete Mathlib retrieval, GPU/pretrained embedding model or new foundational prover is claimed.",
        "",
        "All timing is shared-host evidence; the initial regression completed before campaign start, and a previous draft overlap assumption is corrected in the timing-note artifact. External references have a two-second per-call cap and opaque internal work. CPU/RSS coverage is partial. Family-balanced sensitivity and theorem-weighted common-success effort are distinct estimands. The ten small families do not establish broad real-world theorem-proving generalization.",
        "",
        "The frozen raw family-bootstrap iteration was hash-order dependent. A separate canonical derived report sorts family IDs; original results are retained, theorem metrics are unchanged, and the correction never feeds model/search selection. This reporting correction and the distinct family-balanced point estimand are documented explicitly.",
        "",
        "## Reproduction, validation and review",
        "",
        "[Model/features/labels](phase-5-model.md) · [Data/protocol boundary](phase-5-data.md) · [Source comparison](phase-5-related-work.md) · [Phase 4 coverage diagnosis](phase-5-coverage.md) · [Exact commands and scopes](phase-5-reproduction.md).",
        "",
        "Local and hosted validation evidence is recorded separately in `artifacts/phase5-validation.json` and `artifacts/phase5-hosted-ci.json`. Hosted run 39498108456 passed all 106 tests after the historical CSV checkout rule restored already-frozen CRLF bytes; no data, checksum, model or search budget changed. See [CI investigation](phase-5-ci.md). The delivery branch is `feature/phase5-type-directed-retrieval`, with a draft pull request targeting `feature/phase4-search-architecture`. Main, MathVerify and the Phase 4 branch are not merged or modified.",
    ]
    (ROOT / "docs/phase-5-final-report.md").write_text("\n".join(report) + "\n")
    print("Rendered actual Phase 5 results and final report")


if __name__ == "__main__":
    main()
