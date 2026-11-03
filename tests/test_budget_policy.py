"""Operational completion, conservative decisions and native intermediate proofs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prooflab.adaptive_model import mode_features, predict
from prooflab.budget_policy import BudgetModel, choose, features, sigmoid
from prooflab.budget_search import run
from prooflab.models import Budget, ProofState
from prooflab.phase7_data import check_freeze, tasks
from prooflab.phase7_training import completion_fit


def predictions(p_symbolic: float, p_hybrid: float) -> dict[str, dict[str, float]]:
    return {
        "symbolic": {"completion_probability": p_symbolic, "conditional_attempts": 2},
        "hybrid": {"completion_probability": p_hybrid, "conditional_attempts": 20},
        "typed": {"completion_probability": 0.1, "conditional_attempts": 1},
    }


def test_conditional_low_cost_does_not_imply_completion() -> None:
    p = predictions(0.1, 0.9)
    assert choose(p, "symbolic", "cost", 160)[0] == "typed"
    assert choose(p, "symbolic", "completion", 160)[0] == "hybrid"
    assert choose(p, "symbolic", "joint", 160)[0] == "hybrid"


@pytest.mark.parametrize("margin", [0.1, 0.2, 0.3])
def test_conservative_policy_requires_observed_model_advantage(margin: float) -> None:
    assert choose(predictions(0.6, 0.61), "symbolic", "conservative", 160, margin)[0] == "symbolic"
    assert choose(predictions(0.1, 0.9), "symbolic", "conservative", 160, margin)[0] == "hybrid"


def test_remaining_budget_changes_joint_tradeoff() -> None:
    p = predictions(0.8, 0.9)
    assert choose(p, "symbolic", "joint", 600)[0] == "hybrid"
    assert choose(p, "symbolic", "joint", 10)[0] == "symbolic"


def test_features_are_budgeted_and_have_no_identifiers_or_future() -> None:
    a = ProofState(state_id=19, goals=[])
    b = ProofState(state_id=999, goals=[])
    assert features(a, 160, 28, 8, 1) == features(b, 160, 28, 8, 1)
    assert features(a, 160, 28, 8, 1) != features(a, 600, 80, 18, 1)
    assert all(
        not any(s in k for s in ("task_id", "state_id", "verified", "proof", "prefix"))
        for k in features(a, 160, 28, 8, 1)
        if k != "proof_hypotheses"
    )


def test_both_cpu_architectures_learn_completion_instead_of_cost() -> None:
    rows = []
    for family in ("a", "b"):
        for mode in ("symbolic", "hybrid", "typed"):
            for i in range(20):
                rows.append(
                    dict(
                        task_id=family + str(i),
                        family=family,
                        mode=mode,
                        features={"bias": 1.0, "remaining_attempts": i / 20},
                        completion=int(mode == "hybrid"),
                    )
                )
    for nonlinear in (False, True):
        model = completion_fit(rows, nonlinear)
        hybrid = sigmoid(
            predict(model, mode_features({"bias": 1.0, "remaining_attempts": 0.5}, "hybrid"))
        )
        symbolic = sigmoid(
            predict(model, mode_features({"bias": 1.0, "remaining_attempts": 0.5}, "symbolic"))
        )
        assert hybrid > symbolic + 0.1


def test_frozen_new_test_is_distinct_and_not_used_for_training() -> None:
    f = check_freeze()
    assert f["duplicate_pairs"] == [] and f["evaluation_accessed"] is False
    assert len(tasks("evaluation")) == 48 and len(tasks()) == 64
    assert not {t.id for t in tasks()} & {t.id for t in tasks("evaluation")}


def test_test_trained_models_are_refused(tmp_path: Path) -> None:
    p = tmp_path / "model.json"
    p.write_text(json.dumps(dict(feature_version="budget-completion-v1", evaluation_accessed=True)))
    with pytest.raises(ValueError, match="evaluation-trained"):
        BudgetModel(p)


@pytest.mark.integration
def test_real_intermediate_state_replay_audits_original_theorem() -> None:
    task = next(t for t in tasks() if t.id == "p7_dev_conjunctive_continuations_01")
    trace = run(
        task,
        Budget(max_attempts=160, max_depth=10, timeout_s=12),
        prefix=["constructor"],
        forced_mode="symbolic",
    )
    assert trace.status == "verified", trace.error
    assert trace.proof[0] == "constructor" and trace.verification.verified
    assert trace.verification.source_sha256 and len(trace.nodes[0].state.goals) == 2
    assert trace.metrics.attempted_candidates <= 160
    assert trace.nodes[-1].on_proof_path


@pytest.mark.integration
def test_bounded_noncompletion_is_not_mathematical_falsity() -> None:
    task = next(t for t in tasks() if t.id == "p7_dev_conjunctive_continuations_01")
    trace = run(task, Budget(max_attempts=1, timeout_s=8), forced_mode="typed")
    assert trace.status == "not_found_within_budget"
    assert not trace.verification.verified
    assert trace.metrics.attempted_candidates == 1
    assert trace.termination == "resource_limit:attempts"
