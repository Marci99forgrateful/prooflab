"""Offline native expression replay and grouping. Never semantic pruning."""

from __future__ import annotations

import gzip
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from prooflab.lean import ROOT, lake_command, lean_environment
from prooflab.models import Task, Trace
from prooflab.phase3_data import digest
from prooflab.research_io import read_json, trace_paths
from prooflab.search import metadata, path_to


def binder_count(text: str) -> int:
    stack = 0
    start = 0
    count = 0
    for i, char in enumerate(text):
        if char in "([{":
            if stack == 0:
                start = i + 1
            stack += 1
        elif char in ")]}":
            stack -= 1
            if stack == 0:
                block = text[start:i]
                count += len(block.split(":", 1)[0].split()) if ":" in block else 1
    if stack != 0 or count == 0:
        raise ValueError("Unsupported binder declaration")
    return count


def inspect(task: Task, prefixes: list[list[str]]) -> dict[str, dict[str, Any]]:
    commands = [
        "import ProofLab.Inspect",
        "set_option linter.unusedVariables false",
        "set_option maxHeartbeats 4000000",
    ]
    for index, prefix in enumerate(prefixes):
        script = "; ".join(prefix) if prefix else ""
        # Tactic sequences must preserve the original main-goal sequencing.
        script = "\n".join(prefix)
        block = "(\n" + script + "\n)" if prefix else ""
        commands.append(
            f'#prooflab_state "{index}" binders {binder_count(task.binders)} : '
            f"∀ {task.binders}, {task.target} := {json.dumps(block, ensure_ascii=False)}"
        )
    with tempfile.TemporaryDirectory(prefix="prooflab-native-inspect-") as directory:
        path = Path(directory) / "Inspect.lean"
        path.write_text("\n".join(commands) + "\n")
        result = subprocess.run(
            [*lake_command(), str(path)],
            cwd=ROOT,
            env=lean_environment(),
            capture_output=True,
            text=True,
            timeout=240,
        )
    if result.returncode:
        raise ValueError("Native replay failed: " + result.stdout[-2500:] + result.stderr[-1000:])
    records = {}
    for line in result.stdout.splitlines():
        if "PROOFLAB_STATE:" in line:
            record = json.loads(line.split("PROOFLAB_STATE:", 1)[1])
            records[record["label"]] = record
    if len(records) != len(prefixes):
        raise ValueError("Incomplete native state inspection")
    return records


def run(experiment: Path, destination: Path, workers: int = 2) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    groups: dict[str, list[tuple[Path, Trace]]] = {}
    for path in trace_paths(experiment / "traces"):
        trace = Trace.model_validate(read_json(path))
        groups.setdefault(trace.task.id, []).append((path, trace))

    def work(item: tuple[str, list[tuple[Path, Trace]]]) -> dict[str, Any]:
        ident, items = item
        prefixes: list[list[str]] = []
        index: dict[tuple[str, ...], int] = {}
        refs: dict[str, dict[str, Any]] = {}
        for path, trace in items:
            mapping = {}
            for node in trace.nodes:
                if node.state is None or not node.state.goals:
                    continue
                prefix = [trace.nodes[i].tactic for i in path_to(trace.nodes, node.id)[1:]]
                assert all(t is not None for t in prefix)
                key = tuple(str(t) for t in prefix)
                if key not in index:
                    index[key] = len(prefixes)
                    prefixes.append(list(key))
                mapping[str(node.id)] = index[key]
            refs[path.name] = dict(source_sha256=digest(path), nodes=mapping)
        native = inspect(items[0][1].task, prefixes)
        keys = {
            i: json.dumps([g["tree"] for g in row["goals"]], sort_keys=True)
            if not any(g["has_expr_mvar"] for g in row["goals"])
            else "unresolved-prefix:" + i
            for i, row in native.items()
        }
        stats = {}
        for path, trace in items:
            mapping = refs[path.name]["nodes"]
            distinct = len({keys[str(i)] for i in mapping.values()})
            representative: dict[str, int] = {}
            relationships = []
            for node_id, i in mapping.items():
                shape_key = keys[str(i)]
                if shape_key in representative:
                    relationships.append([int(node_id), representative[shape_key]])
                else:
                    representative[shape_key] = int(node_id)
                row = native[str(i)]
                original = trace.nodes[int(node_id)].state
                if original is None or len(row["goals"]) != len(original.goals):
                    raise ValueError("Offline replay does not match recorded goal count")
            stats[path.name] = dict(
                states=len(mapping),
                distinct_native_shapes=distinct,
                repeated_native_shapes=len(mapping) - distinct,
                relationships=relationships,
                unresolved_mvar_states=sum(
                    any(g["has_expr_mvar"] for g in native[str(i)]["goals"])
                    for i in mapping.values()
                ),
            )
        record = dict(
            task_id=ident,
            prefixes=prefixes,
            native=native,
            trace_references=refs,
            statistics=stats,
            caveat=(
                "Reduced native full-context sequent shapes only; universes/binder names erased. "
                "Hidden elaboration constraints are not state equivalence. "
                "Unresolved metavariables excluded from shared grouping. "
                "NO merging or cached proof reuse."
            ),
        )
        raw = (json.dumps(record, separators=(",", ":")) + "\n").encode()
        target = destination / f"{ident}.json.gz"
        target.write_bytes(gzip.compress(raw, mtime=0))
        print(ident, len(prefixes), "native prefixes", flush=True)
        return dict(
            task_id=ident,
            file=target.name,
            sha256=digest(target),
            prefixes=len(prefixes),
            statistics=stats,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(work, groups.items()))
    report = dict(
        metadata=metadata(),
        source=(
            str(experiment.relative_to(ROOT))
            if experiment.is_relative_to(ROOT)
            else str(experiment.resolve())
        ),
        inspector_sha256=digest(ROOT / "ProofLab/Inspect.lean"),
        tasks=results,
        purpose=(
            "Offline native diagnostics; excluded from primary timed search "
            "and never used for merging/training"
        ),
    )
    (destination / "index.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
