from __future__ import annotations

import json
from pathlib import Path

import pytest

from prooflab.features import extract_features
from prooflab.learning import LearnedRanking, ModelArtifact, save_model
from prooflab.models import Candidate, Expression, Goal, Hypothesis, ProofState
from prooflab.training import fit, pair_loss, training_pairs


def sample_state() -> ProofState:
    return ProofState(
        state_id=12,
        goals=[
            Goal(
                id="g",
                target=Expression(text="Q", head="[anonymous]", forall=False),
                hypotheses=[
                    Hypothesis(
                        name="f", id="f1", type=Expression(text="P → Q", head="", forall=True)
                    ),
                    Hypothesis(name="p", id="f2", type=Expression(text="P", head="", forall=False)),
                ],
            )
        ],
    )


def test_cpu_fit_learns_from_pairwise_data_and_is_deterministic() -> None:
    # Synthetic optimizer unit test only; these records are never training artifacts.
    pairs = [{"op:assumption": 1.0, "op:rfl": -1.0}] * 12
    weights = fit(pairs, 0.01, epochs=100)
    assert pair_loss(weights, pairs) < pair_loss({}, pairs)
    assert weights["op:assumption"] > 0 > weights["op:rfl"]
    assert weights == fit(pairs, 0.01, epochs=100)


def test_model_scores_reorder_without_altering_candidates(tmp_path: Path) -> None:
    path = tmp_path / "model.json"
    save_model(path, ModelArtifact(weights={"op:rfl": 1.0, "op:assumption": -1.0}))
    model = LearnedRanking(path)
    steps = [
        Candidate(tactic="assumption", category="goal", reason="test"),
        Candidate(tactic="rfl", category="goal", reason="test"),
    ]
    ranked = model.rank_candidates(sample_state(), steps)
    assert ranked == list(reversed(steps))
    assert sorted(s.model_dump_json() for s in ranked) == sorted(s.model_dump_json() for s in steps)
    assert len(model.model_hash) == 64


def test_features_have_no_theorem_identifier_or_dataset_access() -> None:
    state = sample_state()
    candidate = Candidate(tactic="apply f", category="hypothesis", reason="test")
    before = extract_features(state, candidate)
    state.state_id = 9999
    state.goals[0].id = "a_hidden_task_id"
    state.goals[0].hypotheses[0].id = "different_internal_lean_identity"
    assert before == extract_features(state, candidate)
    assert before["hyp_conclusion_match"] == 1
    assert before["hyp_premise_present"] == 1
    assert not any("task" in key or "9999" in key for key in before)


def test_valid_unlabeled_alternatives_are_never_negative_evidence() -> None:
    state = sample_state()
    row = {
        "task_id": "imp_chain",
        "split": "development",
        "state": state.model_dump(),
        "fresh_proof_audit": {"verified": True},
        "observations": [
            {
                "candidate": Candidate(
                    tactic="apply f", category="hypothesis", reason="test"
                ).model_dump(),
                "label": "verified_path_preferred",
                "status": "accepted",
            },
            {
                "candidate": Candidate(
                    tactic="assumption", category="goal", reason="test"
                ).model_dump(),
                "label": "valid_alternative_unlabeled",
                "status": "accepted",
            },
        ],
    }
    assert training_pairs([row]) == []
    row["observations"][1]["label"] = "observed_invalid"
    with pytest.raises(ValueError, match="mislabeled"):
        training_pairs([row])
    row["task_id"] = "p2_witness_single"
    with pytest.raises(ValueError, match="Forbidden"):
        training_pairs([row])


def test_untrusted_model_formats_and_nonfinite_weights_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    for payload in (
        {"weights": {"unknown": 1}},
        {"weights": {"bias": float("nan")}},
        {"weights": {"bias": 1}, "feature_version": "old"},
    ):
        path.write_text(json.dumps(payload))
        with pytest.raises(ValueError):
            LearnedRanking(path)
