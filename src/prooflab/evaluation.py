"""Frozen Phase 2 experiment; raw executions and theorem-cluster uncertainty."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from prooflab.benchmark import summary
from prooflab.dataset import load_phase2_tasks
from prooflab.lean import ROOT
from prooflab.learning import DEFAULT_MODEL, LearnedRanking
from prooflab.models import Budget, SearchAlgorithm, Trace
from prooflab.search import metadata, search
from prooflab.splits import PHASE2, check_freeze

METRICS = (
    "elapsed_s",
    "lean_execution_s",
    "initialization_s",
    "verification_s",
    "planning_s",
    "model_inference_s",
    "expanded_states",
    "attempted_candidates",
    "proof_length",
)


def interval(values: list[float], samples: list[list[int]]) -> dict[str, float]:
    """Percentile bootstrap over precomputed theorem clusters (repeats stay together)."""
    n = len(values)
    means = sorted(sum(values[i] for i in sample) / n for sample in samples)
    return {
        "estimate": statistics.mean(values),
        "lower": means[int(0.025 * len(means))],
        "upper": means[min(len(means) - 1, int(0.975 * len(means)))],
    }


def summarize(traces: list[Trace], protocol: dict[str, Any]) -> dict[str, Any]:
    target = protocol.get("target_algorithm", "learned")
    tasks = sorted({t.task.id for t in traces})
    algorithms = protocol["algorithms"]
    rng = random.Random(protocol["uncertainty"]["seed"])
    samples = [
        [rng.randrange(len(tasks)) for _ in tasks]
        for _ in range(protocol["uncertainty"]["bootstrap_samples"])
    ]
    by_task = {
        task: {a: [t for t in traces if t.task.id == task and t.algorithm == a] for a in algorithms}
        for task in tasks
    }
    per_task = {
        task: {
            "family": protocol["evaluation_families"][task],
            "algorithms": {
                a: {
                    "runs": len(runs),
                    "verified": sum(t.status == "verified" for t in runs),
                    "terminations": [t.termination for t in runs],
                    **{m: statistics.mean(getattr(t.metrics, m) for t in runs) for m in METRICS},
                }
                for a, runs in by_task[task].items()
            },
        }
        for task in tasks
    }
    groups = summary(traces)
    for algorithm in algorithms:
        subset = [t for t in traces if t.algorithm == algorithm]
        groups[algorithm]["metrics"] = {
            m: {
                "mean": statistics.mean(getattr(t.metrics, m) for t in subset),
                "median": statistics.median(getattr(t.metrics, m) for t in subset),
                "min": min(getattr(t.metrics, m) for t in subset),
                "max": max(getattr(t.metrics, m) for t in subset),
            }
            for m in METRICS
        }
        groups[algorithm]["success_interval"] = interval(
            [
                per_task[task]["algorithms"][algorithm]["verified"]
                / per_task[task]["algorithms"][algorithm]["runs"]
                for task in tasks
            ],
            samples,
        )
        groups[algorithm]["termination_counts"] = {
            reason: sum(t.termination == reason for t in subset)
            for reason in sorted({t.termination for t in subset})
        }
        groups[algorithm]["families"] = {
            family: {
                "runs": sum(protocol["evaluation_families"][t.task.id] == family for t in subset),
                "verified": sum(
                    t.status == "verified" and protocol["evaluation_families"][t.task.id] == family
                    for t in subset
                ),
            }
            for family in sorted(set(protocol["evaluation_families"].values()))
        }
    differences: dict[str, Any] = {}
    for baseline in protocol.get("comparison_baselines", ("bfs", "best_first", "automation")):
        differences[baseline] = {
            "interpretation": (
                "learned minus baseline; lower effort is better; all tasks include failures"
            ),
            "success_rate": interval(
                [
                    per_task[t]["algorithms"][target]["verified"]
                    / per_task[t]["algorithms"][target]["runs"]
                    - per_task[t]["algorithms"][baseline]["verified"]
                    / per_task[t]["algorithms"][baseline]["runs"]
                    for t in tasks
                ],
                samples,
            ),
            **{
                metric: interval(
                    [
                        per_task[t]["algorithms"][target][metric]
                        - per_task[t]["algorithms"][baseline][metric]
                        for t in tasks
                    ],
                    samples,
                )
                for metric in (
                    "expanded_states",
                    "attempted_candidates",
                    "elapsed_s",
                    "lean_execution_s",
                )
            },
        }
        common = [
            t
            for t in tasks
            if all(
                per_task[t]["algorithms"][a]["verified"] == per_task[t]["algorithms"][a]["runs"]
                for a in (target, baseline)
            )
        ]
        differences[baseline]["common_verified_tasks"] = common
        differences[baseline]["common_verified_mean_differences"] = (
            {
                m: statistics.mean(
                    per_task[t]["algorithms"][target][m] - per_task[t]["algorithms"][baseline][m]
                    for t in common
                )
                for m in (
                    "expanded_states",
                    "attempted_candidates",
                    "elapsed_s",
                    "lean_execution_s",
                )
            }
            if common
            else {}
        )
    return {"results": groups, "paired_differences": differences, "per_theorem": per_task}


def run_evaluation(destination: Path, model_path: Path = DEFAULT_MODEL) -> dict[str, Any]:
    frozen = check_freeze()
    protocol = json.loads((PHASE2 / "protocol.json").read_text())
    ranker = LearnedRanking(model_path)
    provenance = ranker.model.provenance
    if not set(provenance["training_task_ids"]).issubset(frozen["permitted_development_ids"]):
        raise ValueError("Model used non-development data")
    if (
        provenance["evaluation_sha256"] != frozen["evaluation_sha256"]
        or provenance["evaluation_accessed_during_selection"]
    ):
        raise ValueError("Model selection does not match frozen protocol")
    budget = Budget.model_validate(protocol["budget"])
    tasks = load_phase2_tasks()
    algorithms = cast(list[SearchAlgorithm], protocol["algorithms"])
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = {
        **metadata(),
        "started_at": datetime.now(UTC).isoformat(),
        "model_sha256": ranker.model_hash,
        "evaluation_sha256": frozen["evaluation_sha256"],
        "protocol_sha256": frozen["protocol_sha256"],
        "frozen_sha256": hashlib.sha256((PHASE2 / "frozen.json").read_bytes()).hexdigest(),
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src/prooflab").glob("*.py"))
        },
        "budget": budget.model_dump(),
        "workers": protocol["workers"],
        "repetitions": protocol["repetitions"],
        "algorithms": algorithms,
        "cpu_count": os.cpu_count(),
        "affinity_cpu_count": len(os.sched_getaffinity(0)),
        "timing_note": (
            "Two workers share host; wall time includes startup and fresh proof audit. "
            "All three ProofLab policies record both score explanations. Native Aesop "
            "is a separate reference with its own internal tactics, not candidate-matched."
        ),
        "ordering": "rotate policy order by theorem and repeat; collect repeats sequentially",
        "uncertainty": protocol["uncertainty"],
    }
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    traces = []
    for repeat in range(protocol["repetitions"]):
        with ThreadPoolExecutor(max_workers=protocol["workers"]) as pool:
            futures = []
            for index, task in enumerate(tasks):
                offset = (repeat + index) % len(algorithms)
                for algorithm in algorithms[offset:] + algorithms[:offset]:
                    futures.append(
                        pool.submit(search, task, algorithm, budget, comparison_ranker=ranker)
                    )
            for future in as_completed(futures):
                trace = future.result()
                trace.metadata["repeat"] = str(repeat)
                trace.metadata["family"] = protocol["evaluation_families"][trace.task.id]
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
    report = {"provenance": provenance, **summarize(traces, protocol)}
    (destination / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    with (destination / "results.csv").open("w", newline="") as output:
        fields = ["task", "family", "algorithm", "repeat", "status", "termination", *METRICS]
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for trace in traces:
            writer.writerow(
                {
                    "task": trace.task.id,
                    "family": trace.metadata["family"],
                    "algorithm": trace.algorithm,
                    "repeat": trace.metadata["repeat"],
                    "status": trace.status,
                    "termination": trace.termination,
                    **{m: getattr(trace.metrics, m) for m in METRICS},
                }
            )
    return report
