"""Render the measured research report directly from the selected raw run."""

import argparse
import json
from pathlib import Path

from prooflab.models import Trace

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"bfs": "Breadth-first", "best_first": "Heuristic best-first", "automation": "Native Aesop"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    report = json.loads((args.experiment / "summary.json").read_text())
    p = report["provenance"]
    results = report["results"]
    traces = [
        Trace.model_validate_json(path.read_text())
        for path in (args.experiment / "traces").glob("*.json")
    ]
    lookup = {(t.task.id, t.algorithm): t for t in traces}
    pairs = [
        (t, lookup[t.task.id, "best_first"])
        for t in traces
        if t.algorithm == "bfs"
        and t.status == "verified"
        and lookup[t.task.id, "best_first"].status == "verified"
    ]
    bfs_states = sum(a.metrics.expanded_states for a, b in pairs)
    best_states = sum(b.metrics.expanded_states for a, b in pairs)
    lines = [
        "# Experimental results — Phase 1",
        "",
        "These numbers are generated from actual completed runs. No unexecuted result is included.",
        "",
        "## Frozen final experiment",
        "",
        f"- Code commit: `{p['code_commit']}`.",
        f"- Lean: `{p['lean_version']}`; Mathlib: `{p['mathlib_revision']}`.",
        f"- Dataset SHA-256: `{p['dataset_sha256']}`.",
        f"- Started: `{p['started_at']}` (UTC).",
        f"- Host: `{p['platform']}`, `{p['machine']}`, {p['cpu_count']} visible CPUs; "
        "peak memory not measured; Lean allocation limit 2048 MB.",
        f"- Python: `{p['python']}`; seed: `{p['seed']}`; workers: {p['workers']}.",
        f"- Budget: `{json.dumps(p['budget'], sort_keys=True)}`.",
        "- 64 tasks: 48 development and 16 reserved held-out; four mathematical subjects.",
        "",
        "## Overall results",
        "",
        "| Strategy | Verified | Success | Mean wall s | Median wall s | Mean expansions | "
        "Mean candidates | Resource limits | Execution errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a, r in results.items():
        lines.append(
            f"| {NAMES[a]} | {r['verified']}/{r['attempted']} | "
            f"{r['success_rate']:.2%} | {r['mean_wall_s']:.3f} | "
            f"{r['median_wall_s']:.3f} | {r['mean_expansions']:.2f} | "
            f"{r['mean_candidates']:.2f} | {r['resource_limits']} | "
            f"{r['execution_errors']} |"
        )
    lines += [
        "",
        "Aesop is one separately identified native automation attempt, not a ProofLab "
        "algorithm. All strategies share the overall and per-call caps; Aesop uses one call.",
        "",
        "## By mathematical subject",
        "",
        "| Subject | BFS | Best-first | Native Aesop |",
        "|---|---:|---:|---:|",
    ]
    for d in ("logic", "order", "algebra", "sets"):
        cells = [f"{results[a]['domains'][d]['verified']}/16" for a in NAMES]
        lines.append(f"| {d.title()} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Reserved held-out split",
        "",
        "| Strategy | Development | Held-out |",
        "|---|---:|---:|",
    ]
    for a, r in results.items():
        lines.append(
            f"| {NAMES[a]} | {r['splits']['development']['verified']}/48 | "
            f"{r['splits']['held_out']['verified']}/16 |"
        )
    lines += [
        "",
        "The reserved split is not a blinded evaluation. Statements were visible during "
        "engineering, including pilot failure analysis. No model was trained. These numbers "
        "do not establish strong out-of-distribution generalization.",
        "",
        "## Where the successful proofs came from",
        "",
        "| Strategy | Constructed derivation | One-step lemma | Specialized tactic | "
        "Native automation |",
        "|---|---:|---:|---:|---:|",
    ]
    for a, r in results.items():
        o = r["proof_origins"]
        lines.append(
            f"| {NAMES[a]} | {o['constructed_derivation']} | {o['retrieved_lemma']} | "
            f"{o['specialized_tactic']} | {o['native_automation']} |"
        )
    lines += [
        "",
        "A multi-step proof can still include a specialized tactic; the exact script "
        "and per-attempt category are retained. This table does not claim new mathematics.",
        "",
        "## Paired effort and interpretation",
        "",
        f"On the **{len(pairs)} tasks verified by both original strategies**, BFS expanded "
        f"{bfs_states} states in total and best-first expanded {best_states}. "
        "This is a descriptive search-effort comparison, not a statistically established "
        "wall-clock speedup.",
        "",
        "Best-first solves some tasks that BFS misses, and misses some that BFS solves. "
        "In particular, inspect `set_inter_monotone`, `set_union_elim`, `eq_pair` and "
        "`symmetric_chain`. A smaller heuristic score is not proof evidence or a guarantee "
        "of better scheduling.",
        "",
        "Lean startup and independent rechecking dominate short runs. Wall times include "
        "failures; fast failed searches must not be interpreted as better proof discovery. "
        "Concurrent workloads share the host. No confidence intervals or novelty claims "
        "are made from one run.",
        "",
        "## Preserved original-search failures",
        "",
        "| Task | Strategy | Actual termination |",
        "|---|---|---|",
    ]
    for t in sorted(traces, key=lambda t: (t.task.id, t.algorithm)):
        if t.algorithm != "automation" and t.status != "verified":
            lines.append(f"| `{t.task.id}` | {NAMES[t.algorithm]} | `{t.termination}` |")
    lines += [
        "",
        "These are incomplete bounded searches, never mathematical counterexamples. "
        "All native automation failures are also retained in the raw results.",
        "",
        "## Preserved pilot history",
        "",
        "| Run | Code commit | BFS | Best-first | Native Aesop |",
        "|---|---|---:|---:|---:|",
    ]
    for name in ("phase1-v1", "phase1-v2", "phase1-v3"):
        q = ROOT / "experiments" / name / "summary.json"
        if q.exists():
            run = json.loads(q.read_text())
            counts = [str(run["results"][a]["verified"]) + "/64" for a in NAMES]
            lines.append(
                f"| {name} | `{run['provenance']['code_commit'][:12]}` | "
                + " | ".join(counts)
                + " |"
            )
    lines += [
        "",
        "The first pilot exposed `ℕ`/`Nat` detection; the second exposed a general "
        "conclusion/context feature mismatch for antisymmetry retrieval. Both received "
        "generic fixes and regressions. Dataset and limits stayed fixed. No failed task "
        "was removed, no complete answer was inserted into candidate generation, and "
        "the prior raw evidence remains available.",
        "",
        "## Reproduce and inspect",
        "",
        f"Raw run: [`{args.experiment}`](../{args.experiment}). "
        "See [methodology](benchmark-methodology.md) for the command and scope.",
        "",
        "![Actual measured results](assets/benchmark-results.svg)",
        "",
        "Exportable figures: [SVG](assets/benchmark-results.svg), "
        "[PNG](assets/benchmark-results.png), [PDF](assets/benchmark-results.pdf).",
        "",
    ]
    (ROOT / "docs/experimental-results.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
