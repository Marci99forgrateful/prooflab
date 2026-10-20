"""Reproducible experiments with per-task raw traces, failures and provenance."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from prooflab.dataset import load_tasks
from prooflab.lean import ROOT
from prooflab.models import Budget, Trace
from prooflab.search import metadata, search

Algorithm = Literal["bfs", "best_first", "automation"]


def trajectory(trace: Trace) -> list[dict[str, Any]]:
    records = []
    for node in trace.nodes[1:]:
        assert node.parent is not None
        records.append(
            {
                "schema_version": 1,
                "task_id": trace.task.id,
                "split": trace.task.split,
                "algorithm": trace.algorithm,
                "goal_state": trace.nodes[node.parent].state,
                "candidate_tactic": node.tactic,
                "category": node.category,
                "lemma": node.lemma,
                "provenance": node.provenance,
                "valid": node.status in ("accepted", "solved"),
                "successor": node.state,
                "depth": node.depth,
                "on_verified_path": node.on_proof_path,
                "label_policy": (
                    "off-path is unexplored or unsuccessful, NOT mathematically useless"
                ),
                "elapsed_ms": node.elapsed_ms,
            }
        )
    return records


def summary(traces: list[Trace]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for algorithm in ("bfs", "best_first", "automation"):
        subset = [t for t in traces if t.algorithm == algorithm]
        if not subset:
            continue
        solved = [t for t in subset if t.status == "verified"]
        groups[algorithm] = {
            "attempted": len(subset),
            "verified": len(solved),
            "success_rate": len(solved) / len(subset),
            "mean_wall_s": statistics.mean(t.metrics.elapsed_s for t in subset),
            "median_wall_s": statistics.median(t.metrics.elapsed_s for t in subset),
            "resource_limits": sum(t.termination.startswith("resource_limit") for t in subset),
            "execution_errors": sum(t.status == "execution_error" for t in subset),
            "mean_expansions": statistics.mean(t.metrics.expanded_states for t in subset),
            "mean_candidates": statistics.mean(t.metrics.attempted_candidates for t in subset),
            "mean_lean_execution_s": statistics.mean(t.metrics.lean_execution_s for t in subset),
            "proof_origins": {
                origin: sum(t.proof_origin == origin for t in solved)
                for origin in (
                    "native_automation",
                    "retrieved_lemma",
                    "specialized_tactic",
                    "constructed_derivation",
                )
            },
            "domains": {
                d: {
                    "attempted": sum(t.task.domain == d for t in subset),
                    "verified": sum(t.task.domain == d for t in solved),
                }
                for d in ("logic", "order", "algebra", "sets")
            },
            "splits": {
                s: {
                    "attempted": sum(t.task.split == s for t in subset),
                    "verified": sum(t.task.split == s for t in solved),
                }
                for s in ("development", "held_out")
            },
            "difficulties": {
                s: {
                    "attempted": sum(t.task.difficulty == s for t in subset),
                    "verified": sum(t.task.difficulty == s for t in solved),
                }
                for s in ("easy", "moderate", "challenge")
            },
        }
    return groups


def run_benchmark(
    destination: Path,
    budget: Budget,
    split: str = "all",
    workers: int = 2,
    algorithms: tuple[Algorithm, ...] = ("bfs", "best_first", "automation"),
) -> dict[str, Any]:
    tasks = [t for t in load_tasks() if split == "all" or t.split == split]
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = {
        **metadata(),
        "started_at": datetime.now(UTC).isoformat(),
        "dataset_sha256": hashlib.sha256((ROOT / "benchmarks/tasks.json").read_bytes()).hexdigest(),
        "budget": budget.model_dump(),
        "split": split,
        "workers": workers,
        "cpu_count": os.cpu_count(),
        "memory": "not measured",
        "algorithms": algorithms,
        "timing_note": (
            "Concurrent tasks share the host. Wall times include startup and final audit."
        ),
    }
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    traces = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(search, task, algorithm, budget): (task.id, algorithm)
            for task in tasks
            for algorithm in algorithms
        }
        for future in as_completed(futures):
            trace = future.result()
            traces.append(trace)
            name = f"{trace.task.id}--{trace.algorithm}"
            (destination / "traces" / f"{name}.json").write_text(trace.model_dump_json(indent=2))
            print(f"{name}: {trace.status} ({trace.metrics.elapsed_s:.2f}s)", flush=True)
    traces.sort(key=lambda t: (t.task.id, t.algorithm))
    report = {"provenance": provenance, "results": summary(traces)}
    (destination / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    with (destination / "results.csv").open("w", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "task",
                "domain",
                "difficulty",
                "split",
                "algorithm",
                "status",
                "termination",
                "elapsed_s",
                "lean_execution_s",
                "initialization_s",
                "verification_s",
                "expanded_states",
                "attempted_candidates",
                "proof_length",
                "max_depth",
            ],
        )
        writer.writeheader()
        for trace in traces:
            row = {key: getattr(trace.metrics, key) for key in list(writer.fieldnames or [])[7:]}
            writer.writerow(
                {
                    "task": trace.task.id,
                    "domain": trace.task.domain,
                    "difficulty": trace.task.difficulty,
                    "split": trace.task.split,
                    "algorithm": trace.algorithm,
                    "status": trace.status,
                    "termination": trace.termination,
                    **row,
                }
            )
    with (destination / "trajectories.jsonl").open("w") as output:
        for trace in traces:
            for record in trajectory(trace):
                output.write(json.dumps(record, default=lambda x: x.model_dump()) + "\n")
    return report
