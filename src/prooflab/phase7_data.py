"""Immutable Phase 7 inputs and genuine matched native continuations."""

from __future__ import annotations

import gzip
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from prooflab.budget_policy import budget_features
from prooflab.budget_search import run
from prooflab.lean import ROOT
from prooflab.models import Budget, ProofState, Task
from prooflab.phase3_data import digest
from prooflab.research_io import read_json
from prooflab.search import metadata

DIRECTORY = ROOT / "benchmarks/phase7"
DATA = ROOT / "experiments/phase7/development-v1"


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.name.endswith(".gz") else raw)


def tasks(split: str = "development") -> list[Task]:
    if split not in ("development", "evaluation"):
        raise ValueError("Unknown registered split")
    return [Task.model_validate(t) for t in read_json(DIRECTORY / f"{split}.json")]


def protocol() -> dict[str, Any]:
    return read_json(DIRECTORY / "protocol.json")


def check_freeze() -> dict[str, Any]:
    frozen = read_json(DIRECTORY / "frozen.json")
    for name, sha in frozen["files"].items():
        if digest(DIRECTORY / name) != sha:
            raise ValueError("Frozen Phase 7 input changed: " + name)
    return frozen


def source_hashes() -> dict[str, str]:
    paths = [
        ROOT / "src/prooflab" / name
        for name in ("budget_policy.py", "budget_search.py", "phase7_data.py")
    ]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def collect(destination: Path = DATA, resume: bool = False) -> None:
    check_freeze()
    config = protocol()
    if destination.exists() and not resume:
        raise ValueError("Refusing to overwrite development evidence")
    destination.mkdir(parents=True, exist_ok=resume)
    provenance = dict(
        **metadata(),
        source_sha256=source_hashes(),
        protocol_sha256=digest(DIRECTORY / "protocol.json"),
        data_freeze_sha256=digest(DIRECTORY / "frozen.json"),
        evaluation_accessed=False,
        source_state_rule=config["source_state_rule"],
        workers=config["workers"],
    )
    pp = destination / "provenance.json"
    if pp.exists():
        old = read_json(pp)
        if any(
            old[k] != provenance[k]
            for k in ("source_sha256", "protocol_sha256", "data_freeze_sha256")
        ):
            raise ValueError("Cannot resume collection under changed source or inputs")
    else:
        save(pp, provenance)
    selected = tasks()
    random.Random(config["seed"]).shuffle(selected)

    def one(task: Task) -> None:
        source_path = destination / "sources" / f"{task.id}.json.gz"
        if source_path.exists():
            source = read_json(source_path)
        else:
            source = run(
                task, Budget.model_validate(config["source_budget"]), "staged"
            ).model_dump()
            save(source_path, source)
        # Pick by actual expansion order, without requiring source success.
        intermediate = next((q["node_id"] for q in source["retrievals"] if q["node_id"] != 0), None)
        if intermediate is None:
            intermediate = next(
                (n["id"] for n in source["nodes"][1:] if n["state"] and n["state"]["goals"]), None
            )
        prefixes: list[list[str]] = [[]]
        if intermediate is not None:
            tactic_path: list[str] = []
            node = source["nodes"][intermediate]
            while node["parent"] is not None:
                tactic_path.insert(0, node["tactic"])
                node = source["nodes"][node["parent"]]
            prefixes.append(tactic_path)
        for si, prefix in enumerate(prefixes):
            for bi, raw_budget in enumerate(config["collection_budgets"]):
                budget = Budget.model_validate(raw_budget)
                for mode in config["strategies"]:
                    key = f"{task.id}--s{si}--b{bi}--{mode}"
                    path = destination / "traces" / f"{key}.json.gz"
                    if path.exists():
                        continue
                    trace = run(task, budget, "staged", prefix=prefix, forced_mode=mode)
                    trace.metadata.update(
                        collection_key=key,
                        source_state=str(si),
                        budget_level=str(bi),
                        arm=mode,
                        role="development-only matched continuation",
                        source_trace_sha256=digest(source_path),
                    )
                    save(path, trace.model_dump())
                    print(key, trace.status, trace.metrics.attempted_candidates, flush=True)

    with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
        list(pool.map(one, selected))
    rows = []
    for path in sorted((destination / "traces").glob("*.json.gz")):
        trace = read_json(path)
        nodes = trace["nodes"]
        q = trace["retrievals"]
        state = nodes[0]["state"] if nodes else None
        status = trace["status"]
        target = (
            1
            if status == "verified" and trace["verification"]["verified"]
            else 0
            if status == "not_found_within_budget"
            else None
        )
        row = dict(
            key=trace["metadata"]["collection_key"],
            task_id=trace["task"]["id"],
            family=read_json(DIRECTORY / "families.json")[trace["task"]["id"]],
            source_state=int(trace["metadata"]["source_state"]),
            budget_level=int(trace["metadata"]["budget_level"]),
            prefix=json.loads(trace["metadata"]["prefix"]),
            mode=trace["metadata"]["arm"],
            state=state,
            features=q[0]["budget_features"]
            if q
            else budget_features(
                ProofState.model_validate(state),
                Budget.model_validate(trace["budget"]),
            )
            if state
            else None,
            baseline=q[0]["baseline_decision"] if q else None,
            completion=target,
            conditional_attempts=trace["metrics"]["attempted_candidates"] if target == 1 else None,
            status=status,
            termination=trace["termination"],
            metrics=trace["metrics"],
            verification=trace["verification"],
            trace_file=str(path.relative_to(destination)),
            sha256=digest(path),
        )
        rows.append(row)
    save(destination / "rows.json.gz", rows)
    save(
        destination / "manifest.json",
        dict(
            rows=len(rows),
            verified=sum(r["completion"] == 1 for r in rows),
            bounded_noncompletion=sum(r["completion"] == 0 for r in rows),
            missing=sum(r["completion"] is None for r in rows),
            sources={
                str(p.relative_to(destination)): digest(p)
                for p in sorted((destination / "sources").glob("*.gz"))
            },
            files={r["trace_file"]: r["sha256"] for r in rows},
            rows_sha256=digest(destination / "rows.json.gz"),
            evaluation_accessed=False,
        ),
    )
