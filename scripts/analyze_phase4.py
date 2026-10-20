"""Theorem/family clustered uncertainty and paired success-conditioned diagnostics."""

import json
import random
import statistics
from collections import defaultdict

from prooflab.lean import ROOT
from prooflab.models import Trace
from prooflab.phase4_data import DIRECTORY
from prooflab.research_io import read_json, trace_paths


def ci(values, groups, samples=10000):
    rng = random.Random(2718)
    labels = sorted(set(groups))
    members = {
        g: [v for v, group in zip(values, groups, strict=True) if group == g] for g in labels
    }
    means = []
    for _ in range(samples):
        selected = [v for _ in labels for v in members[rng.choice(labels)]]
        means.append(statistics.mean(selected))
    means.sort()
    return dict(
        estimate=statistics.mean(values),
        lower=means[int(0.025 * samples)],
        upper=means[int(0.975 * samples)],
        clusters=len(labels),
        theorems=len(values),
    )


def main():
    directory = ROOT / "experiments/phase4/evaluation-v1"
    traces = [Trace.model_validate(read_json(p)) for p in trace_paths(directory / "traces")]
    protocol = read_json(DIRECTORY / "protocol.json")
    families = read_json(DIRECTORY / "families.json")
    grouped = defaultdict(list)
    for t in traces:
        grouped[t.task.id, t.algorithm].append(t)
    ids = sorted(families)
    algorithms = protocol["algorithms"]
    fields = (
        "success",
        "attempted_candidates",
        "expanded_states",
        "elapsed_s",
        "lean_execution_s",
        "planning_s",
        "model_inference_s",
        "tree_size",
    )

    def mean(ident, a, m):
        return statistics.mean(
            float(t.status == "verified")
            if m == "success"
            else len(t.nodes)
            if m == "tree_size"
            else getattr(t.metrics, m)
            for t in grouped[ident, a]
        )

    comparisons = {}
    for base in algorithms:
        if base == "joint":
            continue
        common = [i for i in ids if mean(i, "joint", "success") == mean(i, base, "success") == 1]
        cohorts = {}
        for name, cohort in [("all_theorems", ids), ("common_verified", common)]:
            cohorts[name] = {}
            for m in fields:
                if base in ("automation", "grind") and m in (
                    "attempted_candidates",
                    "expanded_states",
                    "tree_size",
                ):
                    continue
                values = [mean(i, "joint", m) - mean(i, base, m) for i in cohort]
                cohorts[name][m] = (
                    dict(
                        theorem=ci(values, cohort), family=ci(values, [families[i] for i in cohort])
                    )
                    if values
                    else None
                )
        comparisons[base] = cohorts
    repeat_differences = []
    for (ident, a), runs in grouped.items():
        runs.sort(key=lambda t: int(t.metadata["repeat"]))
        if any(
            (
                t.status,
                t.termination,
                t.metrics.attempted_candidates,
                t.metrics.expanded_states,
                t.proof,
            )
            != (
                runs[0].status,
                runs[0].termination,
                runs[0].metrics.attempted_candidates,
                runs[0].metrics.expanded_states,
                runs[0].proof,
            )
            for t in runs[1:]
        ):
            repeat_differences.append(dict(task=ident, algorithm=a))
    changes = {}
    for base in ("best_first", "outcome", "frontier"):
        changes[base] = dict(
            gained=[i for i in ids if mean(i, "joint", "success") > mean(i, base, "success")],
            lost=[i for i in ids if mean(i, "joint", "success") < mean(i, base, "success")],
            common_verified_attempt_differences={
                i: mean(i, "joint", "attempted_candidates") - mean(i, base, "attempted_candidates")
                for i in ids
                if mean(i, "joint", "success") == mean(i, base, "success") == 1
            },
        )
    output = dict(
        comparisons=comparisons,
        repeat_structural_differences=repeat_differences,
        success_changes=changes,
        definitions=(
            "Repeat means paired by theorem; 10000 seeded bootstrap samples. "
            "Family bootstrap resamples entire families, retains theorem multiplicity. "
            "Common-verified comparisons are selected subsets, not all-task success evidence. "
            "External tactic internal work excluded."
        ),
    )
    (directory / "analysis.json").write_text(json.dumps(output, indent=2) + "\n")
    print("repeat structural differences", repeat_differences)
    print("joint-hand common", comparisons["best_first"]["common_verified"]["attempted_candidates"])


if __name__ == "__main__":
    main()
