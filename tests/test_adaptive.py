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
from prooflab.models import Candidate, ProofState, Task
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


def test_provisional_ranker_cannot_execute_unfitted_adaptive_selector(tmp_path) -> None:
    import json

    from prooflab.adaptive_model import VERSION, AdaptiveModel

    path = tmp_path / "relevance-only.json"
    path.write_text(
        json.dumps(
            dict(
                feature_version=VERSION,
                evaluation_accessed=False,
                selector_ready=False,
                relevance=dict(weights={"x": 1.0}),
            )
        )
    )
    with pytest.raises(ValueError, match="not finalized"):
        AdaptiveModel(path)
    assert AdaptiveModel(path, allow_provisional=True).candidate_score({"x": 2.0}) == 2


@pytest.mark.integration
def test_forced_development_mode_uses_fitted_relevance_without_future_selector(tmp_path) -> None:
    import json

    from prooflab.adaptive_model import VERSION

    task = next(t for t in read_tasks("development") if t.id == "p6_dev_curried_construction_02")
    path = tmp_path / "provisional.json"
    path.write_text(
        json.dumps(
            dict(
                feature_version=VERSION,
                evaluation_accessed=False,
                selector_ready=False,
                relevance=dict(weights={"retrieval:family:witness": 1.0}),
            )
        )
    )
    with AdaptiveSession(task) as lean:
        _, query = HybridProvider("learned", path, forced_mode="hybrid").generate(
            lean, lean.initial, 24, frozenset(), 2
        )
        assert query["decision"] == "hybrid" and query["predicted_log_costs"] == {}
        assert query["decision_source"] == "forced development counterfactual"
        witness = next(r for r in query["pool"] if r.get("term") == "f a b")
        assert witness["learned_score"] == 1 and witness["selected"]


@pytest.mark.integration
def test_shared_candidate_schema_and_relative_order_are_mode_independent(tmp_path) -> None:
    import json

    from prooflab.adaptive_model import VERSION

    task = next(t for t in read_tasks("development") if t.id == "p6_dev_lattice_maps_01")
    path = tmp_path / "provisional.json"
    path.write_text(
        json.dumps(
            dict(
                feature_version=VERSION,
                evaluation_accessed=False,
                selector_ready=False,
                relevance=dict(weights={"x": 1.0}),
            )
        )
    )
    with AdaptiveSession(task) as lean:
        hybrid, _ = HybridProvider("learned", path, forced_mode="hybrid").generate(
            lean, lean.initial, 24, frozenset(), 2
        )
        typed, _ = HybridProvider("learned", path, forced_mode="typed").generate(
            lean, lean.initial, 24, frozenset(), 2
        )
        a, b = {c.tactic: c for c in hybrid}, {c.tactic: c for c in typed}
        common = a.keys() & b.keys()
        assert len(common) > 4
        assert all(a[t].model_dump() == b[t].model_dump() for t in common)
        policy = CanonicalOutcomeRanking()
        left = [
            c.tactic for c in policy.rank_candidates(lean.initial, hybrid) if c.tactic in common
        ]
        right = [
            c.tactic for c in policy.rank_candidates(lean.initial, typed) if c.tactic in common
        ]
        assert left == right


@pytest.mark.integration
@pytest.mark.parametrize("kind", ["image", "preimage"])
def test_native_set_witness_constructor_has_real_inferred_type_and_audit(kind) -> None:
    task = Task(
        id=f"p6_api_set_{kind}",
        title="Set constructor API validation",
        domain="sets",
        difficulty="challenge",
        split="development",
        binders="(α β : Type) (f : α → β) " + ("(A : Set α)" if kind == "image" else "(B : Set β)"),
        target=(
            "∃ S : Set β, ∀ y, y ∈ S ↔ ∃ x, x ∈ A ∧ f x = y"
            if kind == "image"
            else "∃ S : Set α, ∀ x, x ∈ S ↔ f x ∈ B"
        ),
        display="native Set witness",
        description=(
            "Feature API validation only, excluded from frozen training and final-test datasets"
        ),
    )
    with AdaptiveSession(task) as lean:
        query = lean.retrieve(0, [])
        row = next(r for r in query["rows"] if f"Set.{kind}" in r.get("construction", ""))
        assert row["compatible"] and row["construction_depth"] <= 3
        assert row["type"] == ("Set β" if kind == "image" else "Set α")
        assert query["term_constructions"] <= 128
        proof = [row["tactic"], "intro x", "rfl"]
        parent = 0
        for tactic in proof:
            message = lean.step(parent, tactic, 2)
            assert message["status"] == "accepted"
            parent = message["state_id"]
        assert not message["goals"]
    assert verify(task, proof).verified


@pytest.mark.integration
def test_staged_policy_counts_nonexistential_expansions_and_keeps_one_budget() -> None:
    task = Task(
        id="p6_api_stage_probe",
        title="Staged query validation",
        domain="algebra",
        difficulty="challenge",
        split="development",
        binders="(G : Type) [Group G] (a : G)",
        target="∃ z, z = a ∧ z*a⁻¹=1",
        display="staged native goal",
        description="API-only feature check, not training or final evaluation",
    )
    provider = HybridProvider("staged")
    with AdaptiveSession(task) as lean:
        state = lean.initial
        _, q = provider.generate(lean, state, 24, frozenset(), 2)
        assert q["decision"] == "hybrid" and q["nonexistential_stage"] == 0
        for tactic, expected in [("exists a", 1), ("constructor", 2), ("rfl", 3)]:
            msg = lean.step(state.state_id, tactic, 2)
            assert msg["status"] == "accepted"
            state = ProofState(state_id=msg["state_id"], goals=msg["goals"])
            _, q = provider.generate(lean, state, 24, frozenset(), 2)
            assert q["nonexistential_stage"] == expected
            assert q["decision"] == ("symbolic" if expected <= 2 else "hybrid")


@pytest.mark.integration
def test_fixed_quota_ablation_preserves_the_same_context_gate() -> None:
    task = next(t for t in read_tasks("development") if t.id == "p6_dev_ring_expansion_02")
    with AdaptiveSession(task) as lean:
        det, a = HybridProvider("deterministic").generate(lean, lean.initial, 24, frozenset(), 2)
        fixed, b = HybridProvider("fixed").generate(lean, lean.initial, 24, frozenset(), 2)
        assert a["decision"] == b["decision"] == "symbolic"
        assert [c.model_dump() for c in det] == [c.model_dump() for c in fixed]
        assert "native" not in a and "native" not in b
