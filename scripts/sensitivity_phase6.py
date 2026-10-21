"""Labelled post-hoc robustness checks; never rewrites preregistered results."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime

from prooflab.phase6_evaluation import EXPERIMENT, contrast
from prooflab.research_io import read_json


def main() -> None:
    summary = read_json(EXPERIMENT / "summary.json")
    with (EXPERIMENT / "results.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        groups[row["arm"]][row["task"]].append(
            dict(
                verified=row["status"] == "verified",
                family=row["family"],
                metrics={
                    m: float(row[m])
                    for m in ("attempted_candidates", "expanded_states", "runner_wall_s")
                },
            )
        )
    ids = sorted(groups["phase4"])
    families = {i: groups["phase4"][i][0]["family"] for i in ids}
    comparisons = {}
    for left, right in [
        ("learned", "phase4"),
        ("deterministic", "phase4"),
        ("learned", "deterministic"),
        ("staged", "phase4"),
    ]:
        difference = contrast(groups[left], groups[right], "success", ids)
        d = difference["differences"]
        common = [i for i in ids if all(r["verified"] for r in groups[left][i] + groups[right][i])]
        comparisons[f"{left} minus {right}"] = dict(
            success=difference,
            common_verified={
                m: contrast(groups[left], groups[right], m, common)
                for m in ("attempted_candidates", "expanded_states", "runner_wall_s")
            },
            gains=[i for i in ids if d[i] > 0],
            losses=[i for i in ids if d[i] < 0],
            leave_one_family_out={
                family: statistics.mean(v for i, v in d.items() if families[i] != family)
                for family in sorted(set(families.values()))
            },
        )
    provenance = read_json(EXPERIMENT / "provenance.json")
    finished = read_json(EXPERIMENT / "finished.json")
    roots = read_json(EXPERIMENT / "analysis.json")["root_decisions"]
    resources = {}
    for metric in ("coordinator_cpu_s", "session_cpu_s", "session_peak_rss_kib"):
        values = [float(r[metric]) for r in rows if r[metric]]
        resources[metric] = dict(
            observed=len(values),
            missing=len(rows) - len(values),
            mean=statistics.mean(values) if values else None,
            maximum=max(values) if values else None,
            sum=sum(values) if values else None,
        )
    output = dict(
        role=(
            "Post-hoc descriptive sensitivity, not additional preregistered primary "
            "evidence or model selection. Original summary.json is preserved."
        ),
        comparisons=comparisons,
        unsolved_all_registered_arms=[
            i for i in ids if not any(r["verified"] for g in groups.values() for r in g[i])
        ],
        root_modes={
            arm: dict(Counter(r["decision"] for r in roots if r["arm"] == arm))
            for arm in ("learned", "deterministic", "staged")
        },
        campaign_wall_s=(
            datetime.fromisoformat(finished["finished_at"])
            - datetime.fromisoformat(provenance["started_at"])
        ).total_seconds(),
        resources=resources,
        limits=(
            "CPU/RSS exclude independent-audit processes; RSS sums are not simultaneous "
            "physical peaks. Campaign wall includes canonical archive processing. "
            "Related hand-curated families, repeated statements and shared-host timings "
            "do not establish population-wide superiority."
        ),
        repeat_variation={a: r["repeat_variations"] for a, r in summary["results"].items()},
    )
    (EXPERIMENT / "sensitivity.json").write_text(json.dumps(output, indent=2) + "\n")
    print(
        "Post-hoc staged minus P4:",
        comparisons["staged minus phase4"]["success"],
        "\nUnsolved by all arms:",
        output["unsolved_all_registered_arms"],
    )


if __name__ == "__main__":
    main()
