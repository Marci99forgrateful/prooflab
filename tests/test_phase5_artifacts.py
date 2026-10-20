"""Evidence integrity and frozen factorial boundaries, never synthetic search results."""

from __future__ import annotations

import hashlib
import json

from prooflab.lean import ROOT, theorem_source
from prooflab.models import Trace
from prooflab.phase5_data import DIRECTORY, check_freeze, read_tasks
from prooflab.phase5_evaluation import EXPERIMENT, check_execution
from prooflab.research_io import read_json, trace_paths
from prooflab.retrieval import RetrievalRanker
from prooflab.retrieval_training import DATA, pairs


def test_retrieval_supervision_uses_only_development_and_actual_outcomes() -> None:
    frozen = check_freeze()
    rows = [read_json(p) for p in trace_paths(DATA / "traces")]
    assert {r["task_id"] for r in rows} == set(frozen["permitted_development_ids"])
    assert sum(len(r["states"]) for r in rows) == 99
    stored = json.loads((ROOT / "models/phase5/preferences.json").read_text())
    assert pairs(rows) == stored
    assert len(stored) == 555
    for r in rows:
        if not r["states"]:
            continue
        assert r["source_audit"]["verified"]
        for state in r["states"]:
            outcomes = {o["candidate"]["tactic"]: o for o in state["observations"]}
            for p in (
                p for p in stored if p["task_id"] == r["task_id"] and p["depth"] == state["depth"]
            ):
                positive, negative = outcomes[p["positive"]], outcomes[p["negative"]]
                assert positive["label"] in ("verified_path", "verified_continuation")
                if p["kind"] == "verified_over_rejected_application":
                    assert negative["status"] == "invalid_candidate"
                else:
                    a, b = positive["continuation"], negative["continuation"]
                    assert a["verification"]["verified"] and b["verification"]["verified"]
                    assert (
                        a["metrics"]["attempted_candidates"] < b["metrics"]["attempted_candidates"]
                    )
            assert not any(
                word in (o.get("error") or "").lower()
                for o in state["observations"]
                for word in ("heartbeat", "timeout", "recursion", "memory")
            )


def test_phase5_execution_model_and_index_are_frozen() -> None:
    frozen = check_execution()
    ranker = RetrievalRanker()
    assert ranker.sha256 == frozen["model_sha256"]
    assert ranker.artifact["l2"] == 0.01
    assert len(ranker.weights) == 130
    assert not ranker.artifact["evaluation_accessed"]
    assert (
        ranker.artifact["index_sha256"]
        == hashlib.sha256((DIRECTORY / "declarations.json").read_bytes()).hexdigest()
    )


def test_complete_factorial_trace_matrix_and_real_audits() -> None:
    protocol = read_json(DIRECTORY / "protocol.json")
    tasks = {t.id for t in read_tasks()}
    algorithms = {a["id"]: a["algorithm"] for a in protocol["arms"]}
    expected = {
        (i, a["id"], str(r))
        for i in tasks
        for a in protocol["arms"]
        for r in range(a["repetitions"])
    }
    paths = trace_paths(EXPERIMENT / "traces")
    assert len(paths) == len(expected) == 1120
    actual = set()
    verified = 0
    for path in paths:
        t = Trace.model_validate(read_json(path))
        actual.add((t.task.id, t.metadata["arm"], t.metadata["repeat"]))
        assert t.algorithm == algorithms[t.metadata["arm"]]
        assert t.budget.model_dump() == protocol["budget"]
        assert len(t.nodes) - 1 == t.metrics.attempted_candidates
        assert t.metrics.retrieval_s <= t.metrics.lean_execution_s + 1e-9
        assert all(len(q["selected"]) <= 24 for q in t.retrievals)
        for q in t.retrievals:
            if "native" in q:
                assert q["native"]["declaration_probes"] <= 128
                assert q["native"]["rewrite_probes"] <= 16
                assert q["native"]["term_constructions"] <= 48
        if t.status == "verified":
            verified += 1
            assert t.verification.verified and t.proof
            assert (
                t.verification.source_sha256
                == hashlib.sha256(theorem_source(t.task, t.proof).encode()).hexdigest()
            )
            assert set(t.verification.axioms) <= {"propext", "Classical.choice", "Quot.sound"}
            assert t.nodes[-1].status == "solved"
        if t.metadata["generator_mode"] in ("typed", "learned", "no_witness", "no_normalize"):
            assert not any(n.tactic in ("aesop", "grind", "simp_all") for n in t.nodes)
    assert actual == expected
    summary = read_json(EXPERIMENT / "summary.json")
    assert sum(r["verified"] for r in summary["results"].values()) == verified
    assert len(summary["per_theorem"]) == 40 * 16
    assert summary["availability"]["records"]


def test_canonical_bootstrap_is_invariant_to_family_input_order() -> None:
    import copy
    import runpy

    canonical = runpy.run_path(str(ROOT / "scripts/canonicalize_phase5_statistics.py"))["canonical"]

    first = {
        "comparisons": {
            "a minus b": {
                "success": {"differences": {"task_a": 0.0, "task_b": 1.0, "task_c": -0.5}},
                "all_runs": {},
                "common_verified": {},
            }
        }
    }
    second = copy.deepcopy(first)
    second["comparisons"]["a minus b"]["success"]["differences"] = {
        "task_c": -0.5,
        "task_b": 1.0,
        "task_a": 0.0,
    }
    families = {"task_a": "z_family", "task_b": "a_family", "task_c": "m_family"}
    config = {"bootstrap_seed": 2718, "bootstrap_samples": 200}
    a = canonical(first, families, config)["comparisons"]["a minus b"]["success"]
    b = canonical(second, families, config)["comparisons"]["a minus b"]["success"]
    assert a["ci95_family"] == b["ci95_family"]
    assert a["family_balanced_mean"] == b["family_balanced_mean"]
