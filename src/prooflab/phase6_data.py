"""Phase 6 curriculum boundary, typed graph audit and immutable historical evidence."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from prooflab.lean import ROOT
from prooflab.models import Task
from prooflab.phase3_data import digest
from prooflab.phase5_data import check_freeze as check_previous
from prooflab.phase5_evaluation import check_execution as check_previous_execution
from prooflab.splits import equivalent, graph_hash, native_structures

DIRECTORY = ROOT / "benchmarks/phase6"
VALIDATION_FAMILIES = ("continuation_logic", "lattice_maps", "set_difference", "product_graphs")


def read_tasks(name: str = "evaluation") -> list[Task]:
    if name not in ("evaluation", "development"):
        raise ValueError("Unregistered Phase 6 split")
    return [Task.model_validate(x) for x in json.loads((DIRECTORY / f"{name}.json").read_text())]


def freeze() -> dict[str, Any]:
    if (DIRECTORY / "frozen.json").exists():
        raise ValueError("Dataset already frozen")
    previous = check_previous()
    check_previous_execution()
    dev, test = read_tasks("development"), read_tasks()
    if len(dev) != 160 or len(test) != 48 or len({t.id for t in dev + test}) != 208:
        raise ValueError("Unexpected curriculum/evaluation size")
    trees = native_structures(dev + test)
    groups: dict[str, list[tuple[str, list[Any]]]] = defaultdict(list)
    duplicates = []
    for ident, tree in [*previous["expression_trees"].items(), *trees.items()]:
        sha = graph_hash(tree)
        for other, old in groups[sha]:
            if ident in trees and equivalent(tree, old):
                duplicates.append([ident, other])
        groups[sha].append((ident, tree))
    if duplicates:
        raise ValueError("Structural duplicates: " + repr(duplicates))
    previous_files = {}
    for pattern in (
        "benchmarks/phase[1-5]/**",
        "benchmarks/tasks.json",
        "models/**",
        "experiments/**",
        "research/**",
        "docs/phase-[1-5]*",
        "artifacts/phase[1-5]*",
    ):
        for p in ROOT.glob(pattern):
            if p.is_file():
                previous_files[str(p.relative_to(ROOT))] = digest(p)
    # Include all descendants, not merely direct glob directory entries.
    for folder in ("benchmarks", "models", "experiments", "research"):
        for p in (ROOT / folder).rglob("*"):
            if p.is_file() and "/phase6/" not in str(p):
                previous_files[str(p.relative_to(ROOT))] = digest(p)
    families = json.loads((DIRECTORY / "families.json").read_text())
    data = dict(
        schema_version=1,
        base_revision="4cc061edf338e5d581f73f3b843fec503d7e6e64",
        files={
            n: digest(DIRECTORY / n)
            for n in ("development.json", "evaluation.json", "families.json", "protocol.json")
        },
        prior_evidence=previous_files,
        training_ids=[t.id for t in dev if families[t.id] not in VALIDATION_FAMILIES],
        validation_ids=[t.id for t in dev if families[t.id] in VALIDATION_FAMILIES],
        development_ids=[t.id for t in dev],
        evaluation_ids=[t.id for t in test],
        validation_families=VALIDATION_FAMILIES,
        expression_trees=trees,
        graph_hashes={i: graph_hash(t) for i, t in trees.items()},
        historical_structures_sha256=digest(ROOT / "benchmarks/phase5/frozen.json"),
        duplicate_pairs=[],
        audit_limits=(
            "Native reducible typed expression graphs; alpha/binder permutation "
            "invariance, not arbitrary logical equivalence or absence of shared proof "
            "primitives. Family registry/manual review complement the structural audit. "
            "Historical tasks diagnosis only; no labels imported."
        ),
    )
    (DIRECTORY / "frozen.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


def check_freeze() -> dict[str, Any]:
    check_previous()
    check_previous_execution()
    data: dict[str, Any] = json.loads((DIRECTORY / "frozen.json").read_text())
    for name, sha in data["files"].items():
        if digest(DIRECTORY / name) != sha:
            raise ValueError("Phase 6 frozen input changed: " + name)
    for name, sha in data["prior_evidence"].items():
        if digest(ROOT / name) != sha:
            raise ValueError("Historical evidence changed: " + name)
    return data


def check_archive(directory: Path) -> None:
    """Validate canonical compressed training evidence against its recorded index."""
    from prooflab.research_io import read_json, trace_paths

    paths = trace_paths(directory / "traces")
    storage = read_json(directory / "trace-storage.json")["traces"]
    if {p.name for p in paths} != {r["file"] for r in storage.values()}:
        raise ValueError("Archive index mismatch")
    for row in storage.values():
        if digest(directory / "traces" / row["file"]) != row["gzip_sha256"]:
            raise ValueError("Changed source search archive")
    if (directory / "action-storage.json").exists():
        actions = read_json(directory / "action-storage.json")
        if {p.name for p in trace_paths(directory / "actions")} != set(actions):
            raise ValueError("Action archive index mismatch")
        for name, row in actions.items():
            if digest(directory / "actions" / name) != row["sha256"]:
                raise ValueError("Changed executed action archive")
