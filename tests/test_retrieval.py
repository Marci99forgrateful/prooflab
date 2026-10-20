"""Native proposal isolation, bounded expressiveness and honest learning labels."""

from __future__ import annotations

import copy
import json

import pytest

from prooflab.candidates import generate_candidates
from prooflab.dataset import get_task
from prooflab.features import extract_features
from prooflab.lean import ROOT, verify
from prooflab.models import Candidate
from prooflab.native_retrieval import RetrievalSession, declarations
from prooflab.phase5_data import check_freeze, read_tasks
from prooflab.retrieval import TypedProvider, features
from prooflab.retrieval_training import fit, pairs


def test_phase5_frozen_boundary() -> None:
    frozen = check_freeze()
    assert len(read_tasks()) == 40
    assert (
        len(set(json.loads((ROOT / "benchmarks/phase5/families.json").read_text()).values())) == 10
    )
    assert len(frozen["expression_trees"]) == 212
    assert frozen["duplicate_pairs"] == []
    assert len(declarations()) == 116
    assert len(frozen["permitted_development_ids"]) == 48
    assert not {t.id for t in read_tasks()} & set(frozen["permitted_development_ids"])


@pytest.mark.integration
def test_native_queries_restore_state_and_compatible_is_not_success() -> None:
    task = get_task("imp_chain")
    with RetrievalSession(task) as lean:
        before = lean.initial.model_dump()
        first = lean.retrieve(0, ["And.left", "And.intro", "le_trans"])
        second = lean.retrieve(0, ["And.left", "And.intro", "le_trans"])
        assert first["state"] == second["state"] == before["goals"]
        row = next(r for r in first["rows"] if r["tactic"] == "apply And.left")
        assert row["compatible"] and row["premises"]
        # Read-only generic compatibility did not discharge a goal or corrupt it.
        msg = lean.step(0, "apply hqr", 2)
        assert msg["status"] == "accepted"
        assert msg["goals"][0]["target"]["text"] == "Q"
    assert lean.resource_usage["cpu_s"] > 0
    assert lean.resource_usage["peak_rss_kib"] > 0
    assert lean.resource_usage["process_count"] >= 2


@pytest.mark.integration
def test_typed_witness_transport_and_independent_audit() -> None:
    task = get_task("p4_witness_transport")
    with RetrievalSession(task) as lean:
        candidates, record = TypedProvider().generate(lean, lean.initial, 24, frozenset(), 2)
        assert "exists (f a)" in [c.tactic for c in candidates]
        row = next(r for r in record["native"]["rows"] if r.get("term") == "f a")
        assert row["compatible"] and row["construction_depth"] == 1
        assert row["type"] == "β"
        current = 0
        for tactic in ["exists (f a)", "apply h", "assumption"]:
            msg = lean.step(current, tactic, 2)
            assert msg["status"] == "accepted"
            current = msg["state_id"]
        assert msg["goals"] == []
    assert verify(task, ["exists (f a)", "apply h", "assumption"]).verified


@pytest.mark.integration
def test_product_construction_and_group_instance_gate() -> None:
    product = next(t for t in read_tasks("pilot") if t.id == "p5_pilot_pair")
    with RetrievalSession(product) as lean:
        data = lean.retrieve(0, ["And.intro"])
        assert any(r.get("term") == "(a, b)" and r["compatible"] for r in data["rows"])
        assert data["term_constructions"] <= 48
    with RetrievalSession(get_task("p4_inverse_right")) as lean:
        data = lean.retrieve(0, ["mul_comm", "mul_assoc", "mul_inv_cancel_right"])
        comm = next(r for r in data["rows"] if r.get("tactic") == "apply mul_comm")
        assert not comm["compatible"]
        assert "Group" in data["classes"]


@pytest.mark.integration
def test_candidate_cap_original_protection_and_ranking_vocabulary() -> None:
    task = get_task("p4_cubic_pair")
    with RetrievalSession(task) as lean:
        original = generate_candidates(lean.initial, 24)
        for mode in ("broad", "type_filtered", "typed", "no_witness", "no_normalize"):
            selected, record = TypedProvider(mode).generate(lean, lean.initial, 24, frozenset(), 2)
            assert len(selected) <= 24
            assert len({c.tactic for c in selected}) == len(selected)
            protected = [r["candidate"]["tactic"] for r in record["pool"] if r["protected"]]
            assert set(protected) <= set(record["selected"])
            assert set(record["displaced"]) == {c.tactic for c in original} - set(
                record["selected"]
            )
        c = Candidate(
            tactic="apply And.left",
            category="lemma",
            lemma="And.left",
            reason="test new vocabulary",
        )
        # Frozen model vocabulary safely ignores a new name, retaining structure.
        assert "op:lemma_apply" in extract_features(lean.initial, c)
        f = features(lean.initial, c, {"compatible": True, "premises": ["P"], "family": "lemma"})
        assert f["retrieval:compatible"] == 1
        assert not any("p4_cubic" in n or "state_id" in n for n in f)


def test_censored_and_unexplored_are_never_negative_and_cpu_fit_deterministic() -> None:
    source = dict(
        candidate={"tactic": "assumption"},
        label="verified_path",
        status="accepted",
        features={"x": 1},
        continuation=None,
    )
    invalid = dict(
        candidate={"tactic": "rfl"},
        label="rejected_application",
        status="invalid_candidate",
        features={"x": -1},
        continuation=None,
    )
    censored = dict(
        candidate={"tactic": "apply h"},
        label="accepted_censored",
        status="accepted",
        features={"x": 3},
        continuation={"status": "censored"},
    )
    unknown = copy.deepcopy(censored)
    unknown["label"] = "accepted_unknown"
    unknown["candidate"] = {"tactic": "apply k"}
    evidence = [
        dict(
            task_id="allowed_dev",
            states=[dict(depth=0, observations=[source, invalid, censored, unknown])],
        )
    ]
    preferences = pairs(evidence)
    assert len(preferences) == 1
    assert preferences[0]["positive"] == "assumption" and preferences[0]["negative"] == "rfl"
    a = fit(preferences, 0.1, 20, 0.1)
    assert a == fit(preferences, 0.1, 20, 0.1) and a["x"] > 0
    assert (
        pairs([dict(task_id="dev", states=[dict(depth=0, observations=[censored, unknown])])]) == []
    )
