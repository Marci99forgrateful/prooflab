"""Complete research matrices, independent audit hashes and frozen training boundaries."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any, cast

from prooflab.budget_policy import MODEL_DIR, BudgetModel
from prooflab.lean import ROOT, theorem_source
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.phase7_data import DATA, DIRECTORY, check_freeze, protocol, tasks
from prooflab.phase7_evaluation import EXPERIMENT, check_execution
from prooflab.research_io import read_json


def test_phase7_whole_family_model_boundary_and_intermediate_training() -> None:
    check_freeze()
    check_execution()
    model = BudgetModel().artifact
    root = BudgetModel(MODEL_DIR / "root-trained.json").artifact
    families = read_json(DIRECTORY / "families.json")
    valid = set(protocol()["validation_families"])
    evaluation = {t.id for t in tasks("evaluation")}
    for m in (model, root):
        assert m["evaluation_accessed"] is False
        assert not set(m["training_ids"]) & set(m["validation_ids"])
        assert not set(m["training_ids"]) & evaluation
        assert all(families[i] not in valid for i in m["training_ids"])
        assert all(families[i] in valid for i in m["validation_ids"])
        assert m["collection_sha256"] == digest(DATA / "manifest.json")
    assert not model["root_only_training"] and root["root_only_training"]
    assert read_json(MODEL_DIR / "training-report.json")["training_intermediate_rows"] > 0
    assert read_json(MODEL_DIR / "root-training-report.json")["training_intermediate_rows"] == 0


def test_all_actual_continuations_and_missing_labels_are_preserved() -> None:
    manifest = read_json(DATA / "manifest.json")
    rows = cast(list[dict[str, Any]], read_json(DATA / "rows.json.gz"))
    assert len(rows) == manifest["rows"] == len(manifest["files"])
    assert len(manifest["sources"]) == 64
    grouped = defaultdict(list)
    for row in rows:
        assert digest(DATA / row["trace_file"]) == row["sha256"]
        trace = Trace.model_validate(read_json(DATA / row["trace_file"]))
        assert row["completion"] == (
            1
            if trace.verification.verified
            else 0
            if trace.status == "not_found_within_budget"
            else None
        )
        assert (row["conditional_attempts"] is not None) == (row["completion"] == 1)
        assert trace.metadata["role"] == "development-only matched continuation"
        grouped[(row["task_id"], row["source_state"], row["budget_level"])].append(row)
        if trace.verification.verified:
            assert (
                hashlib.sha256(theorem_source(trace.task, trace.proof).encode()).hexdigest()
                == trace.verification.source_sha256
            )
    assert all(
        {r["mode"] for r in group} == {"symbolic", "hybrid", "typed"} for group in grouped.values()
    )
    assert any(r["completion"] == 0 for r in rows)
    assert any(r["source_state"] > 0 and r["completion"] == 1 for r in rows)


def test_complete_final_matrix_has_no_false_or_unaudited_successes() -> None:
    check_execution()
    summary = read_json(EXPERIMENT / "summary.json")
    expected = {(t.id, a) for t in tasks("evaluation") for a in protocol()["arms"]}
    observed = set()
    counts = defaultdict(int)
    for row in summary["per_run"]:
        trace = Trace.model_validate(read_json(EXPERIMENT / row["file"]))
        key = (trace.task.id, trace.metadata["arm"])
        assert key not in observed
        observed.add(key)
        assert trace.budget.model_dump() == protocol()["evaluation_budget"]
        assert trace.verification.verified == (trace.status == "verified")
        assert row["verified"] == int(trace.verification.verified)
        assert trace.metrics.attempted_candidates <= 600 and trace.metrics.expanded_states <= 80
        assert trace.metadata["execution_freeze_sha256"] == digest(MODEL_DIR / "frozen.json")
        counts[row["arm"]] += row["verified"]
        if trace.verification.verified:
            assert trace.proof and trace.lean_source == theorem_source(trace.task, trace.proof)
            assert (
                hashlib.sha256(trace.lean_source.encode()).hexdigest()
                == trace.verification.source_sha256
            )
            assert [n.tactic for n in trace.nodes if n.on_proof_path and n.tactic] == trace.proof
    assert observed == expected and summary["runs"] == len(expected) == 528
    for arm, count in counts.items():
        assert summary["results"][arm]["verified"] == count
    for comparison in summary["comparisons"].values():
        assert not set(comparison["gains"]) & set(comparison["regressions"])


def test_phase7_web_assets_are_exact_canonical_archives() -> None:
    index = read_json(ROOT / "web/public/phase7/explorer.json")
    assert len(index["tasks"]) == 112
    assert sum(r["role"] == "evaluation" for r in index["manifest"]) == 528
    for row in index["manifest"]:
        source = EXPERIMENT if row["role"] == "evaluation" else DATA
        assert (ROOT / "web/public" / row["url"]).read_bytes() == (
            source / "traces" / row["url"].split("/")[-1]
        ).read_bytes()


def test_selected_model_refits_from_frozen_development_only(tmp_path) -> None:
    import pytest

    from prooflab.phase7_training import fit

    fit(tmp_path)
    original = BudgetModel()
    reproduced = BudgetModel(tmp_path / "selected.json")
    rows = cast(list[dict[str, Any]], read_json(DATA / "rows.json.gz"))
    for row in rows[::41]:
        left = original.predictions(row["features"])
        right = reproduced.predictions(row["features"])
        for mode in left:
            assert left[mode] == pytest.approx(right[mode], abs=1e-8, rel=1e-8)
    assert original.artifact["training_ids"] == reproduced.artifact["training_ids"]
    assert original.artifact["conservative_margin"] == reproduced.artifact["conservative_margin"]
