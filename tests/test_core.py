from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from prooflab import candidates
from prooflab.benchmark import summary, trajectory
from prooflab.dataset import get_task, load_tasks
from prooflab.models import Budget, Expression, Goal, Hypothesis, Node, ProofState, Trace


def example_state() -> ProofState:
    return ProofState(
        state_id=0,
        goals=[
            Goal(
                id="g0",
                target=Expression(text="R", head="", forall=False),
                hypotheses=[
                    Hypothesis(
                        name="hpq", id="h0", type=Expression(text="P → R", head="", forall=True)
                    ),
                    Hypothesis(
                        name="hp", id="h1", type=Expression(text="P", head="", forall=False)
                    ),
                ],
            )
        ],
    )


def test_dataset_is_disjoint_diverse_and_contains_no_solutions() -> None:
    tasks = load_tasks()
    assert len(tasks) >= 60
    assert len({t.id for t in tasks}) == len(tasks)
    assert {t.domain for t in tasks} == {"logic", "order", "algebra", "sets"}
    for domain in {t.domain for t in tasks}:
        assert sum(t.domain == domain and t.split == "held_out" for t in tasks) >= 3
    assert all("proof" not in t.model_dump() for t in tasks)
    assert all("prooflab_result" in t.forbidden_lemmas for t in tasks)
    assert all("sorry" not in t.target for t in tasks)


def test_candidates_are_state_driven_and_deterministic() -> None:
    state = example_state()
    first = candidates.generate_candidates(state)
    assert first == candidates.generate_candidates(state)
    assert "apply hpq" in {c.tactic for c in first}
    assert "apply hp" not in {c.tactic for c in first}
    renamed = state.model_copy(deep=True)
    renamed.goals[0].hypotheses[0].name = "unseen_implication"
    assert "apply unseen_implication" in {c.tactic for c in candidates.generate_candidates(renamed)}
    assert "get_task" not in inspect.getsource(candidates)


def test_generator_bounds_and_does_not_execute_hostile_names() -> None:
    state = example_state()
    state.goals[0].hypotheses[0].name = "h; run_tac IO.println 1"
    assert len(candidates.generate_candidates(state, 1)) == 1
    assert all("run_tac" not in c.tactic for c in candidates.generate_candidates(state))
    assert candidates.generate_candidates(ProofState(state_id=0, goals=[])) == []


def test_ranking_reorders_without_adding_candidates() -> None:
    state = example_state()
    steps = candidates.generate_candidates(state)
    ranked = candidates.HeuristicRanking().rank_candidates(state, steps)
    assert {c.tactic for c in steps} == {c.tactic for c in ranked}
    assert candidates.UniformRanking().rank_candidates(state, steps) == steps


def test_target_filter_applies_to_the_retrieval_corpus() -> None:
    state = example_state()
    state.goals[0].target = Expression(text="a ≤ c", head="LE.le", forall=False)
    names = {c.lemma for c in candidates.generate_candidates(state, 64, frozenset({"le_trans"}))}
    assert "le_trans" not in names
    assert "le_refl" in names


@pytest.mark.parametrize(
    "values", [{"max_depth": 0}, {"max_attempts": 10001}, {"timeout_s": 0}, {"max_candidates": 65}]
)
def test_invalid_budgets_are_rejected(values: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        Budget(**values)


def test_failed_search_is_not_counted_as_a_proof() -> None:
    trace = Trace(task=get_task("imp_chain"), algorithm="bfs", budget=Budget())
    results = summary([trace])
    assert results["bfs"]["verified"] == 0
    assert results["bfs"]["attempted"] == 1


def test_trajectory_never_labels_off_path_as_mathematically_useless() -> None:
    state = example_state()
    trace = Trace(
        task=get_task("imp_chain"),
        algorithm="bfs",
        budget=Budget(),
        nodes=[
            Node(id=0, parent=None, depth=0, state=state, tactic=None, status="root"),
            Node(id=1, parent=0, depth=1, state=None, tactic="rfl", status="rejected"),
        ],
    )
    record = trajectory(trace)[0]
    assert record["valid"] is False
    assert record["on_verified_path"] is False
    assert "NOT mathematically useless" in record["label_policy"]
