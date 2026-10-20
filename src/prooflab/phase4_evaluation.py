"""Controlled Phase 4 factorial search experiment. No held-out tuning."""

from __future__ import annotations

import csv
import json
import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from prooflab.evaluation import METRICS, summarize
from prooflab.frontier import MODELS, FrontierModel
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, SearchAlgorithm, Trace
from prooflab.outcome import OutcomeRanking
from prooflab.phase3_data import digest
from prooflab.phase4_data import DIRECTORY, check_freeze, read_tasks
from prooflab.research_io import compact
from prooflab.search import metadata, search


def description_key(trace: Trace, ident: int) -> str:
    """Diagnostic display grouping, explicitly not safe semantic identity."""
    state = trace.nodes[ident].state
    assert state is not None
    return json.dumps(
        [
            dict(
                target=g.target.model_dump(),
                hypotheses=[
                    dict(name=h.name, type=h.type.model_dump(), is_proof=h.is_proof)
                    for h in g.hypotheses
                ],
            )
            for g in state.goals
        ],
        sort_keys=True,
    )


def extra_metrics(t: Trace) -> dict[str, float]:
    states = [n for n in t.nodes if n.state is not None and n.state.goals]
    distinct = len({description_key(t, n.id) for n in states})
    return dict(
        search_tree_size=len(t.nodes),
        described_states=len(states),
        distinct_native_handles=len({n.state.state_id for n in states if n.state is not None}),
        distinct_descriptions=distinct,
        repeated_descriptions=len(states) - distinct,
        beam_evictions=len(t.beam_evictions),
        search_s=max(
            0, t.metrics.elapsed_s - t.metrics.initialization_s - t.metrics.verification_s
        ),
    )


def report(traces: list[Trace], protocol: dict[str, Any]) -> dict[str, Any]:
    compatible = {
        **protocol,
        "uncertainty": {
            "seed": protocol["bootstrap_seed"],
            "bootstrap_samples": protocol["bootstrap_samples"],
        },
    }
    result = summarize(traces, compatible)
    for reference in ("automation", "grind"):
        comparison = result["paired_differences"].get(reference, {})
        for metric in ("attempted_candidates", "expanded_states"):
            comparison.pop(metric, None)
            comparison.get("common_verified_mean_differences", {}).pop(metric, None)
        comparison["internal_work_note"] = "External tactic work units differ; counts not compared"
    for algorithm, group in result["results"].items():
        subset = [t for t in traces if t.algorithm == algorithm]
        for name in extra_metrics(subset[0]):
            values = [extra_metrics(t)[name] for t in subset]
            group["metrics"][name] = dict(
                mean=statistics.mean(values),
                median=statistics.median(values),
                min=min(values),
                max=max(values),
            )
    return result


def run(destination: Path) -> dict[str, Any]:
    frozen = check_freeze()
    protocol = json.loads((DIRECTORY / "protocol.json").read_text())
    models = {n: FrontierModel(MODELS / f"{n}.json") for n in ("selected", "linear")}
    model_freeze = json.loads((MODELS / "frozen.json").read_text())
    if model_freeze["protocol_sha256"] != digest(DIRECTORY / "protocol.json"):
        raise ValueError("Model selection protocol differs")
    for name, model in models.items():
        if (
            model.sha256 != model_freeze["models"][name]
            or model.artifact.provenance["evaluation_accessed"]
        ):
            raise ValueError("Changed model or test tuning")
        if not set(cast(list[str], model.artifact.provenance["training_ids"])) <= set(
            frozen["permitted_development_ids"]
        ):
            raise ValueError("Forbidden frontier training IDs")
    tasks = read_tasks()
    budget = Budget.model_validate(protocol["budget"])
    phase2, outcome = LearnedRanking(), OutcomeRanking()
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = dict(
        **metadata(),
        started_at=datetime.now(UTC).isoformat(),
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        dataset_sha256=digest(DIRECTORY / "evaluation.json"),
        freeze_sha256=digest(DIRECTORY / "frozen.json"),
        model_freeze_sha256=digest(MODELS / "frozen.json"),
        model_sha256={n: m.sha256 for n, m in models.items()},
        phase2_model_sha256=phase2.model_hash,
        outcome_model_sha256=outcome.model_hash,
        workers=protocol["workers"],
        affinity_cpus=len(os.sched_getaffinity(0)),
        source_sha256={
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted((ROOT / "src/prooflab").glob("*.py"))
        },
        notes=(
            "Two workers; rotated interleaving. All ProofLab arms include same score/explanation "
            "overhead; no added Lean lookahead. Native references use different internal units. "
            "Linear ablation duplicates selected architecture if validation selects linear; "
            "not independent evidence."
        ),
    )
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    families = json.loads((DIRECTORY / "families.json").read_text())
    traces = []
    for repeat in range(protocol["repetitions"]):
        algorithms = cast(list[SearchAlgorithm], protocol["algorithms"])
        with ThreadPoolExecutor(max_workers=protocol["workers"]) as pool:
            futures = []
            for index, task in enumerate(tasks):
                offset = (index + repeat) % len(algorithms)
                for a in algorithms[offset:] + algorithms[:offset]:
                    futures.append(
                        pool.submit(
                            search,
                            task,
                            a,
                            budget,
                            ranking=phase2
                            if a == "learned"
                            else outcome
                            if a in ("outcome", "joint", "beam", "linear_frontier")
                            else None,
                            comparison_ranker=phase2,
                            comparison_outcome=outcome,
                            comparison_frontier=models[
                                "linear" if a == "linear_frontier" else "selected"
                            ],
                            beam_width=protocol["beam_width"],
                        )
                    )
            for future in as_completed(futures):
                t = future.result()
                t.metadata.update(repeat=str(repeat), family=families[t.task.id])
                traces.append(t)
                name = f"{t.task.id}--{t.algorithm}--r{repeat}"
                (destination / "traces" / f"{name}.json").write_text(
                    t.model_dump_json(indent=2) + "\n"
                )
                print(
                    name,
                    t.status,
                    t.termination,
                    t.metrics.attempted_candidates,
                    f"{t.metrics.elapsed_s:.2f}s",
                    flush=True,
                )
    traces.sort(key=lambda t: (t.task.id, t.algorithm, t.metadata["repeat"]))
    result = dict(
        provenance=provenance, **report(traces, {**protocol, "evaluation_families": families})
    )
    (destination / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    with (destination / "results.csv").open("w", newline="") as out:
        columns = [
            "task",
            "family",
            "algorithm",
            "repeat",
            "status",
            "termination",
            *METRICS,
            *extra_metrics(traces[0]),
        ]
        writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for t in traces:
            writer.writerow(
                dict(
                    task=t.task.id,
                    family=t.metadata["family"],
                    algorithm=t.algorithm,
                    repeat=t.metadata["repeat"],
                    status=t.status,
                    termination=t.termination,
                    **{m: getattr(t.metrics, m) for m in METRICS},
                    **extra_metrics(t),
                )
            )
    compact(destination)
    return result
