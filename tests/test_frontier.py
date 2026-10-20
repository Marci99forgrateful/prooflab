"""Actual trajectory training, pre-decision scoring and scheduler controls."""

import json
from pathlib import Path

import pytest

from prooflab.candidates import generate_candidates
from prooflab.dataset import load_tasks
from prooflab.frontier import MODELS, FrontierModel, state_features
from prooflab.frontier_training import examples, fit
from prooflab.models import Budget, ProofState
from prooflab.phase4_data import check_freeze
from prooflab.search import search


def test_no_test_examples_and_censoring():
    frozen = check_freeze()
    rows, ledger = examples(set(frozen["permitted_development_ids"]))
    assert len(rows) == 139 and ledger["censored"] == 16 and ledger["terminal_excluded"] == 44
    assert all(
        r["split"] == "development" and not r["task_id"].startswith(("p2_", "p3_", "p4_"))
        for r in rows
    )
    with pytest.raises(ValueError, match="Forbidden"):
        examples(set())


def test_reproduce_frozen_state_weights():
    frozen = check_freeze()
    rows, _ = examples(set(frozen["permitted_development_ids"]))
    expected = FrontierModel().artifact
    model = fit(rows, expected.mode, float(expected.provenance["selection"]["l2"]))
    assert model.weights == expected.weights
    assert model.means == expected.means and model.scales == expected.scales
    assert json.loads((MODELS / "training-report.json").read_text())["selected"]["mode"] == "linear"


def test_state_features_have_no_identifiers_or_future(monkeypatch):
    row = examples(set(check_freeze()["permitted_development_ids"]))[0][0]
    state = ProofState.model_validate(row["state"])
    parent = ProofState.model_validate(row["parent"])

    def forbidden(*args, **kwargs):
        raise AssertionError("Scoring cannot query Lean")

    monkeypatch.setattr("prooflab.lean.LeanSession", forbidden)
    value = FrontierModel().score(state, row["depth"], parent)
    assert isinstance(value, float)
    altered = state.model_copy(deep=True)
    altered.state_id = 100000
    for g in altered.goals:
        g.id = "new native handle"
        for h in g.hypotheses:
            h.id = "another handle"
    assert state_features(altered, row["depth"], parent) == state_features(
        state, row["depth"], parent
    )


@pytest.mark.integration
def test_actual_joint_and_beam_decisions():
    task = load_tasks()[0]
    traces = [
        search(task, a, Budget(timeout_s=20), comparison_frontier=FrontierModel(), beam_width=1)
        for a in ("best_first", "frontier", "joint", "beam")
    ]
    assert all(t.status == "verified" and t.verification.verified for t in traces)
    for t in traces:
        assert t.frontier_decisions and t.state_values
        values = {v.node_id: v for v in t.state_values}
        for d in t.frontier_decisions:
            assert d.selected == min(d.frontier)[1]
            assert d.selected in values
        for ranking in t.rankings:
            node = t.nodes[ranking.node_id]
            assert node.state
            assert {
                c.tactic
                for c in generate_candidates(node.state, 24, frozenset(task.forbidden_lemmas))
            } == {c.tactic for c in ranking.candidates}
    assert all(len(d.frontier) <= 1 for d in traces[-1].frontier_decisions)


def test_training_refuses_overwrite(tmp_path: Path):
    from prooflab.frontier_training import train

    with pytest.raises(ValueError, match="new frontier"):
        train(tmp_path)
