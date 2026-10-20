"""Deterministic family-bootstrap order; preserve the frozen runner's raw report.

The frozen runner iterates an intermediate family set. Its finite seeded bootstrap
therefore depends on Python hash order. Sorting fixes reporting reproducibility,
without changing traces, search, model selection, estimand or bootstrap budget.
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.phase5_evaluation import EXPERIMENT, ci
from prooflab.research_io import read_json


def canonical(
    raw: dict[str, Any], families: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    result = copy.deepcopy(raw)
    for comparison in result["comparisons"].values():
        estimates = [
            comparison["success"],
            *comparison["all_runs"].values(),
            *comparison["common_verified"].values(),
        ]
        for estimate in estimates:
            by_family: dict[str, list[float]] = defaultdict(list)
            for task in sorted(estimate["differences"]):
                by_family[families[task]].append(estimate["differences"][task])
            values = [statistics.mean(by_family[f]) for f in sorted(by_family)]
            estimate["ci95_family"] = ci(
                values, seed=config["bootstrap_seed"], samples=config["bootstrap_samples"]
            )
            estimate["family_balanced_mean"] = statistics.mean(values) if values else None
    result["statistics_method"] = dict(
        version="sorted-family-bootstrap-v1",
        family_order="lexicographic family IDs; theorem IDs sorted within family",
        bootstrap_seed=config["bootstrap_seed"],
        bootstrap_samples=config["bootstrap_samples"],
        note=(
            "Raw summary retained separately. Search outcomes, metrics, model and theorem "
            "bootstrap unchanged. Family-balanced common-success sensitivity has its own "
            "point estimand."
        ),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--experiment", type=Path, default=EXPERIMENT)
    args = parser.parse_args()
    experiment = args.experiment
    raw = read_json(experiment / "summary.json")
    result = canonical(
        raw,
        read_json(ROOT / "benchmarks/phase5/families.json"),
        read_json(ROOT / "benchmarks/phase5/protocol.json"),
    )
    content = json.dumps(result, indent=2) + "\n"
    path = experiment / "summary-canonical.json"
    if args.verify:
        if path.read_text() != content:
            raise ValueError("Canonical statistics differ")
        print("Canonical statistics byte-identical on fixed recorded evidence")
        return
    path.write_text(content)
    (experiment / "statistics-correction.json").write_text(
        json.dumps(
            dict(
                raw_summary_sha256=digest(experiment / "summary.json"),
                canonical_summary_sha256=digest(path),
                reason=(
                    "Frozen runner intermediate family set makes finite bootstrap order "
                    "hash-dependent; sorted family names fix derived reporting only."
                ),
                changed=(
                    "Family bootstrap Monte Carlo ordering plus explicit family-balanced point; "
                    "no raw trace, outcome, model, budget or theorem-bootstrap change."
                ),
                method=result["statistics_method"],
            ),
            indent=2,
        )
        + "\n"
    )
    print("Wrote canonical family statistics; raw frozen report preserved")


if __name__ == "__main__":
    main()
