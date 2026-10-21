"""Native construction, policy isolation and scientifically honest labels."""

from __future__ import annotations

import copy
import math
import random

import pytest

from prooflab.adaptive import CanonicalOutcomeRanking, HybridProvider, candidate_features
from prooflab.adaptive_fit import boosted_pairs, pair_loss
from prooflab.adaptive_model import predict
from prooflab.adaptive_native import AdaptiveSession
from prooflab.adaptive_training import preferences
from prooflab.lean import verify
from prooflab.models import Candidate, ProofState
from prooflab.phase6_data import check_freeze, read_tasks


def test_phase6_curriculum_and_historical_boundaries() -> None:
    f = check_freeze()
    assert len(f["training_ids"]) == 120 and len(f["validation_ids"]) == 40
    assert not set(f["training_ids"]) & set(f["validation_ids"])
    assert len(read_tasks()) == 48 and len(read_tasks("development")) == 160
    assert not set(f["evaluation_ids"]) & set(f["development_ids"])
    assert f["duplicate_pairs"] == [] and len(f["prior_evidence"]) > 3000


@pytest.mark.integration
def test_curried_callable_closure_and_fresh_independent_audit() -> None:
    task = next(t for t in read_tasks("development") if t.id == "p6_dev_curried_construction_02")
    with AdaptiveSession(task) as lean:
        query = lean.retrieve(0, [])
        row = next(r for r in query["rows"] if r.get("term") == "f a b")
        assert row["compatible"] and row["construction_depth"] == 2
        assert "application(f a, b)" in row["construction"] and row["type"] == "γ"
        assert query["state"] == lean.initial.model_dump()["goals"]
        assert query["term_constructions"] <= 128
        first = lean.step(0, row["tactic"], 2)
        last = lean.step(first["state_id"], "apply h", 2)
        assert last["status"] == "accepted" and last["goals"] == []
    assert verify(task, ["exists (f a b)", "apply h"]).verified


@pytest.mark.integration
def test_dependent_application_and_nested_typed_product() -> None:
    tasks = read_tasks("development")
    for ident, term in [
        ("p6_dev_product_graphs_01", "(a, b, c)"),
        ("p6_dev_dependent_contexts_03", "f a b"),
    ]:
        task = next(t for t in tasks if t.id == ident)
        with AdaptiveSession(task) as lean:
            record = lean.retrieve(0, [])
            row = next(r for r in record["rows"] if r.get("term") == term)
            assert row["compatible"] and row["construction_depth"] <= 3
            assert record["term_constructions"] <= 128
            msg = lean.step(0, row["tactic"], 2)
            assert msg["status"] == "accepted"


@pytest.mark.integration
def test_selection_cap_baseline_normalizer_and_unknown_features() -> None:
    task = next(t for t in read_tasks("development") if t.id == "p6_dev_group_equations_05")
    with AdaptiveSession(task) as lean:
        chosen, q = HybridProvider().generate(lean, lean.initial, 24, frozenset(), 2)
        assert len(chosen) <= 24 and len({c.tactic for c in chosen}) == len(chosen)
        assert "simp_all" in q["selected"] and "simp_all" not in q["displaced"]
        assert q["recognized_structures"] == ["Group"]
        assert q["allocation"]["baseline"] + q["allocation"]["novelty"] == len(chosen)
        protected = {r["candidate"]["tactic"] for r in q["pool"] if r["protected"]}
        assert protected <= set(q["selected"])
        row = next(r for r in q["pool"] if r["candidate"]["tactic"] == "simp_all")
        f = candidate_features(lean.initial, Candidate.model_validate(row["candidate"]), row)
        assert f["compatibility_observed"] == 0 and row.get("compatible") is None
        assert not any(task.id in n or "state_id" in n for n in f)


def test_canonical_execution_order_ignores_retrieval_input_order() -> None:
    state = ProofState(state_id=0, goals=[])
    candidates = [
        Candidate(tactic=t, category="goal", reason="ranking interface test")
        for t in ("constructor", "assumption", "rfl")
    ]
    ranker = CanonicalOutcomeRanking()
    expected = [c.tactic for c in ranker.rank_candidates(state, candidates)]
    for seed in range(8):
        shuffled = candidates.copy()
        random.Random(seed).shuffle(shuffled)
        assert [c.tactic for c in ranker.rank_candidates(state, shuffled)] == expected


def test_finite_failure_and_unknown_are_not_usefulness_negatives() -> None:
    a = dict(
        candidate=dict(tactic="assumption"),
        features={"x": 1.0},
        status="accepted",
        label="verified_path",
        continuation=None,
    )
    b = dict(
        candidate=dict(tactic="rfl"),
        features={"x": -1.0},
        status="invalid_candidate",
        label="rejected_application",
        continuation=None,
    )
    c = dict(
        candidate=dict(tactic="apply h"),
        features={"x": 0.5},
        status="accepted",
        label="accepted_censored",
        continuation=dict(status="censored"),
    )
    d = copy.deepcopy(b)
    d["label"] = "resource_censored"
    rows = [dict(task_id="dev_only", states=[dict(depth=0, observations=[a, b, c, d])])]
    p = preferences(rows)
    assert len(p) == 1 and p[0]["negative"] == "rfl"
    assert (
        preferences([dict(task_id="dev_only", states=[dict(depth=0, observations=[a, c, d])])])
        == []
    )
    assert len(preferences(rows, True)) == 2  # Acceptance objective labels c positive.


def test_boosted_pairwise_model_is_fitted_and_seed_reproducible() -> None:
    pairs = []
    for sign in (-1.0, 1.0):
        for _ in range(15):
            pairs.append(
                dict(
                    positive_features={"context": sign, "choice": sign},
                    negative_features={"context": sign, "choice": -sign},
                    weight=1.0,
                )
            )
    model = boosted_pairs(pairs, 2, 24, 0, min_leaf=1)
    assert model == boosted_pairs(pairs, 2, 24, 0, min_leaf=1)
    assert pair_loss(pairs, model) < math.log(2)
    assert predict(model, {"context": 1.0, "choice": 1.0}) > predict(
        model, {"context": 1.0, "choice": -1.0}
    )
    assert predict(model, {"context": -1.0, "choice": -1.0}) > predict(
        model, {"context": -1.0, "choice": 1.0}
    )


def test_compressed_collection_save_preserves_requested_path(tmp_path) -> None:
    from prooflab.adaptive_training import save
    from prooflab.research_io import read_json

    path = tmp_path / "actual.json.gz"
    save(path, {"genuine": "data"})
    assert path.exists() and not (tmp_path / "actual.json.json.gz").exists()
    assert read_json(path) == {"genuine": "data"}
