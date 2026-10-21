# ruff: noqa: E501
"""Render only measured Phase 6 evidence and explicitly conditional conclusions."""

from __future__ import annotations

from prooflab.lean import ROOT
from prooflab.phase6_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def interval(values, scale=1):
    return "[" + ", ".join(f"{x * scale:+.3f}" for x in values) + "]" if values else "unavailable"


def main() -> None:
    s = read_json(EXPERIMENT / "summary.json")
    training = read_json(ROOT / "models/phase6/training-report.json")
    storage = read_json(EXPERIMENT / "trace-storage.json")
    primary = s["comparisons"]["learned minus phase4"]
    diff = primary["success"]
    learning = s["comparisons"]["learned minus deterministic"]["success"]
    established = bool(diff["ci95_theorem"] and diff["ci95_theorem"][0] > 0)
    lines = [
        "# Phase 6 measured results",
        "",
        f"{s['runs']} genuine searches on 48 frozen new statements in twelve families. Every verified success includes a fresh complete-proof Lean check and transitive axiom audit. All failures and unsolved statements are retained.",
        "",
        f"The learned hybrid changes verified success by **{diff['mean_difference'] * 100:+.3f} percentage points** relative to the strongest Phase 4 expanded/P3 reference; paired theorem 95% interval **{interval(diff['ci95_theorem'], 100)}**. "
        + (
            "This finite-sample interval supports a positive success difference."
            if established
            else "This does not establish a positive success difference on this sample."
        ),
        f"The learned-minus-deterministic contrast is **{learning['mean_difference'] * 100:+.3f} pp**, interval **{interval(learning['ci95_theorem'], 100)}**. Symbolic/candidate gains are not attributed automatically to learning.",
        "",
        "| Policy | Verified runs | Theorem success % [95% interval] | Mean attempts/calls | Mean expansions | Wall s | Lean s | Retrieval s | Inference s | Resource limits | Execution errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, r in s["results"].items():
        m = r["metrics"]
        ref = name in ("automation", "grind")
        limits = sum(n for t, n in r["terminations"].items() if t.startswith("resource_limit:"))
        lines.append(
            f"| {name} | {r['verified']}/{r['runs']} | {r['success_rate'] * 100:.2f} {interval(r['success_ci95'], 100)} | {f'{m["attempted_candidates"]["mean"]:.2f} external calls' if ref else f'{m["attempted_candidates"]["mean"]:.2f}'} | {'opaque' if ref else f'{m["expanded_states"]["mean"]:.2f}'} | {m['runner_wall_s']['mean']:.3f} | {m['lean_execution_s']['mean']:.3f} | {m['retrieval_s']['mean']:.3f} | {m['model_inference_s']['mean']:.3f} | {limits} | {r['statuses'].get('execution_error', 0)} |"
        )
    lines += [
        "",
        "Primary arms share 18 seconds, 600 attempts, eighty expansions, depth twelve, 24 candidates and two seconds per tactic/query. Smaller arms share 10 seconds, 240 attempts and forty expansions. Aesop/grind use one two-second external call; their work is not one elementary inference. Retrieval, Python inference and independent-audit wall count inside the shared outer budget. All-run effort mixes successes/failures and does not measure proof efficiency alone. Selected relevance is linear in both learned and fully linear controls; their controllers differ (boosted versus ridge). The applicability relevance ablation holds the selected controller fixed.",
        "",
        "## Paired comparisons",
        "",
        "| Left minus right | Success difference pp [theorem 95%] | Equal-family point pp [family interval] | Common-verified theorems | Common-success attempts difference [95%] |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, c in s["comparisons"].items():
        d = c["success"]
        f = d["family_sensitivity"]
        e = c["common_verified"]["attempted_candidates"]
        effort = (
            f"{e['mean_difference']:+.3f} {interval(e['ci95_theorem'])}"
            if e["mean_difference"] is not None
            else "unavailable"
        )
        lines.append(
            f"| {name} | {d['mean_difference'] * 100:+.3f} {interval(d['ci95_theorem'], 100)} | {f['mean_difference'] * 100:+.3f} {interval(f['ci95'], 100)} | {e['theorems']} | {effort} |"
        )
    lines += [
        "",
        "10,000 paired bootstrap draws, seed 2718, on theorem averages across repeats. The family sensitivity is a different equal-family estimand; it is not another interval around the theorem-weighted point. Common-success comparisons condition on a potentially different subset for each contrast. Repetitions are execution-variability checks, not independent new theorems. Secondary contrasts are descriptive.",
        "",
        "## Mathematical families",
        "",
        "| Family | Expanded P3 | Typed 5 | Learned 5 | Deterministic | Learned | Staged | Aesop | grind |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for family in s["results"]["phase4"]["families"]:
        values = [
            s["results"][a]["families"][family]
            for a in (
                "phase4",
                "typed5",
                "learned5",
                "deterministic",
                "learned",
                "staged",
                "automation",
                "grind",
            )
        ]
        lines.append(
            "| "
            + family
            + " | "
            + " | ".join(f"{r['verified']}/{r['runs']}" for r in values)
            + " |"
        )
    lines += [
        "",
        "## Applicability, selection and actual progress",
        "",
        "| Policy | Potential / selected occurrences | Entered / displaced | Compatible accepted / rejected | Symbolic / hybrid / typed decisions |",
        "|---|---:|---:|---:|---:|",
    ]
    for a, r in s["results"].items():
        c = r["observations"]
        lines.append(
            f"| {a} | {c.get('potential', 0)} / {c.get('selected', 0)} | {c.get('entered', 0)} / {c.get('displaced', 0)} | {c.get('compatible_accepted', 0) + c.get('compatible_solved', 0)} / {c.get('compatible_rejected', 0)} | {c.get('symbolic_decisions', 0)} / {c.get('hybrid_decisions', 0)} / {c.get('typed_decisions', 0)} |"
        )
    lines += [
        "",
        "Native resource rejections are retained separately as `tactic_resource_failures` and probe errors as `retrieval_probe_errors` in summary observations; an exhausted tactic is not evidence of mathematical incompatibility. Potential occurrences here count the scored candidate pool, not every declaration probe; complete returned native rows, including incompatible proposals, remain in each raw query. Symbolic decisions have no invented typed availability. Compatibility is a proposal annotation, actual acceptance is a native event, and useful availability is witnessed only by complete audited paths at identical prefixes. `summary.json/availability` links those partial recall witnesses. `run-diagnostics.json.gz` retains every observed goal reduction, new metavariable count, actual status and verified-path flag; valid unproductive steps remain unknown as mathematical conclusions.",
        "",
        "## Learning evidence",
        "",
        "The development and final-test boundaries are distinct. "
        + f"There are {training['development_tasks']} development tasks, {training['contributing_tasks']} contributing tasks, {training['source_states']} source states and {training['preferences']} pair preferences. Labels: `{training['labels']}`. Preference kinds: `{training['preference_kinds']}`.",
        "",
        f"Relevance validation winner: `{training['winner']}`. Selected selector: `{training['selector_selected']}` from {training['verified_selector_rows']} verified matched fixed-mode costs. Censored/unknown costs were excluded rather than labelled mathematically wrong. The selector has success-conditioned missingness and root/continuation-policy distribution limitations. The fully linear control uses the same linear relevance and a ridge controller. The applicability control changes relevance while holding the selected controller fixed.",
        "",
        "## Resource measurement scope",
        "",
        "The full-call wall column includes provider/model/index setup and engine metadata work; engine elapsed_s separately measures search, native initialization, retrieval, inference, verification and cleanup. Archive I/O/interpreter startup are outside the solver call. Fixed artifact setup precedes the engine deadline. All comparable arms use the same engine budget and execute every tactic/query/branch within it. Inference timing includes P2/P3/P4 comparison annotations and explanations as well as new controller/relevance work, so it is not isolated new-model overhead.",
        "",
        "Failed native queries are metered too. Missing interrupted native probe/heartbeat counts remain unknown; returned native counters are allocation observations, not primitive-inference totals. Session CPU/RSS exclude independent-audit process resources; total CPU is not claimed.",
        "",
        "## Per-theorem primary outcomes",
        "",
        "Each entry is verified repetitions / total. Exact attempts, expansions, wall, terminations, proofs and filenames are in `summary.json/per_theorem`; every single run is in `results.csv`.",
        "",
        "| Theorem | Expanded | Typed 5 | Learned 5 | Deterministic | Learned | Staged | Aesop | grind |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    indexed = {(r["task_id"], r["arm"]): r for r in s["per_theorem"]}
    for ident in sorted({r["task_id"] for r in s["per_theorem"]}):
        lines.append(
            "| "
            + ident
            + " | "
            + " | ".join(
                f"{indexed[(ident, a)]['verified']}/{indexed[(ident, a)]['repetitions']}"
                for a in (
                    "phase4",
                    "typed5",
                    "learned5",
                    "deterministic",
                    "learned",
                    "staged",
                    "automation",
                    "grind",
                )
            )
            + " |"
        )
    lines += [
        "",
        "## Resource and storage limitations",
        "",
        f"The lossless trace archive stores {storage['raw_bytes']:,} original JSON bytes in {storage['stored_bytes']:,} gzip bytes, with per-file raw/compressed SHA-256 hashes. Static replay reuses compressed archives; it does not commit another unpacked copy.",
        "",
        "Linux live-session CPU and sum of process high-water RSS bounds are practical partial measurements; they exclude independent-audit CPU/RSS and are not simultaneous physical-memory peaks. End-to-end wall includes audit. Planning/inference/native interaction are overlapping measured categories and must not be summed as disjoint wall components. Shared-host timings, finite budgets and timeout variation limit interpretation. No pretrained model, hosted inference, paid AI API or GPU is used. Previous frozen data and measurements remain unchanged.",
    ]
    (ROOT / "docs/phase-6-results.md").write_text("\n".join(lines) + "\n")
    print("Rendered actual Phase 6 quantitative results")


if __name__ == "__main__":
    main()
