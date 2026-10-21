"""Export complete genuine Phase 6 evidence; reuse each canonical gzip verbatim."""

from __future__ import annotations

import csv
import json
import shutil
import statistics

from export_phase4 import RESEARCH

from prooflab.lean import ROOT
from prooflab.phase6_data import DIRECTORY, read_tasks
from prooflab.phase6_evaluation import EXPERIMENT
from prooflab.research_io import read_json, trace_paths

LABELS = dict(
    phase4="Phase 4 expanded · strongest prior baseline",
    typed5="Phase 5 deterministic typed",
    learned5="Phase 5 learned retrieval",
    naive="Naive symbolic/typed union",
    deterministic="Deterministic context hybrid",
    learned="Learned adaptive hybrid",
    linear="Linear learned hybrid",
    staged="Adaptive staged hybrid",
    fixed="Fixed novelty quota",
    no_synthesis="Hybrid with Phase 5 synthesis",
    applicability="Applicability-only relevance control",
    phase4_canonical="Phase 4 with explicit canonical ties",
    automation="Native Aesop reference",
    grind="Native grind reference",
)


def main() -> None:
    if not (EXPERIMENT / "summary.json").exists():
        print("Phase 6 final evidence not yet available; no fabricated replay exported")
        return
    summary = read_json(EXPERIMENT / "summary.json")
    protocol = read_json(DIRECTORY / "protocol.json")
    destination = ROOT / "web/public/phase6"
    (destination / "data/traces").mkdir(parents=True, exist_ok=True)
    paths = trace_paths(EXPERIMENT / "traces")
    with (EXPERIMENT / "results.csv").open(newline="") as handle:
        recorded = {
            f"{r['task']}--{r['arm']}--r{r['repeat']}.json.gz": r for r in csv.DictReader(handle)
        }
    expected = sum(a["repetitions"] for a in protocol["arms"]) * len(read_tasks())
    if len(recorded) != expected or {p.name for p in paths} != set(recorded):
        raise ValueError("Incomplete matrix; do not publish partial results as final")
    arms = {a["id"]: a for a in protocol["arms"]}
    manifest = []
    for path in paths:
        row = recorded[path.name]
        shutil.copyfile(path, destination / "data/traces" / path.name)
        mode = arms[row["arm"]]["mode"]
        algorithm = mode if mode in ("automation", "grind") else "outcome"
        manifest.append(
            dict(
                task_id=row["task"],
                algorithm=algorithm,
                arm=row["arm"],
                repeat=int(row["repeat"]),
                url=f"phase6/data/traces/{path.name}",
                status=row["status"],
            )
        )
    examples = []
    indexed = {(r["task_id"], r["arm"]): r for r in summary["per_theorem"]}

    def example(ident: str, a: str, b: str, title: str) -> None:
        left, right = indexed[(ident, a)], indexed[(ident, b)]
        examples.append(
            dict(
                title=title,
                task_id=ident,
                left=a,
                right=b,
                left_verified=left["verified"],
                right_verified=right["verified"],
                repetitions=left["repetitions"],
                family=left["family"],
                left_attempt_mean=statistics.mean(left["attempts"]),
                right_attempt_mean=statistics.mean(right["attempts"]),
            )
        )

    for name in (
        "learned minus phase4",
        "deterministic minus phase4",
        "learned minus deterministic",
    ):
        c = summary["comparisons"][name]
        a, b = name.split(" minus ")
        for field, title in [
            ("gains", "Actual verified gain"),
            ("losses", "Actual verified regression"),
        ]:
            if c[field]:
                example(c[field][0], a, b, title + " · " + name)
        effort = c["common_verified"]["attempted_candidates"]["differences"]
        regressions = [(v, i) for i, v in effort.items() if v > 0]
        if regressions:
            example(max(regressions)[1], a, b, "More attempts on a common verified theorem")
    unsolved = [
        t.id
        for t in read_tasks()
        if not any(
            indexed[(t.id, a)]["verified"]
            for a in ("phase4", "deterministic", "learned", "automation", "grind")
        )
    ]
    if unsolved:
        example(unsolved[0], "phase4", "learned", "Unsolved across primary methods and references")
    families = read_json(DIRECTORY / "families.json")
    test_ids = {t.id for t in read_tasks()}
    payload = dict(
        tasks=[t.model_dump() for t in read_tasks()],
        families={i: f for i, f in families.items() if i in test_ids},
        manifest=manifest,
        policy_names={
            a["id"]: LABELS[a["mode"]] + (" · small budget" if a["budget_level"] == "small" else "")
            for a in protocol["arms"]
        },
        summary={k: summary[k] for k in ("results", "comparisons", "uncertainty", "runs")},
        examples=examples,
        protocol=protocol,
        declarations=read_json(ROOT / "benchmarks/phase5/declarations.json")["declarations"],
        model=read_json(ROOT / "models/phase6/learned.json"),
        native={},
        research=[
            dict(title=t, idea=i, url=u, relation=r)
            for t, i, u, r in RESEARCH
            if t in ("Aesop", "ReProver / LeanDojo", "TacticToe", "grind / Duper")
        ],
        limitations={
            t.id: (
                "Exact native states and observed outcomes only. Candidate protection is not "
                "a solved-theorem guarantee. Canonical ties separate selection from "
                "scheduling; conditional mode-cost predictions have missing-outcome "
                "selection bias. All strategies share the selected budget level."
            )
            for t in read_tasks()
        },
    )
    (destination / "explorer.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    (destination / "model.json").write_text(json.dumps(payload["model"], indent=2) + "\n")
    print("Exported", len(manifest), "genuine Phase 6 traces")


if __name__ == "__main__":
    main()
