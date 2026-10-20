from __future__ import annotations

import copy
import json

import pytest

from prooflab.continuations import DATA
from prooflab.models import Candidate, ProofState
from prooflab.outcome_features import features
from prooflab.outcome_training import outcome_pairs
from prooflab.phase3_data import check_freeze


def real_record() -> dict:
    return json.loads((DATA / "tasks/and_swap.json").read_text())


def test_actual_nonterminal_alternatives_supply_downstream_preferences() -> None:
    pairs = outcome_pairs([real_record()], set(check_freeze()["permitted_development_ids"]))
    nonterminal = [p for p in pairs if p["both_nonterminal"]]
    assert nonterminal
    assert any(
        p["better"] == "rcases h with ⟨h0, h1⟩" and p["worse"] == "constructor" for p in nonterminal
    )
    assert all(p["better_cost"] < p["worse_cost"] for p in pairs)


def test_censored_valid_alternatives_are_never_negative_labels() -> None:
    record = copy.deepcopy(real_record())
    for state in record["states"]:
        for o in state["observations"]:
            if o["continuation"]:
                o["continuation"]["status"] = "censored"
                o["continuation"]["termination"] = "resource_limit:attempts"
    assert outcome_pairs([record], {record["task_id"]}) == []


def test_invalid_or_unverified_actions_cannot_be_success_preferences() -> None:
    record = copy.deepcopy(real_record())
    observation = next(
        o
        for r in record["states"]
        for o in r["observations"]
        if o["continuation"] and o["continuation"]["status"] == "verified"
    )
    observation["status"] = "invalid_candidate"
    with pytest.raises(ValueError, match="accepted"):
        outcome_pairs([record], {record["task_id"]})
    record = real_record()
    with pytest.raises(ValueError, match="Forbidden"):
        outcome_pairs([record], {"some_other_development_task"})


def test_features_condition_closing_evidence_on_actual_action() -> None:
    rows = [
        json.loads(line)
        for line in (DATA.parents[1] / "phase2-training/examples.jsonl").read_text().splitlines()
    ]
    row = next(
        r for r in rows if r["positive_tactic"] == "assumption" and r["task_id"] == "imp_chain"
    )
    state = ProofState.model_validate(row["state"])
    assumption = Candidate(tactic="assumption", category="goal", reason="Real available candidate")
    another = Candidate(tactic="apply hqr", category="hypothesis", reason="Real context hypothesis")
    assert features(state, assumption)["p3:assumption_exact"] == 1
    assert "p3:assumption_exact" not in features(state, another)
    assert not any("p3:" in n for n in features(state, assumption, "old"))


def test_phase3_freeze_preserves_prior_artifacts_and_disjoint_families() -> None:
    frozen = check_freeze()
    assert len(frozen["evaluation_ids"]) == 32
    assert not frozen["duplicate_pairs"]
    assert not set(frozen["evaluation_ids"]) & set(frozen["permitted_development_ids"])
    assert len(frozen["validation_ids"]) == 12
    assert "models/phase2/ranker.json" in frozen["prior_artifacts"]
