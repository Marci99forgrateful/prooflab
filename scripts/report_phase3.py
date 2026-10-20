"""Measured Phase 3 tables, cluster sensitivity and actual qualitative examples."""

# Literal generated-report prose is kept intact.
# ruff: noqa: E501
from __future__ import annotations

import csv
import json
import random
import re
import statistics
from collections import Counter

from prooflab.evaluation import interval
from prooflab.lean import ROOT
from prooflab.research import DIAGNOSTICS
from prooflab.research_io import read_json, trace_paths

NAMES = {
    "bfs": "Breadth-first",
    "best_first": "Handcrafted",
    "learned": "Phase 2",
    "outcome": "Phase 3 outcome",
    "automation": "Native Aesop",
    "applicability_only": "No outcome signal",
    "old_features_outcome": "Old features + outcomes",
}
DIRECTORY = ROOT / "experiments/phase3/evaluation-v1"


def ci(value: dict, factor: float = 1) -> str:
    return f"{factor * value['estimate']:+.3f} [{factor * value['lower']:+.3f}, {factor * value['upper']:+.3f}]"


def main() -> None:
    report = read_json(DIRECTORY / "summary.json")
    families = sorted({r["family"] for r in report["per_theorem"].values()})
    family_rng = random.Random(2718)
    family_samples = [[family_rng.randrange(len(families)) for _ in families] for _ in range(10000)]
    sensitivity = {
        "label": "Supplementary family-cluster sensitivity; added after selection, no model/test retuning",
        "clusters": families,
        "comparisons": {},
    }
    for baseline in ("best_first", "learned", "applicability_only", "old_features_outcome"):
        values = [
            statistics.mean(
                row["algorithms"]["outcome"]["attempted_candidates"]
                - row["algorithms"][baseline]["attempted_candidates"]
                for row in report["per_theorem"].values()
                if row["family"] == family
            )
            for family in families
        ]
        sensitivity["comparisons"][baseline] = interval(values, family_samples)
    (DIRECTORY / "family-sensitivity.json").write_text(json.dumps(sensitivity, indent=2) + "\n")
    rows = list(csv.DictReader((DIRECTORY / "results.csv").open()))
    structural = {}
    for row in rows:
        key = (row["task"], row["algorithm"])
        structural.setdefault(key, set()).add(
            (row["status"], row["attempted_candidates"], row["expanded_states"])
        )
    stats = {
        "structural_repetitions_identical": all(len(v) == 1 for v in structural.values()),
        "common_verified_intervals": {},
        "verified_mean_proof_lengths": {},
        "native_resource_messages": {},
    }
    rng = random.Random(2718)
    for baseline, delta in report["paired_differences"].items():
        tasks = delta["common_verified_tasks"]
        values = [
            report["per_theorem"][t]["algorithms"]["outcome"]["attempted_candidates"]
            - report["per_theorem"][t]["algorithms"][baseline]["attempted_candidates"]
            for t in tasks
        ]
        samples = [[rng.randrange(len(tasks)) for _ in tasks] for _ in range(10000)]
        stats["common_verified_intervals"][baseline] = interval(values, samples) if tasks else None
    for algorithm in NAMES:
        lengths = [
            float(r["proof_length"])
            for r in rows
            if r["algorithm"] == algorithm and r["status"] == "verified"
        ]
        stats["verified_mean_proof_lengths"][algorithm] = (
            statistics.mean(lengths) if lengths else None
        )
    pattern = re.compile(
        r"heartbeats|maximum recursion|maximum number of recursions|timed out|timeout", re.I
    )
    native = Counter()
    chosen = {}
    diagnostics = read_json(DIAGNOSTICS / "manifest.json")["cases"]
    selected = {c["task_id"] for c in diagnostics if c["status"] == "recorded"}
    for path in trace_paths(DIRECTORY / "traces"):
        trace = read_json(path)
        native[trace["algorithm"]] += sum(
            bool(pattern.search(n.get("error") or "")) for n in trace["nodes"]
        )
        if trace["task"]["id"] in selected and trace["metadata"]["repeat"] == "0":
            chosen[(trace["task"]["id"], trace["algorithm"])] = trace
    stats["native_resource_messages"] = dict(native)
    (DIRECTORY / "analysis.json").write_text(json.dumps(stats, indent=2) + "\n")
    lines = [
        "# Phase 3: measured outcome-aware proof search",
        "",
        "The new model learns from genuine valid-alternative futures, but this experiment **does not establish an improvement over the handcrafted or Phase 2 policy**. All three solve 23/32 tasks. The matched-feature ablation shows a small attempt-count benefit from the new signal; its uncertainty crosses zero when resampling the eight theorem families instead of treating all 32 statements as independent clusters. The enhanced representation itself does not establish a benefit and contributes a concrete regression. No model or dataset is retuned after these findings.",
        "",
        "## Controlled experiment",
        "",
        "384 actual searches: 32 statements, five primary policies with two repetitions, and two ablations with one repetition. Counts below include failures. Repeats are execution measurements, not independent mathematical observations. Same generator and primary ProofLab budgets: depth 10, 70 expansions, 24 candidates/state, 500 attempts, 12 seconds wall time, two seconds/tactic. Native Aesop is a separate reference with its own internal search.",
        "",
        "| Policy | Verified runs | Mean attempts | Mean expansions | Verified mean proof length | Mean wall s | Mean search s | Lean interaction s | Audit s | Resource-limited runs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a, g in report["results"].items():
        lines.append(
            f"| {NAMES[a]} | {g['verified']}/{g['attempted']} | {g['mean_candidates']:.3f} | {g['mean_expansions']:.3f} | {stats['verified_mean_proof_lengths'][a]:.3f} | {g['mean_wall_s']:.3f} | {g['metrics']['search_s']['mean']:.3f} | {g['mean_lean_execution_s']:.3f} | {g['metrics']['verification_s']['mean']:.3f} | {g['resource_limits']} |"
        )
    lines += [
        "",
        "There are no execution-error runs. Unsolved tasks and all resource terminations are retained. Native Aesop attempt/expansion counts denote one external call and cannot be compared with its hidden internal work. Search time is elapsed minus startup minus fresh verification, including cleanup overhead. Timings share a host; inference/explanation cost is counted for all ProofLab policies. Each individual component, min/max/median, proof length, termination and family result is exported in JSON/CSV.",
        "",
        "## Paired differences and uncertainty",
        "",
        "Phase 3 minus baseline; lower effort favors Phase 3. Primary intervals use the frozen 10,000-sample theorem-cluster bootstrap (seed 2718), retaining repeated executions together. They describe this curated sample under a theorem-independence assumption.",
        "",
        "| Baseline | Success difference, pp [95% interval] | All-task attempts difference [95% interval] | Expansions difference [95% interval] | Wall s difference [95% interval] |",
        "|---|---|---|---|---|",
    ]
    for a, d in report["paired_differences"].items():
        lines.append(
            f"| {NAMES[a]} | {ci(d['success_rate'], 100)} | {ci(d['attempted_candidates'])} | {ci(d['expanded_states'])} | {ci(d['elapsed_s'])} |"
        )
    lines += [
        "",
        "All-task effort can misleadingly favor a policy that stops early without proving anything. The next table restricts each comparison to theorems verified by both policies in every recorded repeat; these supplementary intervals also resample theorem clusters. Proof lengths in the aggregate table include verified runs only, so zero-length failed searches are never presented as short proofs.",
        "",
        "| Baseline | Common verified theorems | Attempts difference [supplementary 95% interval] |",
        "|---|---:|---|",
    ]
    for a, d in report["paired_differences"].items():
        value = stats["common_verified_intervals"][a]
        lines.append(
            f"| {NAMES[a]} | {len(d['common_verified_tasks'])} | {ci(value) if value else 'insufficient'} |"
        )
    lines += [
        "",
        "### Family-cluster sensitivity",
        "",
        "Four statements within each of eight families can be dependent. This **supplementary analysis was added after selection**, changes no model/data/budget and resamples whole frozen families (all four statements and repeats together). It is more conservative about independent mathematical units. Only eight family clusters remain, so inference is still limited.",
        "",
        "| Baseline | All-task attempt difference [95% family-cluster interval] |",
        "|---|---|",
    ]
    for a, d in sensitivity["comparisons"].items():
        lines.append(f"| {NAMES[a]} | {ci(d)} |")
    lines += [
        "",
        "The matched-feature no-outcome ablation has a theorem-resampled interval below zero, but its family-resampled interval includes zero. This is **suggestive, small sample evidence**, not a robust general gain. The old-feature outcome model has a slightly lower mean attempt count than the full representation; adding features is not automatically an improvement. Success is unchanged across learned/heuristic variants.",
        "",
        "## Mathematical families",
        "",
        "Each entry counts unique theorems verified in **every** recorded repeat, out of four; repeated runs do not enlarge the family sample.",
        "",
        "| Family | BFS | Handcrafted | Phase 2 | Phase 3 | Aesop | No outcome signal | Old features + outcomes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    families = sorted({r["family"] for r in report["per_theorem"].values()})
    for family in families:
        counts = [
            sum(
                r["algorithms"][a]["verified"] == r["algorithms"][a]["runs"]
                for r in report["per_theorem"].values()
                if r["family"] == family
            )
            for a in NAMES
        ]
        lines.append("| " + family + " | " + " | ".join(f"{c}/4" for c in counts) + " |")
    lines += [
        "",
        "## Every theorem, including failures",
        "",
        "Cells show verified repetitions / recorded repetitions followed by mean candidate attempts. The canonical per-run CSV has all timing/proof/resource fields.",
        "",
        "| Theorem | BFS | Handcrafted | Phase 2 | Phase 3 | Aesop | No outcome | Old features + outcomes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for task, row in report["per_theorem"].items():
        cells = [
            f"{row['algorithms'][a]['verified']}/{row['algorithms'][a]['runs']} · {row['algorithms'][a]['attempted_candidates']:.0f}"
            for a in NAMES
        ]
        lines.append("| `" + task + "` | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Actual cases and proof paths",
        "",
        "These cases were selected for illustration **after** frozen evaluation, never used for fitting. Additional bounded rollouts replay an exact prefix in fresh Lean and retain all accepted/rejected candidates and audited completions. Their costs are separate diagnostics under the collection budget, not replacements for primary measurements. Full evidence and both model scores appear in the Alternative continuations view.",
        "",
    ]
    examples = ROOT / "examples/phase3"
    examples.mkdir(exist_ok=True)
    example_manifest = []
    for item in diagnostics:
        if item["status"] != "recorded":
            continue
        ident = item["task_id"]
        case = item["case"]
        a = chosen[(ident, "outcome")]
        b = chosen[(ident, case["baseline"])]
        lines += [
            f"### `{ident}` — {case['kind'].replace('_', ' ')}",
            "",
            f"{NAMES[case['baseline']]} uses {b['metrics']['attempted_candidates']} attempts; Phase 3 uses {a['metrics']['attempted_candidates']}. Verified proof lengths are {len(b['proof'])} and {len(a['proof'])}.",
            "",
            f"{NAMES[case['baseline']]} actual tactic path:",
            "```lean",
            *b["proof"],
            "```",
            "",
            "Phase 3 actual tactic path:",
            "```lean",
            *a["proof"],
            "```",
            "",
        ]
        for algorithm, t in [("outcome", a), (case["baseline"], b)]:
            if t["status"] == "verified":
                filename = f"{ident}--{algorithm}.lean"
                (examples / filename).write_text(t["lean_source"])
                example_manifest.append(
                    {
                        "file": filename,
                        "task_id": ident,
                        "algorithm": algorithm,
                        "source_sha256": t["verification"]["source_sha256"],
                    }
                )
    (examples / "manifest.json").write_text(json.dumps(example_manifest, indent=2) + "\n")
    lines += [
        "### Interpretation of the recorded mechanisms",
        "",
        "- `p3_order_guard`: both learned policies find the same seven-step verified proof, but Phase 3 makes 109 attempts instead of 133. In the diagnostic state after the first transitivity application, the frozen Phase 2 model ranks `apply le_trans` first and `assumption` third. Phase 3 ranks `assumption` first using candidate-conditioned context evidence. Under the diagnostic rollout, that branch verifies at cost 50; the alternative transitivity branch is unresolved within the smaller rollout budget. This is an illustrative trace mechanism, not an isolated causal ablation.",
        "- `p3_monoid_distractor`: both policies ultimately use `rw [h]; apply mul_one`, but Phase 3 needs 39 attempts versus 18 for Phase 2. Its full feature representation places `rw [k]` ahead of `rw [h]`, despite near-equal displayed scores. Diagnostic `rw [h]` completes at cost 9; `rw [k]` remains unresolved under that finite diagnostic budget. The no-outcome ablation uses 33 attempts and the old-feature outcome model 24, so neither adding the signal nor the added representation guarantees improvement on this example.",
        "- `p3_relation_reverse`: BFS finds a four-step proof in 28 attempts. The heuristic and learned scheduling select a different, five-step verified route; Phase 3 uses 40 attempts. The interface compares these actual paths and trees rather than drawing hypothetical alternatives.",
        "",
        "Native resource-message occurrences inside tactic outcomes (separate from run termination counts) are exported in `analysis.json`. No resource-message observation in the development probe corpus is used as an invalid applicability contrast.",
        "",
        "## What this establishes",
        "",
        "The downstream signal is real: 155 preferences compare unequal measured costs of independently verified valid continuations, including 81 nonterminal-versus-nonterminal pairs. The matched-feature objective ablation changes learned weights and observed held-out attempt counts. This is a working outcome-aware system, not a larger applicability model relabeled as progress.",
        "",
        "The experiment establishes no success advantage over the existing heuristic or Phase 2 model. Attempt-count effects are small and cluster-sensitive; the enhanced representation contributes a substantial local regression. Rollout-policy bias, only 36 preference-bearing development theorems, censoring, approximate textual semantics, limited generator coverage and eight curated families constrain conclusions. Unresolved mathematical tasks remain in the dataset. No weights, budgets or test tasks are changed to improve the headline.",
        "",
        "Canonical evidence: [summary and raw traces](../experiments/phase3/evaluation-v1/), [training report](../models/phase3/training-report.json), [model](../models/phase3/outcome.json), [data/protocol](phase-3-data.md), [model methodology](phase-3-model.md).",
        "",
        "![Actual Phase 3 measurements](assets/phase3-results.svg)",
        "",
    ]
    (ROOT / "docs/phase-3-results.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
