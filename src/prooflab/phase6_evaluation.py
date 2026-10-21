"""Frozen Phase 6 equal-budget experiments and bounded-memory paired reporting."""

from __future__ import annotations

import csv
import json
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prooflab.adaptive_model import MODELS, AdaptiveModel
from prooflab.adaptive_training import save
from prooflab.lean import ROOT
from prooflab.models import Budget, Trace
from prooflab.phase3_data import digest
from prooflab.phase5_evaluation import METRICS, ci, coverage
from prooflab.phase6_data import DIRECTORY, check_archive, check_freeze, read_tasks
from prooflab.phase6_execution import run_task
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.search import metadata

EXPERIMENT = ROOT / "experiments/phase6/evaluation-v1"
FROZEN = MODELS / "frozen.json"
SOURCES = [
    "benchmarks/phase6/selector-protocol.json",
    "benchmarks/phase6/selector-frozen.json",
    "experiments/phase6/development-v1/trace-storage.json",
    "experiments/phase6/development-v1/action-storage.json",
    "experiments/phase6/selector-v1/trace-storage.json",
    "ProofLab/Adaptive.lean",
    *[
        str(p.relative_to(ROOT))
        for pattern in ("adaptive*.py", "phase6*.py")
        for p in sorted((ROOT / "src/prooflab").glob(pattern))
    ],
]


def freeze_execution() -> dict[str, Any]:
    check_freeze()
    if FROZEN.exists():
        raise ValueError("Execution already frozen")
    for mode in ("learned", "linear", "applicability"):
        model = AdaptiveModel(variant=mode)
        if set(model.artifact["training_ids"]) != set(check_freeze()["development_ids"]):
            raise ValueError("Training boundary mismatch")
    data = dict(
        **metadata(),
        evaluation_accessed=False,
        data_freeze_sha256=digest(DIRECTORY / "frozen.json"),
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        source_sha256={n: digest(ROOT / n) for n in SOURCES},
        models_sha256={str(p.relative_to(ROOT)): digest(p) for p in sorted(MODELS.glob("*.json"))},
        ordering=(
            "All final new arms use canonical P3 ties; original historical "
            "controls retain their original policy"
        ),
        test_runs_before_freeze=0,
    )
    FROZEN.write_text(json.dumps(data, indent=2) + "\n")
    return data


def check_execution() -> dict[str, Any]:
    check_freeze()
    check_archive(ROOT / "experiments/phase6/development-v1")
    check_archive(ROOT / "experiments/phase6/selector-v1")
    data = read_json(FROZEN)
    for name, sha in {**data["source_sha256"], **data["models_sha256"]}.items():
        if digest(ROOT / name) != sha:
            raise ValueError("Frozen Phase 6 execution changed: " + name)
    return data


def run(destination: Path = EXPERIMENT, resume: bool = False) -> None:
    frozen = check_execution()
    protocol = read_json(DIRECTORY / "protocol.json")
    families = read_json(DIRECTORY / "families.json")
    destination.mkdir(parents=True, exist_ok=resume)
    (destination / "traces").mkdir(exist_ok=resume)
    provenance = dict(
        **metadata(),
        started_at=datetime.now(UTC).isoformat(),
        execution_freeze_sha256=digest(FROZEN),
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        source_sha256=frozen["source_sha256"],
        model_hashes=frozen["models_sha256"],
        workers=protocol["workers"],
        budgets=protocol["budgets"],
        no_retuning=True,
    )
    file = destination / "provenance.json"
    if (
        file.exists()
        and read_json(file)["execution_freeze_sha256"] != provenance["execution_freeze_sha256"]
    ):
        raise ValueError("Cannot resume different execution")
    if not file.exists():
        file.write_text(json.dumps(provenance, indent=2) + "\n")
    jobs = [
        (task, arm, repeat)
        for task in read_tasks()
        for arm in protocol["arms"]
        for repeat in range(arm["repetitions"])
    ]
    random.Random(6060).shuffle(jobs)

    def one(job: Any) -> None:
        task, arm, repeat = job
        name = f"{task.id}--{arm['id']}--r{repeat}.json.gz"
        path = destination / "traces" / name
        if path.exists():
            return
        t = run_task(
            task, arm["mode"], Budget.model_validate(protocol["budgets"][arm["budget_level"]])
        )
        t.metadata.update(
            arm=arm["id"],
            family=families[task.id],
            repeat=str(repeat),
            budget_level=arm["budget_level"],
            trace_file=name,
            execution_freeze_sha256=digest(FROZEN),
        )
        save(path, t.model_dump())
        print(
            task.id,
            arm["id"],
            repeat,
            t.status,
            t.metrics.attempted_candidates,
            t.termination,
            flush=True,
        )

    with ThreadPoolExecutor(max_workers=protocol["workers"]) as pool:
        futures = [pool.submit(one, j) for j in jobs]
        for f in as_completed(futures):
            f.result()
    check_execution()
    compact(destination)
    (destination / "finished.json").write_text(
        json.dumps(
            dict(finished_at=datetime.now(UTC).isoformat(), runs=len(jobs), expected=len(jobs)),
            indent=2,
        )
        + "\n"
    )


def contrast(
    left: dict[str, list[dict[str, Any]]],
    right: dict[str, list[dict[str, Any]]],
    metric: str,
    ids: list[str],
) -> dict[str, Any]:
    def value(row: dict[str, Any]) -> float:
        return float(row["verified"]) if metric == "success" else float(row["metrics"][metric])

    diffs = {
        i: statistics.mean(value(r) for r in left[i]) - statistics.mean(value(r) for r in right[i])
        for i in ids
    }
    byfamily: dict[str, list[float]] = defaultdict(list)
    for i, v in diffs.items():
        byfamily[left[i][0]["family"]].append(v)
    family_means = [statistics.mean(byfamily[f]) for f in sorted(byfamily)]
    return dict(
        mean_difference=statistics.mean(diffs.values()) if diffs else None,
        theorems=len(ids),
        ci95_theorem=ci(list(diffs.values())),
        family_sensitivity=dict(
            estimand="equal-family mean difference, separate from theorem-weighted point",
            mean_difference=statistics.mean(family_means) if family_means else None,
            ci95=ci(family_means),
        ),
        differences=diffs,
    )


def finalize(destination: Path = EXPERIMENT) -> dict[str, Any]:
    check_execution()
    protocol = read_json(DIRECTORY / "protocol.json")
    paths = trace_paths(destination / "traces")
    expected = {
        (t.id, a["id"], str(r))
        for t in read_tasks()
        for a in protocol["arms"]
        for r in range(a["repetitions"])
    }
    rows: list[dict[str, Any]] = []
    known: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
    keys = set()
    for p in paths:
        t = Trace.model_validate(read_json(p))
        key = (t.task.id, t.metadata["arm"], t.metadata["repeat"])
        if key in keys:
            raise ValueError("Duplicate final run")
        keys.add(key)
        if (t.status == "verified") != t.verification.verified:
            raise ValueError("Uncertified success")
        if t.verification.verified and t.algorithm not in ("automation", "grind"):
            for depth, tactic in enumerate(t.proof):
                known[(t.task.id, tuple(t.proof[:depth]))].add(tactic)
        observations: Counter[str] = Counter()
        progress = []
        for q in t.retrievals:
            observations["retrieval_probe_errors"] += sum(
                r.get("family") == "probe_error" for r in q.get("native", {}).get("rows", [])
            )
            observations.update(
                dict(
                    selected=len(q["selected"]),
                    potential=len(q["pool"]),
                    entered=len(q.get("entered", [])),
                    displaced=len(q.get("displaced", [])),
                    queries=int(bool(q.get("native"))),
                    symbolic_decisions=int(q.get("decision") == "symbolic"),
                    hybrid_decisions=int(q.get("decision") == "hybrid"),
                    typed_decisions=int(q.get("decision") == "typed"),
                )
            )
            by_tactic = {r["candidate"]["tactic"]: r for r in q["pool"]}
            for n in t.nodes:
                if n.parent != q["node_id"]:
                    continue
                row = by_tactic.get(n.tactic or "", {})
                resource_rejection = n.status in ("error", "rejected") and any(
                    token in (n.error or "").lower()
                    for token in ("heartbeats", "recursion", "memory", "timeout", "exceeded")
                )
                observations["tactic_resource_failures"] += int(resource_rejection)
                if row.get("compatible") is True and row.get("family") != "normalizer":
                    observations["compatible_" + n.status] += 1
                    observations["compatible_resource_failures"] += int(resource_rejection)
                observations["attempted_" + n.status] += 1
                if n.state is not None:
                    assert n.parent is not None
                    parent = t.nodes[n.parent].state
                    if parent is not None:
                        progress.append(
                            dict(
                                node=n.id,
                                tactic=n.tactic,
                                goals_before=len(parent.goals),
                                goals_after=len(n.state.goals),
                                goal_reduction=len(parent.goals) - len(n.state.goals),
                                new_metavariables=sum(
                                    g.target.text.count("?") for g in n.state.goals
                                )
                                - sum(g.target.text.count("?") for g in parent.goals),
                                on_verified_path=n.on_proof_path,
                            )
                        )
        rows.append(
            dict(
                task_id=t.task.id,
                family=t.metadata["family"],
                arm=t.metadata["arm"],
                repeat=int(t.metadata["repeat"]),
                status=t.status,
                verified=t.verification.verified,
                termination=t.termination,
                metrics={m: getattr(t.metrics, m) for m in METRICS},
                coverage=coverage(t),
                observations=dict(observations),
                proof=t.proof,
                proof_sha256=t.verification.source_sha256,
                trace_file=p.name,
                axioms=t.verification.axioms,
                progress=progress,
            )
        )
    if keys != expected:
        raise ValueError(f"Incomplete final matrix {len(keys)}/{len(expected)}")
    results = {}
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for arm in protocol["arms"]:
        name = arm["id"]
        items = [r for r in rows if r["arm"] == name]
        bytask = {
            i: [r for r in items if r["task_id"] == i]
            for i in sorted({r["task_id"] for r in items})
        }
        groups[name] = bytask
        successes = [float(statistics.mean(r["verified"] for r in bytask[i])) for i in bytask]
        metrics = {}
        for m in METRICS:
            values = [float(r["metrics"][m]) for r in items if r["metrics"][m] is not None]
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
                verified=sum(r["verified"] for r in items if r["family"] == f),
                runs=sum(r["family"] == f for r in items),
            )
            for f in sorted({r["family"] for r in items})
        }
        totals: Counter[str] = Counter()
        for r in items:
            totals.update(r["observations"])
        results[name] = dict(
            runs=len(items),
            verified=sum(r["verified"] for r in items),
            success_rate=statistics.mean(successes),
            success_ci95=ci(successes),
            metrics=metrics,
            families=families,
            terminations=dict(Counter(r["termination"] for r in items)),
            observations=dict(totals),
            repeat_variations=[
                i
                for i, rs in bytask.items()
                if len(rs) > 1
                and len(
                    {
                        (
                            r["status"],
                            r["termination"],
                            r["metrics"]["attempted_candidates"],
                            tuple(r["proof"]),
                        )
                        for r in rs
                    }
                )
                > 1
            ],
        )
    pairs = [
        *protocol["primary_comparisons"],
        ["typed5", "phase4"],
        ["learned5", "typed5"],
        ["naive", "phase4"],
        ["deterministic", "naive"],
        ["deterministic", "fixed"],
        ["deterministic", "no_synthesis"],
        ["learned", "linear"],
        ["learned", "applicability"],
        ["staged", "deterministic"],
        ["phase4_canonical", "phase4"],
        ["automation", "phase4"],
        ["grind", "phase4"],
        ["learned_small", "phase4_small"],
        ["deterministic_small", "phase4_small"],
        ["staged_small", "phase4_small"],
    ]
    comparisons = {}
    for a, b in pairs:
        left, right = groups[a], groups[b]
        ids = sorted(left)
        common = [i for i in ids if all(r["verified"] for r in left[i] + right[i])]
        comparisons[a + " minus " + b] = dict(
            success=contrast(left, right, "success", ids),
            all_runs={
                m: contrast(left, right, m, ids)
                for m in (
                    "attempted_candidates",
                    "expanded_states",
                    "elapsed_s",
                    "retrieval_s",
                    "model_inference_s",
                )
            },
            common_verified={
                m: contrast(left, right, m, common)
                for m in (
                    "attempted_candidates",
                    "expanded_states",
                    "elapsed_s",
                    "lean_execution_s",
                    "proof_length",
                )
            },
            gains=[
                i
                for i in ids
                if statistics.mean(r["verified"] for r in left[i])
                > statistics.mean(r["verified"] for r in right[i])
            ],
            losses=[
                i
                for i in ids
                if statistics.mean(r["verified"] for r in left[i])
                < statistics.mean(r["verified"] for r in right[i])
            ],
        )
    availability: dict[str, Counter[str]] = defaultdict(Counter)
    records = []
    for path in paths:
        t = Trace.model_validate(read_json(path))
        prefixes: dict[int, tuple[str, ...]] = {0: ()}
        for n in t.nodes[1:]:
            if n.parent is not None and n.tactic:
                prefixes[n.id] = (*prefixes[n.parent], n.tactic)
        for q in t.retrievals:
            good = known.get((t.task.id, prefixes[q["node_id"]]), set())
            if not good:
                continue
            available = good & set(q["selected"])
            counts = availability[t.metadata["arm"]]
            counts["matched_states"] += 1
            counts["observed_useful_actions"] += len(good)
            counts["selected_useful_actions"] += len(available)
            counts["displaced_useful_actions"] += len(good & set(q.get("displaced", [])))
            records.append(
                dict(
                    task_id=t.task.id,
                    arm=t.metadata["arm"],
                    repeat=t.metadata["repeat"],
                    node_id=q["node_id"],
                    prefix=list(prefixes[q["node_id"]]),
                    observed_useful_actions=sorted(good),
                    available=sorted(available),
                    displaced=sorted(good & set(q.get("displaced", []))),
                )
            )
    per_theorem = []
    for arm, bytask in groups.items():
        for ident, ts in bytask.items():
            per_theorem.append(
                dict(
                    task_id=ident,
                    arm=arm,
                    family=ts[0]["family"],
                    verified=sum(t["verified"] for t in ts),
                    repetitions=len(ts),
                    attempts=[t["metrics"]["attempted_candidates"] for t in ts],
                    expanded=[t["metrics"]["expanded_states"] for t in ts],
                    wall_s=[t["metrics"]["elapsed_s"] for t in ts],
                    termination=[t["termination"] for t in ts],
                    proofs=[t["proof"] for t in ts],
                    trace_files=[t["trace_file"] for t in ts],
                )
            )
    summary = dict(
        schema_version=1,
        results=results,
        comparisons=comparisons,
        per_theorem=per_theorem,
        availability=dict(
            by_arm={a: dict(c) for a, c in availability.items()},
            records=records,
            limits=(
                "Partial witnessed recall only at exact theorem/tactic-prefix identity. "
                "Accepted or selected actions are not evidence of useful completion; "
                "opaque references excluded."
            ),
        ),
        uncertainty=protocol["uncertainty"],
        resource_limits=(
            "Equal outer budget includes retrieval/inference/audit wall. Native "
            "heartbeats are allocations, not primitive inference counts. "
            "CPU/RSS are partial live-session bounds; audit CPU/RSS excluded. "
            "Two workers on shared host, no hardware speedup claim."
        ),
        runs=len(rows),
    )
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    # Streamed progress diagnostics are kept separately from frontend summary.
    save(destination / "run-diagnostics.json.gz", dict(runs=rows))
    with (destination / "results.csv").open("w", newline="") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=["task", "family", "arm", "repeat", "status", "termination", *METRICS],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["task_id"], r["arm"], r["repeat"])):
            writer.writerow(
                dict(
                    task=row["task_id"],
                    family=row["family"],
                    arm=row["arm"],
                    repeat=row["repeat"],
                    status=row["status"],
                    termination=row["termination"],
                    **row["metrics"],
                )
            )
    return summary
