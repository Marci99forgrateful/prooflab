"""Static replay from complete canonical Phase 5 experiments; no Lean execution."""

from __future__ import annotations

import csv
import gzip
import json
import shutil
import statistics

from export_phase4 import RESEARCH

from prooflab.lean import ROOT
from prooflab.research_io import read_json, trace_paths

GEN_NAMES = {
    "original": "Original",
    "phase4": "Phase 4 expanded",
    "typed": "Deterministic typed",
    "learned": "Learned retrieval",
    "broad": "Broad unfiltered",
    "type_filtered": "Type filter only",
    "no_witness": "Typed without witnesses",
    "no_normalize": "Typed without normalization",
}
ORDER_NAMES = {"best_first": "handcrafted", "outcome": "Phase 3 actions", "joint": "Phase 4 joint"}


def main():
    experiment = ROOT / "experiments/phase5/evaluation-v1"
    summary = read_json(experiment / "summary-canonical.json")
    protocol = read_json(ROOT / "benchmarks/phase5/protocol.json")
    destination = ROOT / "web/public/phase5"
    (destination / "data/traces").mkdir(parents=True, exist_ok=True)
    paths = trace_paths(experiment / "traces")
    if len(paths) != sum(a["repetitions"] for a in protocol["arms"]) * 40:
        raise ValueError("Incomplete real matrix; no partial results published as complete")
    # The real per-run CSV supplies replay metadata; copy archives without
    # reparsing 4.6 GB of duplicated whitespace just to build the manifest.
    with (experiment / "results.csv").open(newline="") as handle:
        recorded = {
            f"{r['task']}--{r['arm']}--r{r['repeat']}.json.gz": r for r in csv.DictReader(handle)
        }
    arms = {arm["id"]: arm for arm in protocol["arms"]}
    if len(recorded) != len(paths):
        raise ValueError("CSV/archive matrix mismatch")
    manifest = []
    for path in paths:
        filename = path.name if path.suffix == ".gz" else path.name + ".gz"
        data = recorded[filename]
        target = destination / "data/traces" / filename
        if path.suffix == ".gz":
            shutil.copyfile(path, target)
        else:
            target.write_bytes(gzip.compress(path.read_bytes(), compresslevel=6, mtime=0))
        manifest.append(
            dict(
                task_id=data["task"],
                algorithm=arms[data["arm"]]["algorithm"],
                arm=data["arm"],
                repeat=int(data["repeat"]),
                url=f"phase5/data/traces/{filename}",
                status=data["status"],
            )
        )
    analysis = read_json(experiment / "analysis.json")
    examples = []
    for comparison, field, title in [
        ("typed_p3 minus original_p3", "success_gains", "Typed generation enables a proof"),
        ("typed_p3 minus original_p3", "success_regressions", "Typed generator regression"),
        ("learned_p3 minus typed_p3", "success_gains", "Learned retrieval changes success"),
        ("learned_p3 minus typed_p3", "success_regressions", "Learned retrieval regression"),
        ("typed_joint minus typed_p3", "success_gains", "Frozen frontier changes success"),
        ("automation minus learned_p3", "success_gains", "Separate native Aesop success"),
    ]:
        cases = analysis["case_studies"].get(comparison, {}).get(field, [])
        if cases:
            row = cases[0]
            left, right = comparison.split(" minus ")
            examples.append(
                dict(
                    title=title,
                    task_id=row["task_id"],
                    left=left,
                    right=right,
                    left_verified=row["left"]["verified"],
                    right_verified=row["right"]["verified"],
                    repetitions=row["left"]["repetitions"],
                    family=row["family"],
                    left_attempt_mean=statistics.mean(row["left"]["attempts"]),
                    right_attempt_mean=statistics.mean(row["right"]["attempts"]),
                )
            )
    losses = [
        r
        for r in analysis["case_studies"]["learned_p3 minus typed_p3"]["common_verified_effort"]
        if r["attempt_difference"] > 0
    ]
    if losses:
        row = max(losses, key=lambda r: r["attempt_difference"])
        examples.append(
            dict(
                title="Learned retrieval costs more attempts",
                task_id=row["task_id"],
                left="learned_p3",
                right="typed_p3",
                left_verified=row["left"]["verified"],
                right_verified=row["right"]["verified"],
                repetitions=row["left"]["repetitions"],
                family=row["family"],
                left_attempt_mean=statistics.mean(row["left"]["attempts"]),
                right_attempt_mean=statistics.mean(row["right"]["attempts"]),
            )
        )
    labels = {
        a["id"]: (
            "Native Aesop reference"
            if a["algorithm"] == "automation"
            else "Native grind reference"
            if a["algorithm"] == "grind"
            else GEN_NAMES[a["generator"]] + " × " + ORDER_NAMES[a["algorithm"]]
        )
        for a in protocol["arms"]
    }
    payload = dict(
        examples=examples,
        manifest=manifest,
        tasks=json.loads((ROOT / "benchmarks/phase5/evaluation.json").read_text()),
        policy_names=labels,
        summary={k: summary[k] for k in ("results", "comparisons", "uncertainty")},
        research=[
            dict(title=t, idea=i, url=u, relation=r)
            for t, i, u, r in RESEARCH
            if t
            in (
                "Aesop",
                "ReProver / LeanDojo",
                "Sledgehammer / LeanHammer",
                "grind / Duper",
                "TacticToe",
            )
        ],
        declarations=read_json(ROOT / "benchmarks/phase5/declarations.json")["declarations"],
        model=read_json(ROOT / "models/phase5/retrieval.json"),
        protocol=protocol,
        coverage=read_json(ROOT / "experiments/phase5/coverage-v1/summary.json"),
        native={},
        limitations={
            t: (
                "Every queried state records capped selection, native "
                "compatibility, entered/displaced actions and actual outcomes. "
                "Recall is partial: observed verified next actions at identical "
                "tactic prefixes, not all mathematically useful actions."
            )
            for t in json.loads((ROOT / "benchmarks/phase5/families.json").read_text())
        },
    )
    (destination / "explorer.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    (destination / "model.json").write_text(json.dumps(payload["model"], indent=2) + "\n")
    print("Exported", len(manifest), "genuine Phase 5 traces; canonical declaration index reused")


if __name__ == "__main__":
    main()
