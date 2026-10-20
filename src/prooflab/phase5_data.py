"""New typed benchmark and immutable Phase 1–4 evidence boundary."""

from __future__ import annotations
import json
from typing import Any
from prooflab.dataset import load_tasks, load_phase2_tasks, load_phase3_tasks
from prooflab.lean import ROOT
from prooflab.models import Task
from prooflab.phase3_data import digest
from prooflab.phase4_data import check_freeze as check_previous, read_tasks as phase4_tasks
from prooflab.splits import native_structures, graph_hash, equivalent

DIRECTORY = ROOT / "benchmarks/phase5"


def read_tasks(name: str = "evaluation") -> list[Task]:
    if name not in ("evaluation", "pilot"):
        raise ValueError("Unknown Phase 5 dataset")
    return [Task.model_validate(t) for t in json.loads((DIRECTORY / f"{name}.json").read_text())]


def freeze() -> dict[str, Any]:
    if (DIRECTORY / "frozen.json").exists():
        raise ValueError("Already frozen")
    check_previous()
    old = [
        *load_tasks(),
        *load_phase2_tasks(),
        *load_phase3_tasks(),
        *phase4_tasks(),
        *phase4_tasks("pilot"),
    ]
    old += [
        Task.model_validate(t)
        for t in json.loads((ROOT / "benchmarks/phase3/pilot.json").read_text())
    ]
    old += read_tasks("pilot")
    final = read_tasks()
    if len(final) != 40 or len({t.id for t in [*old, *final]}) != len(old) + len(final):
        raise ValueError("Task count or IDs")
    trees = native_structures([*old, *final])
    hashes = {i: graph_hash(t) for i, t in trees.items()}
    for i, t in enumerate(final):
        for o in [*old, *final[:i]]:
            if hashes[t.id] == hashes[o.id] and equivalent(trees[t.id], trees[o.id]):
                raise ValueError(f"Equivalent {t.id}/{o.id}")
    prior = {}
    for folder in ("benchmarks/phase4", "models/phase4", "experiments/phase4", "research/phase4"):
        for p in sorted((ROOT / folder).rglob("*")):
            if p.is_file():
                prior[str(p.relative_to(ROOT))] = digest(p)
    for p in sorted((ROOT / "artifacts").glob("phase4*")):
        if p.is_file():
            prior[str(p.relative_to(ROOT))] = digest(p)
    for p in sorted((ROOT / "docs").glob("phase-4*")):
        if p.is_file():
            prior[str(p.relative_to(ROOT))] = digest(p)
    files = {
        n: digest(DIRECTORY / n)
        for n in (
            "evaluation.json",
            "pilot.json",
            "families.json",
            "protocol.json",
            "declarations.json",
        )
    }
    data = dict(
        schema_version=1,
        base_revision="2df4d3d03b1968a490dff8725cca39f70f55faca",
        files=files,
        prior_phase4=prior,
        permitted_development_ids=[t.id for t in load_tasks() if t.split == "development"],
        validation_ids=[
            t.id for t in load_tasks() if t.split == "development" and t.domain == "order"
        ],
        expression_trees=trees,
        graph_hashes=hashes,
        duplicate_pairs=[],
        limits="Reducible native typed graph isomorphism with binder permutations, not arbitrary semantic equivalence. Manual family review in docs/phase-5-data.md; shared primitives expected.",
    )
    (DIRECTORY / "frozen.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


def check_freeze() -> dict[str, Any]:
    check_previous()
    data: dict[str, Any] = json.loads((DIRECTORY / "frozen.json").read_text())
    for name, sha in data["files"].items():
        if digest(DIRECTORY / name) != sha:
            raise ValueError("Frozen Phase 5 data/procedure changed: " + name)
    for name, sha in data["prior_phase4"].items():
        if digest(ROOT / name) != sha:
            raise ValueError("Prior evidence changed: " + name)
    return data
