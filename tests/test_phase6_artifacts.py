"""Frozen scientific evidence: no test-data fitting, false successes or missing runs."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from prooflab.adaptive_model import MODELS, AdaptiveModel
from prooflab.lean import ROOT, theorem_source
from prooflab.models import Trace
from prooflab.phase6_data import check_freeze, read_tasks
from prooflab.phase6_evaluation import EXPERIMENT, check_execution, read_protocol
from prooflab.research_io import read_json, trace_paths


def test_phase6_model_boundary_and_distinct_linear_controller() -> None:
    frozen = check_freeze()
    check_execution()
    learned = AdaptiveModel().artifact
    linear = AdaptiveModel(variant="linear").artifact
    assert set(learned["training_ids"]) == set(frozen["training_ids"])
    assert not set(learned["training_ids"]) & set(frozen["validation_ids"])
    assert set(learned["selector_training_ids"]) == set(frozen["development_ids"])
    assert not set(learned["permitted_development_ids"]) & set(frozen["evaluation_ids"])
    assert learned["relevance"] == linear["relevance"]
    assert "trees" in learned["selector"] and "weights" in linear["selector"]
    assert learned["evaluation_accessed"] is False and learned["selector_ready"]
    for seed in (1, 2):
        model = AdaptiveModel(MODELS / f"controller-seed{seed}.json").artifact
        assert model["relevance"] == learned["relevance"]
        assert model["selector"]["seed"] == seed
        assert model["selector_collection_sha256"] == learned["selector_collection_sha256"]


def test_complete_phase6_matrix_all_successes_independently_audited() -> None:
    protocol = read_protocol()
    expected = {
        (t.id, a["id"], str(r))
        for t in read_tasks()
        for a in protocol["arms"]
        for r in range(a["repetitions"])
    }
    paths = trace_paths(EXPERIMENT / "traces")
    assert len(paths) == len(expected) == 1440
    arms = {a["id"]: a for a in protocol["arms"]}
    observed = set()
    verified = 0
    provenance = read_json(EXPERIMENT / "provenance.json")
    stored = read_json(EXPERIMENT / "trace-storage.json")["traces"]
    for path in paths:
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == stored[path.name.removesuffix(".gz")]["gzip_sha256"]
        )
        t = Trace.model_validate(read_json(path))
        key = (t.task.id, t.metadata["arm"], t.metadata["repeat"])
        assert t.budget.model_dump() == protocol["budgets"][arms[t.metadata["arm"]]["budget_level"]]
        assert key not in observed
        observed.add(key)
        assert t.metadata["code_commit"] == provenance["code_commit"]
        assert (t.status == "verified") == t.verification.verified
        assert (
            t.metadata["execution_freeze_sha256"]
            == hashlib.sha256((MODELS / "frozen.json").read_bytes()).hexdigest()
        )
        assert float(t.metadata["runner_wall_s"]) >= t.metrics.elapsed_s >= 0
        assert t.metrics.lean_execution_s + 1e-6 >= t.metrics.retrieval_s
        events = json.loads(t.metadata["native_query_events"])
        assert len(events) == t.metrics.retrieval_queries
        assert sum(e["status"] != "completed" for e in events) == int(
            t.metadata["failed_retrieval_queries"]
        )
        assert all(len(q["selected"]) <= 24 for q in t.retrievals)
        if t.verification.verified:
            verified += 1
            assert t.proof and t.metrics.proof_length == len(t.proof)
            assert (
                hashlib.sha256(theorem_source(t.task, t.proof).encode()).hexdigest()
                == t.verification.source_sha256
            )
            assert [n.tactic for n in t.nodes if n.on_proof_path and n.tactic] == t.proof
            assert any(n.status == "solved" and n.on_proof_path for n in t.nodes)
    assert observed == expected
    summary = read_json(EXPERIMENT / "summary.json")
    assert (
        summary["runs"] == 1440
        and sum(r["verified"] for r in summary["results"].values()) == verified
    )


def test_phase6_csv_summary_and_budget_provenance_agree() -> None:
    with (EXPERIMENT / "results.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    summary = read_json(EXPERIMENT / "summary.json")
    protocol = read_protocol()
    assert len(rows) == 1440
    for arm in protocol["arms"]:
        selected = [r for r in rows if r["arm"] == arm["id"]]
        assert len(selected) == arm["repetitions"] * 48
        assert (
            sum(r["status"] == "verified" for r in selected)
            == summary["results"][arm["id"]]["verified"]
        )
    record = read_json(EXPERIMENT / "provenance.json")
    assert record["no_retuning"] and record["workers"] == 2
    assert record["budgets"] == protocol["budgets"]


def test_phase6_export_reuses_only_canonical_execution_archives() -> None:
    index = read_json(ROOT / "web/public/phase6/explorer.json")
    assert len(index["manifest"]) == 1440 and len(index["tasks"]) == 48
    assert len(set(index["families"].values())) == 12
    for item in index["manifest"]:
        source = EXPERIMENT / "traces" / Path(item["url"]).name
        target = ROOT / "web/public" / item["url"]
        assert source.read_bytes() == target.read_bytes()
    assert {"phase4", "learned", "linear", "learned_seed1", "learned_seed2"} <= set(
        index["policy_names"]
    )
    for case in index["examples"]:
        left = next(
            e
            for e in index["manifest"]
            if (e["task_id"], e["arm"], e["repeat"])
            == (case["task_id"], case["left"], case["repeat"])
        )
        right = next(
            e
            for e in index["manifest"]
            if (e["task_id"], e["arm"], e["repeat"])
            == (case["task_id"], case["right"], case["repeat"])
        )
        if "Actual verified regression" in case["title"]:
            assert left["status"] != "verified" and right["status"] == "verified"
        if "Actual verified gain" in case["title"]:
            assert left["status"] == "verified" and right["status"] != "verified"


def test_candidate_coefficients_reproduce_from_training_families_only() -> None:
    import gzip

    from prooflab.retrieval_training import fit

    frozen = check_freeze()
    pairs = json.loads(gzip.decompress((MODELS / "preferences.json.gz").read_bytes()))
    training = [p for p in pairs if p["task_id"] in frozen["training_ids"]]
    report = read_json(MODELS / "training-report.json")
    assert len(training) == report["final_relevance_training_pairs"] == 1473
    weights = fit(training, 0.01, 200, 0.15)
    assert weights == pytest.approx(
        AdaptiveModel().artifact["relevance"]["weights"], rel=1e-12, abs=1e-12
    )
    assert not {p["task_id"] for p in training} & set(frozen["validation_ids"])
