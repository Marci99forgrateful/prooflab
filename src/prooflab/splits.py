"""Native-expression split auditing with alpha/binder-permutation invariance.

The exact graph isomorphism check is stronger than name or text filtering. It
does not decide arbitrary logical equivalence, a generally undecidable problem.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

import networkx as nx  # type: ignore[import-untyped]

from prooflab.dataset import load_tasks
from prooflab.lean import ROOT, lake_command, lean_environment
from prooflab.models import Task

PHASE2 = ROOT / "benchmarks/phase2"
MARKER = "PROOFLAB_STRUCTURE:"


def read_evaluation() -> list[Task]:
    return [Task.model_validate(t) for t in json.loads((PHASE2 / "evaluation.json").read_text())]


def expression_graph(tree: list[Any]) -> Any:
    graph = nx.DiGraph()

    def node(kind: str) -> int:
        ident = len(graph)
        graph.add_node(ident, kind=kind)
        return ident

    def edge(parent: int, child: int, role: str) -> None:
        graph.add_edge(parent, child, role=role)

    def visit(term: list[Any], scope: list[int]) -> int:
        kind = str(term[0])
        if kind.startswith("UNEXPECTED"):
            raise ValueError("Unresolved expression in split audit")
        if kind == "var":
            ref = node("reference")
            edge(ref, scope[-1 - int(term[1])], "binding")
            return ref
        if kind == "forall":
            block = node("forall_block")
            local = list(scope)
            body = term
            while body[0] == "forall":
                binder = node("binder")
                edge(binder, visit(body[1], local), "type")
                edge(block, binder, "binder")
                local.append(binder)
                body = body[2]
            edge(block, visit(body, local), "body")
            return block
        if kind == "lambda":
            binder = node("lambda_binder")
            edge(binder, visit(term[1], scope), "type")
            edge(binder, visit(term[2], [*scope, binder]), "body")
            return binder
        if kind in ("const", "natural", "string"):
            return node(kind + ":" + str(term[1]))
        if kind == "sort":
            return node("sort")
        result = node(kind + (":" + str(term[1]) + ":" + str(term[2]) if kind == "proj" else ""))
        children = term[3:] if kind == "proj" else term[1:]
        for index, child in enumerate(children):
            if not isinstance(child, list):
                raise ValueError("Invalid expression tree")
            edge(result, visit(child, scope), str(index))
        return result

    root = node("statement")
    edge(root, visit(tree, []), "type")
    return graph


def graph_hash(tree: list[Any]) -> str:
    return cast(
        str,
        nx.weisfeiler_lehman_graph_hash(
            expression_graph(tree),
            node_attr="kind",
            edge_attr="role",
            iterations=4,
        ),
    )


def equivalent(left: list[Any], right: list[Any]) -> bool:
    return bool(
        nx.is_isomorphic(
            expression_graph(left),
            expression_graph(right),
            node_match=nx.algorithms.isomorphism.categorical_node_match("kind", None),
            edge_match=nx.algorithms.isomorphism.categorical_edge_match("role", None),
        )
    )


def native_structures(tasks: list[Task]) -> dict[str, list[Any]]:
    with tempfile.TemporaryDirectory(prefix="prooflab-splits-") as directory:
        path = Path(directory) / "Structures.lean"
        path.write_text(
            "import ProofLab.Structure\nset_option maxHeartbeats 2000000\n"
            + "\n".join(
                f"#prooflab_structure {json.dumps(t.id)} : (∀ {t.binders}, {t.target})"
                for t in tasks
            )
        )
        result = subprocess.run(
            [*lake_command(), str(path)],
            cwd=ROOT,
            env=lean_environment(),
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode:
            raise RuntimeError(result.stdout[-15000:] + result.stderr[-2000:])
        structures = {}
        for line in result.stdout.splitlines():
            if MARKER in line:
                entry = json.loads(line.split(MARKER, 1)[1])
                structures[entry["id"]] = entry["tree"]
        if set(structures) != {t.id for t in tasks}:
            raise ValueError("Native split audit did not elaborate every selected statement")
        return structures


def audit_splits(*, write: bool = False) -> dict[str, Any]:
    phase1 = load_tasks()
    evaluation = read_evaluation()
    protocol = json.loads((PHASE2 / "protocol.json").read_text())
    if len(evaluation) != 24 or len({t.id for t in [*phase1, *evaluation]}) != len(phase1) + 24:
        raise ValueError("Missing evaluation task or duplicate IDs")
    all_tasks = [*phase1, *evaluation]
    trees = native_structures(all_tasks)
    hashes = {ident: graph_hash(tree) for ident, tree in trees.items()}
    duplicates = []
    for index, task in enumerate(evaluation):
        for other in [*phase1, *evaluation[:index]]:
            if hashes[task.id] == hashes[other.id] and equivalent(trees[task.id], trees[other.id]):
                duplicates.append([task.id, other.id])
    if duplicates:
        raise ValueError(f"Structurally equivalent evaluation statements: {duplicates}")
    dev = [t.id for t in phase1 if t.split == "development"]
    families = protocol["evaluation_families"]
    if set(families) != {t.id for t in evaluation}:
        raise ValueError("Incomplete evaluation family registry")
    result = {
        "schema_version": 1,
        "evaluation_sha256": hashlib.sha256((PHASE2 / "evaluation.json").read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((PHASE2 / "protocol.json").read_bytes()).hexdigest(),
        "permitted_development_ids": dev,
        "selection_train_ids": [t.id for t in phase1 if t.id in dev and t.domain != "order"],
        "selection_validation_ids": [t.id for t in phase1 if t.id in dev and t.domain == "order"],
        "evaluation_ids": [t.id for t in evaluation],
        "evaluation_family_count": len(set(families.values())),
        "normalization": "Lean reducible reduction; erased universe levels/binder names; "
        "exact typed expression-graph isomorphism permitting forall-binder permutation",
        "graph_hashes": hashes,
        "expression_trees": trees,
        "duplicate_pairs": duplicates,
        "limits": "No decision procedure for arbitrary theorem equivalence or proof-primitive "
        "overlap. Evaluation families are new; shared logical primitives are expected.",
        "networkx_version": nx.__version__,
        "base_revision": "833ed8063ead78afccbf4952a3cd894e39470f5c",
        "protected_code": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in ("src/prooflab/candidates.py", "src/prooflab/lean.py", "ProofLab/Bridge.lean")
        },
    }
    if write:
        (PHASE2 / "frozen.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def check_freeze() -> dict[str, Any]:
    frozen: dict[str, Any] = json.loads((PHASE2 / "frozen.json").read_text())
    for name, key in (
        ("evaluation.json", "evaluation_sha256"),
        ("protocol.json", "protocol_sha256"),
    ):
        if hashlib.sha256((PHASE2 / name).read_bytes()).hexdigest() != frozen[key]:
            raise ValueError("Frozen evaluation/protocol changed; do not train or score")
    for name, digest in frozen["protected_code"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Candidate generator or trusted Lean layer changed after freeze")
    return frozen
