"""Frozen generation × scheduling matrix; actual independent audits only."""

from __future__ import annotations

import csv
import json
import os
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from prooflab.frontier import FrontierModel
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, SearchAlgorithm, Trace
from prooflab.native_retrieval import RetrievalSession
from prooflab.outcome import OutcomeRanking
from prooflab.phase3_data import digest
from prooflab.phase5_data import DIRECTORY, check_freeze, read_tasks
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.retrieval import MODEL, RetrievalRanker, TypedProvider
from prooflab.search import metadata, search

EXPERIMENT = ROOT / "experiments/phase5/evaluation-v1"
FROZEN = ROOT / "models/phase5/frozen.json"
SOURCE_FILES = [
    "ProofLab/Retrieval.lean",
    *[
        str(p.relative_to(ROOT))
        for p in sorted((ROOT / "src/prooflab").glob("*.py"))
        if p.name not in ("server.py", "cli.py", "__init__.py")
    ],
]
METRICS = [
    "attempted_candidates",
    "expanded_states",
    "proof_length",
    "elapsed_s",
    "lean_execution_s",
    "initialization_s",
    "verification_s",
    "planning_s",
    "model_inference_s",
    "retrieval_s",
    "retrieval_queries",
    "declaration_probes",
    "rewrite_probes",
    "term_constructions",
    "retrieval_heartbeats",
    "tactic_heartbeats",
    "coordinator_cpu_s",
    "session_cpu_s",
    "session_peak_rss_kib",
]


def freeze_execution() -> None:
    check_freeze()
    if FROZEN.exists():
        raise ValueError("Execution already frozen")
    ranker = RetrievalRanker()
    if set(ranker.artifact["training_ids"]) != set(check_freeze()["permitted_development_ids"]):
        raise ValueError("Model training boundary")
    data = dict(
        **metadata(),
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        dataset_sha256=digest(DIRECTORY / "evaluation.json"),
        index_sha256=digest(DIRECTORY / "declarations.json"),
        model_sha256=digest(MODEL),
        phase2_model_sha256=LearnedRanking().model_hash,
        phase3_model_sha256=OutcomeRanking().model_hash,
        phase4_model_sha256=FrontierModel().sha256,
        source_sha256={n: digest(ROOT / n) for n in SOURCE_FILES},
        evaluation_accessed=False,
    )
    FROZEN.write_text(json.dumps(data, indent=2) + "\n")


def check_execution() -> dict[str, Any]:
    check_freeze()
    frozen = read_json(FROZEN)
    for name, sha in frozen["source_sha256"].items():
        if digest(ROOT / name) != sha:
            raise ValueError("Frozen execution source changed: " + name)
    if digest(MODEL) != frozen["model_sha256"]:
        raise ValueError("Changed retrieval model")
    return frozen


def coverage(t: Trace) -> dict[str, float]:
    entered = displaced = compatible = rejected = attempted = path_available = path_total = 0
    for query in t.retrievals:
        entered += len(query.get("entered", []))
        displaced += len(query.get("displaced", []))
        rows = {r["candidate"]["tactic"]: r for r in query.get("pool", [])}
        children = [n for n in t.nodes if n.parent == query["node_id"]]
        for n in children:
            row = rows.get(n.tactic or "", {})
            if row.get("compatible") is not None and row.get("family") != "normalizer":
                attempted += 1
                compatible += int(row["compatible"])
                rejected += int(row["compatible"] and n.status == "rejected")
            if n.on_proof_path:
                path_total += 1
                path_available += int(n.tactic in query["selected"])
    return dict(
        entered=entered,
        displaced=displaced,
        native_annotated_attempts=attempted,
        type_compatible_attempts=compatible,
        compatible_but_rejected=rejected,
        proof_path_selected=path_available,
        verified_path_actions=path_total,
    )


def availability_audit(traces: list[Trace]) -> dict[str, Any]:
    """Observed verified next actions at identical native-session tactic prefixes.

    This is partial witnessed availability, not complete mathematical recall.
    No printed-state equivalence, hypothetical action, or negative label is used.
    """
    known: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
    for t in traces:
        if t.status != "verified" or t.algorithm in ("automation", "grind"):
            continue
        for depth, tactic in enumerate(t.proof):
            known[(t.task.id, tuple(t.proof[:depth]))].add(tactic)
    totals: dict[str, Counter[str]] = defaultdict(Counter)
    records = []
    for t in traces:
        prefixes: dict[int, tuple[str, ...]] = {0: ()}
        for node in t.nodes[1:]:
            if node.parent is not None and node.tactic:
                prefixes[node.id] = (*prefixes[node.parent], node.tactic)
        arm = t.metadata["arm"]
        for q in t.retrievals:
            good = known.get((t.task.id, prefixes[q["node_id"]]), set())
            if not good:
                continue
            available = good & set(q["selected"])
            totals[arm]["matched_verified_prefix_states"] += 1
            totals[arm]["states_with_observed_useful_action"] += bool(available)
            totals[arm]["observed_verified_actions"] += len(good)
            totals[arm]["available_verified_actions"] += len(available)
            totals[arm]["displaced_verified_actions"] += len(good & set(q.get("displaced", [])))
            records.append(
                dict(
                    task_id=t.task.id,
                    arm=arm,
                    repeat=t.metadata["repeat"],
                    node_id=q["node_id"],
                    prefix=list(prefixes[q["node_id"]]),
                    observed_verified_actions=sorted(good),
                    available=sorted(available),
                )
            )
    return dict(
        by_arm={a: dict(v) for a, v in totals.items()},
        records=records,
        limits=(
            "Only observed complete audited paths at exact task/tactic-prefix "
            "identity. Missing actions are availability gaps relative to these"
            " witnesses, never mathematical impossibility. A reference path "
            "may use a stronger normalizer."
        ),
    )


def ci(values: list[float], seed: int = 2718, samples: int = 10000) -> list[float]:
    if not values:
        return []
    rng = random.Random(seed)
    n = len(values)
    draws = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples))
    return [draws[int(samples * 0.025)], draws[int(samples * 0.975)]]


def summarize(traces: list[Trace], protocol: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, list[Trace]] = defaultdict(list)
    for t in traces:
        groups[t.metadata["arm"]].append(t)
    results = {}
    per_theorem = []
    for arm, items in groups.items():
        metrics = {}
        for m in METRICS:
            values = [
                float(getattr(t.metrics, m)) for t in items if getattr(t.metrics, m) is not None
            ]
            metrics[m] = (
                dict(
                    mean=statistics.mean(values),
                    median=statistics.median(values),
                    min=min(values),
                    max=max(values),
                    observed=len(values),
                )
                if values
                else None
            )
        families = {
            f: dict(
                verified=sum(t.status == "verified" for t in items if t.metadata["family"] == f),
                runs=sum(t.metadata["family"] == f for t in items),
            )
            for f in sorted({t.metadata["family"] for t in items})
        }
        bytask = {
            i: [t for t in items if t.task.id == i] for i in sorted({t.task.id for t in items})
        }
        success = [statistics.mean(t.status == "verified" for t in ts) for ts in bytask.values()]
        results[arm] = dict(
            runs=len(items),
            verified=sum(t.status == "verified" for t in items),
            success_rate=statistics.mean(success),
            success_ci95=ci(success),
            metrics=metrics,
            terminations=dict(Counter(t.termination for t in items)),
            families=families,
            coverage={k: sum(coverage(t)[k] for t in items) for k in coverage(items[0])},
        )
        for ident, ts in bytask.items():
            per_theorem.append(
                dict(
                    task_id=ident,
                    arm=arm,
                    family=ts[0].metadata["family"],
                    verified=sum(t.status == "verified" for t in ts),
                    repetitions=len(ts),
                    attempts=[t.metrics.attempted_candidates for t in ts],
                    expanded=[t.metrics.expanded_states for t in ts],
                    wall_s=[t.metrics.elapsed_s for t in ts],
                    termination=[t.termination for t in ts],
                    proofs=[t.proof for t in ts],
                    trace_files=[t.metadata["trace_file"] for t in ts],
                )
            )
    comparisons = {}
    pairs = [
        ("typed_hand", "original_hand"),
        ("typed_p3", "original_p3"),
        ("learned_hand", "typed_hand"),
        ("learned_p3", "typed_p3"),
        ("typed_joint", "typed_p3"),
        ("learned_joint", "learned_p3"),
        ("phase4_hand", "original_hand"),
        ("typed_hand", "broad_hand"),
        ("typed_hand", "type_filtered_hand"),
        ("typed_hand", "no_witness_hand"),
        ("typed_hand", "no_normalize_hand"),
    ]
    for a, b in pairs:
        left = {i: [t for t in groups[a] if t.task.id == i] for i in {t.task.id for t in groups[a]}}
        right = {i: [t for t in groups[b] if t.task.id == i] for i in left}
        ids = sorted(left)
        common = [i for i in ids if all(t.status == "verified" for t in left[i] + right[i])]

        def compare(
            metric: str,
            subset: list[str],
            left: dict[str, list[Trace]] = left,
            right: dict[str, list[Trace]] = right,
        ) -> dict[str, Any]:
            def value(t: Trace) -> float:
                return (
                    float(t.status == "verified")
                    if metric == "success"
                    else float(getattr(t.metrics, metric))
                )

            differences = {
                i: statistics.mean(value(t) for t in left[i])
                - statistics.mean(value(t) for t in right[i])
                for i in subset
            }
            families = {
                f: [v for i, v in differences.items() if left[i][0].metadata["family"] == f]
                for f in {left[i][0].metadata["family"] for i in subset}
            }
            return dict(
                mean_difference=statistics.mean(differences.values()) if differences else None,
                theorems=len(subset),
                ci95_theorem=ci(list(differences.values())),
                ci95_family=ci([statistics.mean(vs) for vs in families.values()]),
                differences=differences,
            )

        comparisons[a + " minus " + b] = dict(
            success=compare("success", ids),
            all_runs={
                m: compare(m, ids)
                for m in (
                    "attempted_candidates",
                    "expanded_states",
                    "elapsed_s",
                    "lean_execution_s",
                    "retrieval_s",
                )
            },
            common_verified={
                m: compare(m, common)
                for m in (
                    "attempted_candidates",
                    "expanded_states",
                    "elapsed_s",
                    "lean_execution_s",
                    "proof_length",
                )
            },
        )
    return dict(
        availability=availability_audit(traces),
        results=results,
        comparisons=comparisons,
        per_theorem=per_theorem,
        uncertainty=protocol["uncertainty"],
        limitations=(
            "Two repeated primary runs measure execution variability, not "
            "independent new theorems. Ablations one run. Allocation "
            "heartbeats measure allocations, not inference nodes. CPU/RSS "
            "cover live session tree and coordinator; independent audits "
            "excluded from CPU/RSS but included in wall. "
            "Original/expanded/query environments identical; no total CPU "
            "claim."
        ),
    )


def finalize(destination: Path = EXPERIMENT) -> dict[str, Any]:
    protocol = read_json(DIRECTORY / "protocol.json")
    traces = [Trace.model_validate(read_json(p)) for p in trace_paths(destination / "traces")]
    expected = sum(a["repetitions"] for a in protocol["arms"]) * len(read_tasks())
    keys = {(t.task.id, t.metadata["arm"], t.metadata["repeat"]) for t in traces}
    if len(traces) != expected or len(keys) != expected:
        raise ValueError(f"Incomplete matrix: {len(traces)}/{expected}")
    result = summarize(traces, protocol)
    (destination / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    with (destination / "results.csv").open("w", newline="") as out:
        columns = [
            "task",
            "family",
            "arm",
            "repeat",
            "status",
            "termination",
            *METRICS,
            *coverage(traces[0]),
        ]
        writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for t in sorted(traces, key=lambda t: (t.task.id, t.metadata["arm"], t.metadata["repeat"])):
            writer.writerow(
                dict(
                    task=t.task.id,
                    family=t.metadata["family"],
                    arm=t.metadata["arm"],
                    repeat=t.metadata["repeat"],
                    status=t.status,
                    termination=t.termination,
                    **{m: getattr(t.metrics, m) for m in METRICS},
                    **coverage(t),
                )
            )
    compact(destination)
    return result


def run(destination: Path = EXPERIMENT) -> None:
    frozen = check_execution()
    protocol = read_json(DIRECTORY / "protocol.json")
    families = read_json(DIRECTORY / "families.json")
    phase2, outcome, frontier, ranker = (
        LearnedRanking(),
        OutcomeRanking(),
        FrontierModel(),
        RetrievalRanker(),
    )
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = dict(
        **metadata(),
        started_at=datetime.now(UTC).isoformat(),
        execution_freeze_sha256=digest(FROZEN),
        frozen=frozen,
        workers=protocol["workers"],
        affinity_cpus=len(os.sched_getaffinity(0)),
    )
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    for repeat in range(2):
        with ThreadPoolExecutor(max_workers=protocol["workers"]) as pool:
            futures = {}
            for index, task in enumerate(read_tasks()):
                arms = [a for a in protocol["arms"] if repeat < a["repetitions"]]
                offset = (index + repeat) % len(arms)
                for arm in arms[offset:] + arms[:offset]:
                    alg = cast(SearchAlgorithm, arm["algorithm"])
                    future = pool.submit(
                        search,
                        task,
                        alg,
                        Budget.model_validate(protocol["budget"]),
                        ranking=outcome if alg in ("outcome", "joint") else None,
                        comparison_ranker=phase2,
                        comparison_outcome=outcome,
                        comparison_frontier=frontier,
                        provider=TypedProvider(arm["generator"], ranker),
                        session_factory=RetrievalSession,
                    )
                    futures[future] = (arm, repeat)
            for future in as_completed(futures):
                arm, r = futures[future]
                t = future.result()
                name = f"{t.task.id}--{arm['id']}--r{r}.json"
                t.metadata.update(
                    arm=arm["id"],
                    generator_mode=arm["generator"],
                    repeat=str(r),
                    family=families[t.task.id],
                    trace_file=name + ".gz",
                    execution_freeze_sha256=digest(FROZEN),
                )
                path = destination / "traces" / name
                path.write_text(t.model_dump_json(indent=2) + "\n")
                # Compress immediately: all native index/probe data are retained.
                import gzip

                packed = gzip.compress(path.read_bytes(), compresslevel=6, mtime=0)
                path.with_suffix(".json.gz").write_bytes(packed)
                path.unlink()
                print(
                    name,
                    t.status,
                    t.termination,
                    t.metrics.attempted_candidates,
                    f"{t.metrics.elapsed_s:.3f}s",
                    flush=True,
                )
    finalize(destination)
