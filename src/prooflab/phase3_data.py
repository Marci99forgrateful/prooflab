"""Phase 3 family separation, immutable prior research, and pre-selection freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prooflab.dataset import load_phase2_tasks, load_tasks
from prooflab.lean import ROOT
from prooflab.models import Task
from prooflab.splits import equivalent, graph_hash, native_structures

DIRECTORY = ROOT / "benchmarks/phase3"


def read_tasks(name: str = "evaluation") -> list[Task]:
    if name not in ("evaluation", "pilot"):
        raise ValueError("Unknown finite Phase 3 dataset")
    return [Task.model_validate(t) for t in json.loads((DIRECTORY / f"{name}.json").read_text())]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_artifacts() -> dict[str, str]:
    paths = [ROOT / "benchmarks/tasks.json", ROOT / "models/phase2/ranker.json"]
    for name in (
        "benchmarks/phase2",
        "experiments/phase1-v1",
        "experiments/phase1-v2",
        "experiments/phase1-v3",
        "experiments/phase2-training",
        "experiments/phase2",
    ):
        paths.extend(p for p in (ROOT / name).rglob("*") if p.is_file())
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def freeze() -> dict[str, Any]:
    if (DIRECTORY / "frozen.json").exists():
        raise ValueError("Phase 3 was already frozen; do not overwrite")
    old = [*load_tasks(), *load_phase2_tasks(), *read_tasks("pilot")]
    final = read_tasks()
    if len(final) != 32 or len({t.id for t in [*old, *final]}) != len(old) + len(final):
        raise ValueError("Wrong task count or duplicate IDs")
    trees = native_structures([*old, *final])
    hashes = {ident: graph_hash(tree) for ident, tree in trees.items()}
    for index, task in enumerate(final):
        for other in [*old, *final[:index]]:
            if hashes[task.id] == hashes[other.id] and equivalent(trees[task.id], trees[other.id]):
                raise ValueError(f"Equivalent final theorem: {task.id} / {other.id}")
    result = {
        "schema_version": 1,
        "base_revision": "4373233f54ccc46e3d321814c8da384f8f2d20df",
        "files": {
            name: digest(DIRECTORY / name)
            for name in ("evaluation.json", "pilot.json", "families.json", "protocol.json")
        },
        "permitted_development_ids": [t.id for t in load_tasks() if t.split == "development"],
        "validation_ids": [
            t.id for t in load_tasks() if t.split == "development" and t.domain == "order"
        ],
        "pilot_role": "Difficulty calibration only; never training or final model selection",
        "evaluation_ids": [t.id for t in final],
        "duplicate_pairs": [],
        "normalization": (
            "Native Lean reducible reduction, erased names/universes; "
            "exact typed graph isomorphism with forall-parameter permutation"
        ),
        "limits": (
            "Excludes normalized structural duplicates, not all logical equivalence "
            "or shared subgoal/primitive overlap; family generalization is limited."
        ),
        "expression_trees": trees,
        "graph_hashes": hashes,
        "prior_artifacts": prior_artifacts(),
        "protected_code": {
            name: digest(ROOT / name)
            for name in (
                "src/prooflab/candidates.py",
                "src/prooflab/lean.py",
                "ProofLab/Bridge.lean",
            )
        },
    }
    (DIRECTORY / "frozen.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def check_freeze() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((DIRECTORY / "frozen.json").read_text())
    for name, sha in data["files"].items():
        if digest(DIRECTORY / name) != sha:
            raise ValueError("Frozen Phase 3 data/protocol changed")
    for name, sha in {**data["prior_artifacts"], **data["protected_code"]}.items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"Prior research or protected verification/generator changed: {name}")
    return data
