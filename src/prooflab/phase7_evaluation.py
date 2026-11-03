"""Preregistered, complete equal-budget comparisons with immutable failed runs."""

from __future__ import annotations

import csv
import random
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any, cast

from prooflab.budget_policy import MODEL_DIR, BudgetModel
from prooflab.budget_search import run as budget_search
from prooflab.lean import ROOT, theorem_source
from prooflab.models import Budget, Task, Trace
from prooflab.phase3_data import digest
from prooflab.phase6_evaluation import check_execution as check_previous
from prooflab.phase6_execution import run_task
from prooflab.phase7_data import DATA, DIRECTORY, check_freeze, protocol, save, source_hashes, tasks
from prooflab.research_io import read_json
from prooflab.search import metadata

EXPERIMENT = ROOT / "experiments/phase7/evaluation-v1"
FROZEN = MODEL_DIR / "frozen.json"


def freeze_execution() -> dict[str, Any]:
    check_freeze()
    check_previous()
    if FROZEN.exists() or (EXPERIMENT / "traces").exists():
        raise ValueError("Cannot freeze after evaluation starts")
    model = BudgetModel()
    root = BudgetModel(MODEL_DIR / "root-trained.json")
    evaluation_ids = {t.id for t in tasks("evaluation")}
    for m in (model, root):
        if set(m.artifact["training_ids"]) & evaluation_ids:
            raise ValueError("Evaluation training leakage")
    sources = source_hashes()
    for name in ("phase7_training.py", "phase7_evaluation.py"):
        p = ROOT / "src/prooflab" / name
        sources[str(p.relative_to(ROOT))] = digest(p)
    sources["benchmarks/phase7/cost-semantics.json"] = digest(DIRECTORY / "cost-semantics.json")
    frozen = dict(
        **metadata(),
        frozen_at=datetime.now(UTC).isoformat(),
        evaluation_accessed=False,
        test_runs_before_freeze=0,
        input_sha256=digest(DIRECTORY / "frozen.json"),
        collection_sha256=digest(DATA / "manifest.json"),
        source_sha256=sources,
        models_sha256={str(p.relative_to(ROOT)): digest(p) for p in MODEL_DIR.glob("*.json")},
    )
    save(FROZEN, frozen)
    return frozen


def check_execution() -> dict[str, Any]:
    check_freeze()
    check_previous()
    f = read_json(FROZEN)
    if digest(DIRECTORY / "frozen.json") != f["input_sha256"]:
        raise ValueError("Frozen inputs changed")
    if digest(DATA / "manifest.json") != f["collection_sha256"]:
        raise ValueError("Collection changed")
    for name, sha in {**f["source_sha256"], **f["models_sha256"]}.items():
        if digest(ROOT / name) != sha:
            raise ValueError("Frozen Phase 7 execution changed: " + name)
    return f


def execute_task(task: Task, arm: str, budget: Budget, cancel: Event | None = None) -> Trace:
    if arm not in protocol()["arms"]:
        raise ValueError("Unregistered Phase 7 arm")
    if arm in ("phase4", "phase6_staged", "phase6_learned", "automation", "grind"):
        mode = {"phase6_staged": "staged", "phase6_learned": "learned"}.get(arm, arm)
        return run_task(task, mode, budget, cancel=cancel)
    return budget_search(
        task,
        budget,
        "conservative" if arm == "root_trained" else arm,
        model_path=MODEL_DIR / "root-trained.json" if arm == "root_trained" else None,
        cancel=cancel,
    )


def run(destination: Path = EXPERIMENT, resume: bool = False) -> None:
    frozen = check_execution()
    config = protocol()
    destination.mkdir(parents=True, exist_ok=resume)
    (destination / "traces").mkdir(exist_ok=resume)
    provenance = dict(
        **metadata(),
        started_at=datetime.now(UTC).isoformat(),
        no_retuning=True,
        execution_freeze_sha256=digest(FROZEN),
        source_sha256=frozen["source_sha256"],
        model_sha256=frozen["models_sha256"],
        workers=config["workers"],
        budget=config["evaluation_budget"],
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
    )
    pp = destination / "provenance.json"
    if pp.exists():
        if read_json(pp)["execution_freeze_sha256"] != provenance["execution_freeze_sha256"]:
            raise ValueError("Resume freeze mismatch")
    else:
        save(pp, provenance)
    jobs = [(task, arm) for task in tasks("evaluation") for arm in config["arms"]]
    random.Random(config["seed"]).shuffle(jobs)

    def one(job: Any) -> None:
        task, arm = job
        path = destination / "traces" / f"{task.id}--{arm}.json.gz"
        if path.exists():
            return
        started = time.monotonic()
        budget = Budget.model_validate(config["evaluation_budget"])
        trace = execute_task(task, arm, budget)
        if "strategy_switches" not in trace.metadata:
            decisions = [q["decision"] for q in trace.retrievals if q.get("decision")]
            trace.metadata["strategy_switches"] = str(
                sum(a != b for a, b in zip(decisions, decisions[1:], strict=False))
            )
        trace.metadata.update(
            arm=arm,
            repeat="0",
            phase="7",
            role="frozen unseen-family evaluation",
            execution_freeze_sha256=digest(FROZEN),
            runner_wall_s=str(time.monotonic() - started),
        )
        save(path, trace.model_dump())
        print(task.id, arm, trace.status, trace.metrics.attempted_candidates, flush=True)

    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        list(pool.map(one, jobs))
    finalize(destination)


def interval(values: list[float], groups: list[str] | None = None) -> dict[str, float]:
    rng = random.Random(707)
    samples = []
    if groups:
        mapping: dict[str, list[float]] = defaultdict(list)
        for group, value in zip(groups, values, strict=True):
            mapping[group].append(value)
        means = [statistics.mean(v) for v in mapping.values()]
    else:
        means = values
    for _ in range(10000):
        samples.append(statistics.mean(rng.choices(means, k=len(means))))
    samples.sort()
    return dict(estimate=statistics.mean(means), lower=samples[249], upper=samples[9749])


def finalize(destination: Path = EXPERIMENT) -> dict[str, Any]:
    check_execution()
    config = protocol()
    families = read_json(DIRECTORY / "families.json")
    expected = {(t.id, arm) for t in tasks("evaluation") for arm in config["arms"]}
    observed = set()
    rows = []
    files = {}
    for path in sorted((destination / "traces").glob("*.json.gz")):
        trace = Trace.model_validate(read_json(path))
        arm = trace.metadata["arm"]
        key = (trace.task.id, arm)
        if key in observed:
            raise ValueError("Duplicate final execution")
        observed.add(key)
        if trace.budget.model_dump() != config["evaluation_budget"]:
            raise ValueError("Unequal registered budget")
        if trace.verification.verified != (trace.status == "verified"):
            raise ValueError("Inconsistent mathematical audit")
        if trace.verification.verified:
            import hashlib

            if (
                hashlib.sha256(theorem_source(trace.task, trace.proof).encode()).hexdigest()
                != trace.verification.source_sha256
            ):
                raise ValueError("Proof source hash mismatch")
        files[str(path.relative_to(destination))] = digest(path)
        rows.append(
            dict(
                task_id=trace.task.id,
                family=families[trace.task.id],
                arm=arm,
                status=trace.status,
                termination=trace.termination,
                verified=int(trace.verification.verified),
                attempts=trace.metrics.attempted_candidates,
                expansions=trace.metrics.expanded_states,
                accepted=trace.metrics.accepted_transitions,
                states=sum(n.state is not None for n in trace.nodes),
                wall_s=trace.metrics.elapsed_s,
                runner_wall_s=float(trace.metadata["runner_wall_s"]),
                query_s=trace.metrics.retrieval_s,
                queries=trace.metrics.retrieval_queries,
                inference_s=trace.metrics.model_inference_s,
                verification_s=trace.metrics.verification_s,
                lean_s=trace.metrics.lean_execution_s,
                heartbeats=trace.metrics.tactic_heartbeats + trace.metrics.retrieval_heartbeats,
                session_cpu_s=trace.metrics.session_cpu_s,
                session_peak_rss_kib=trace.metrics.session_peak_rss_kib,
                switches=int(trace.metadata.get("strategy_switches", "0")),
                proof_length=len(trace.proof),
                file=str(path.relative_to(destination)),
            )
        )
    if observed != expected:
        raise ValueError(f"Incomplete matrix: {len(observed)}/{len(expected)}")
    with (destination / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    results = {}
    for arm in config["arms"]:
        selected = [r for r in rows if r["arm"] == arm]
        results[arm] = dict(
            runs=len(selected),
            verified=sum(r["verified"] for r in selected),
            errors=sum(r["status"] == "execution_error" for r in selected),
            terminations=dict(Counter(r["termination"] for r in selected)),
            means={
                key: statistics.mean(
                    cast(list[float], [r[key] for r in selected if r[key] is not None])
                )
                for key in (
                    "attempts",
                    "expansions",
                    "wall_s",
                    "query_s",
                    "inference_s",
                    "verification_s",
                    "switches",
                    "states",
                    "heartbeats",
                )
            },
            by_family={
                f: sum(r["verified"] for r in selected if r["family"] == f)
                for f in sorted({r["family"] for r in selected})
            },
        )
    contrasts = {}
    indexed = {(r["task_id"], r["arm"]): r for r in rows}
    for a, b in [
        ("conservative", "phase6_staged"),
        ("joint", "phase6_staged"),
        ("completion", "phase6_staged"),
        ("conservative", "staged"),
        ("conservative", "root_trained"),
        ("joint", "cost"),
    ]:
        diffs = []
        groups = []
        gains = []
        losses = []
        common = []
        for task in tasks("evaluation"):
            left, right = indexed[(task.id, a)], indexed[(task.id, b)]
            delta = left["verified"] - right["verified"]
            diffs.append(float(delta))
            groups.append(families[task.id])
            if delta > 0:
                gains.append(task.id)
            if delta < 0:
                losses.append(task.id)
            if left["verified"] and right["verified"]:
                common.append(left["attempts"] - right["attempts"])
        contrasts[a + " minus " + b] = dict(
            theorem_interval=interval(diffs),
            family_interval=interval(diffs, groups),
            gains=gains,
            regressions=losses,
            common_verified=len(common),
            common_verified_mean_attempt_difference=statistics.mean(common) if common else None,
        )
    summary = dict(
        runs=len(rows),
        tasks=48,
        results=results,
        comparisons=contrasts,
        budget=config["evaluation_budget"],
        no_retuning=True,
        per_run=rows,
        provenance=read_json(destination / "provenance.json"),
    )
    save(destination / "summary.json", summary)
    save(destination / "trace-storage.json", files)
    return summary
