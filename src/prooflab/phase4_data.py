"""Immutable Phase 4 benchmark, overlap audit and protected prior artifacts."""

from __future__ import annotations

import json
from typing import Any

from prooflab.dataset import load_phase2_tasks, load_phase3_tasks, load_tasks
from prooflab.lean import ROOT
from prooflab.models import Task
from prooflab.phase3_data import check_freeze as check_phase3
from prooflab.phase3_data import digest
from prooflab.splits import equivalent, graph_hash, native_structures

DIRECTORY = ROOT / "benchmarks/phase4"


def read_tasks(name: str = "evaluation") -> list[Task]:
    if name not in ("evaluation", "pilot"):
        raise ValueError("Unknown Phase 4 dataset")
    return [Task.model_validate(t) for t in json.loads((DIRECTORY / f"{name}.json").read_text())]


def freeze() -> dict[str, Any]:
    if (DIRECTORY / "frozen.json").exists():
        raise ValueError("Phase 4 already frozen")
    check_phase3()
    old_pilot = json.loads((ROOT / "benchmarks/phase3/pilot.json").read_text())
    old = [
        *load_tasks(),
        *load_phase2_tasks(),
        *load_phase3_tasks(),
        *[Task.model_validate(t) for t in old_pilot],
        *read_tasks("pilot"),
    ]
    final = read_tasks()
    if len(final) != 32 or len({t.id for t in [*old, *final]}) != len(old) + len(final):
        raise ValueError("Wrong task count or duplicate ID")
    trees = native_structures([*old, *final])
    hashes = {i: graph_hash(t) for i, t in trees.items()}
    for index, task in enumerate(final):
        for other in [*old, *final[:index]]:
            if hashes[task.id] == hashes[other.id] and equivalent(trees[task.id], trees[other.id]):
                raise ValueError(f"Equivalent final theorem {task.id}/{other.id}")
    prior = {}
    for folder in ("benchmarks/phase3", "models/phase3", "experiments/phase3"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file():
                prior[str(path.relative_to(ROOT))] = digest(path)
    result = dict(
        schema_version=1,
        base_revision="98639e1cfb873f4c78ee172706b90f82d2ab212e",
        files={
            n: digest(DIRECTORY / n)
            for n in ("evaluation.json", "pilot.json", "families.json", "protocol.json")
        },
        prior_phase3=prior,
        phase3_freeze_sha256=digest(ROOT / "benchmarks/phase3/frozen.json"),
        permitted_development_ids=[t.id for t in load_tasks() if t.split == "development"],
        validation_ids=[
            t.id for t in load_tasks() if t.split == "development" and t.domain == "order"
        ],
        expression_trees=trees,
        graph_hashes=hashes,
        duplicate_pairs=[],
        limits=(
            "Native reducible typed dependency-graph isomorphism with binder permutation; "
            "not arbitrary logical equivalence. Shared primitives remain."
        ),
    )
    (DIRECTORY / "frozen.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def check_freeze() -> dict[str, Any]:
    check_phase3()
    data: dict[str, Any] = json.loads((DIRECTORY / "frozen.json").read_text())
    for name, sha in data["files"].items():
        if digest(DIRECTORY / name) != sha:
            raise ValueError("Frozen Phase 4 benchmark/procedure changed")
    for name, sha in data["prior_phase3"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Prior Phase 3 research changed: {name}")
    return data
