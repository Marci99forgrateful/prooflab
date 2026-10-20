"""Frozen Phase 3 experiment with immutable models and real ablations."""

from __future__ import annotations

import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from prooflab.evaluation import METRICS, summarize
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, SearchAlgorithm
from prooflab.outcome import MODELS, OutcomeRanking
from prooflab.phase3_data import DIRECTORY, check_freeze, digest, read_tasks
from prooflab.search import metadata, search


def report_protocol() -> dict[str, Any]:
    protocol: dict[str, Any] = json.loads((DIRECTORY / "protocol.json").read_text())
    return {
        **protocol,
        "algorithms": protocol["algorithms"] + protocol["ablation_algorithms"],
        "target_algorithm": "outcome",
        "comparison_baselines": [
            "bfs",
            "best_first",
            "learned",
            "automation",
            "applicability_only",
            "old_features_outcome",
        ],
    }


def run(destination: Path) -> dict[str, Any]:
    frozen = check_freeze()
    protocol = report_protocol()
    model_freeze = json.loads((MODELS / "frozen.json").read_text())
    phase2 = LearnedRanking()
    models = {v: OutcomeRanking(MODELS / f"{v}.json") for v in model_freeze["models"]}
    for variant, sha in model_freeze["models"].items():
        if models[variant].model_hash != sha:
            raise ValueError("Frozen outcome model changed")
        p = models[variant].model.provenance
        if p["evaluation_accessed"] or not set(p["training_ids"]) <= set(
            frozen["permitted_development_ids"]
        ):
            raise ValueError("Forbidden model training or test tuning")
    if model_freeze["protocol_sha256"] != digest(DIRECTORY / "protocol.json"):
        raise ValueError("Model selection used different protocol")
    tasks = read_tasks()
    budget = Budget.model_validate(protocol["budget"])
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = {
        **metadata(),
        "started_at": datetime.now(UTC).isoformat(),
        "dataset_sha256": digest(DIRECTORY / "evaluation.json"),
        "protocol_sha256": digest(DIRECTORY / "protocol.json"),
        "freeze_sha256": digest(DIRECTORY / "frozen.json"),
        "model_freeze_sha256": digest(MODELS / "frozen.json"),
        "phase2_model_sha256": phase2.model_hash,
        "models": model_freeze["models"],
        "source_sha256": {
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted((ROOT / "src/prooflab").glob("*.py"))
        },
        "workers": protocol["workers"],
        "affinity_cpus": len(os.sched_getaffinity(0)),
        "budget": budget.model_dump(),
        "repetitions": protocol["repetitions"],
        "ablation_repetitions": protocol["ablation_repetitions"],
        "algorithms": protocol["algorithms"],
        "timing_note": (
            "Two workers share host. All ProofLab policies record both model explanations; "
            "their cost is counted. No hidden Lean lookahead. Aesop internal work is separate."
        ),
        "search_time_definition": (
            "elapsed minus initialization minus fresh verification; includes cleanup overhead"
        ),
        "uncertainty": protocol["uncertainty"],
        "ordering": (
            "Repeat 0 interleaves all policies/ablations, repeat 1 primary policies; "
            "rotate by theorem and repeat"
        ),
    }
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    traces = []
    for repeat in range(protocol["repetitions"]):
        algorithms = cast(
            list[SearchAlgorithm],
            [
                a
                for a in protocol["algorithms"]
                if repeat
                < (
                    protocol["ablation_repetitions"]
                    if a in protocol["ablation_algorithms"]
                    else protocol["repetitions"]
                )
            ],
        )
        with ThreadPoolExecutor(max_workers=protocol["workers"]) as pool:
            futures = []
            for index, task in enumerate(tasks):
                offset = (index + repeat) % len(algorithms)
                for algorithm in algorithms[offset:] + algorithms[:offset]:
                    policy = phase2 if algorithm == "learned" else models.get(algorithm)
                    futures.append(
                        pool.submit(
                            search,
                            task,
                            algorithm,
                            budget,
                            ranking=policy,
                            comparison_ranker=phase2,
                            comparison_outcome=models["outcome"],
                        )
                    )
            for future in as_completed(futures):
                trace = future.result()
                trace.metadata["repeat"] = str(repeat)
                families = json.loads((DIRECTORY / "families.json").read_text())
                trace.metadata["family"] = families[trace.task.id]
                traces.append(trace)
                name = f"{trace.task.id}--{trace.algorithm}--r{repeat}"
                (destination / "traces" / f"{name}.json").write_text(
                    trace.model_dump_json(indent=2) + "\n"
                )
                print(
                    f"{name}: {trace.status}, {trace.termination}, "
                    f"{trace.metrics.attempted_candidates} attempts "
                    f"({trace.metrics.elapsed_s:.2f}s)",
                    flush=True,
                )
    traces.sort(key=lambda t: (t.task.id, t.algorithm, t.metadata["repeat"]))
    summary_protocol = {
        **protocol,
        "evaluation_families": json.loads((DIRECTORY / "families.json").read_text()),
    }
    report = {"provenance": provenance, **summarize(traces, summary_protocol)}
    report["training"] = json.loads((MODELS / "training-report.json").read_text())
    (destination / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    with (destination / "results.csv").open("w", newline="") as out:
        columns = [
            "task",
            "family",
            "algorithm",
            "repeat",
            "status",
            "termination",
            *METRICS,
            "search_s",
        ]
        writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for t in traces:
            writer.writerow(
                {
                    "task": t.task.id,
                    "family": t.metadata["family"],
                    "algorithm": t.algorithm,
                    "repeat": t.metadata["repeat"],
                    "status": t.status,
                    "termination": t.termination,
                    **{m: getattr(t.metrics, m) for m in METRICS},
                    "search_s": max(
                        0,
                        t.metrics.elapsed_s - t.metrics.initialization_s - t.metrics.verification_s,
                    ),
                }
            )
    return report
