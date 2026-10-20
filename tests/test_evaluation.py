import json

import pytest

from prooflab.candidates import UniformRanking
from prooflab.dataset import get_task
from prooflab.evaluation import interval
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, Trace
from prooflab.search import search
from prooflab.splits import ROOT, check_freeze
from prooflab.training import fit, training_pairs


def test_bootstrap_keeps_identical_differences_exact():
    assert interval([2.0, 2.0], [[0, 1], [0, 0], [1, 1]]) == {
        "estimate": 2.0,
        "lower": 2.0,
        "upper": 2.0,
    }


def test_exported_model_reproduces_from_permitted_evidence():
    ranker = LearnedRanking()
    rows = [
        json.loads(line)
        for line in (ROOT / "experiments/phase2-training/examples.jsonl").read_text().splitlines()
    ]
    p = ranker.model.provenance
    assert set(p["training_task_ids"]) <= set(check_freeze()["permitted_development_ids"])
    assert (
        fit(training_pairs(rows), p["selected_l2"], p["epochs"], p["learning_rate"], p["seed"])
        == ranker.model.weights
    )


@pytest.mark.integration
def test_learned_uses_real_lean_and_preserves_candidate_pools():
    ranker = LearnedRanking()
    task = get_task("imp_chain")  # Development regression, never evaluation for tuning.
    budget = Budget(timeout_s=20)
    traces = [
        search(task, a, budget, comparison_ranker=ranker) for a in ("bfs", "best_first", "learned")
    ]
    assert all(t.status == "verified" and t.verification.verified for t in traces)
    assert all(t.verification.source_sha256 and t.rankings for t in traces)
    pools = [{c.tactic for c in t.rankings[0].candidates} for t in traces]
    assert pools[0] == pools[1] == pools[2]
    assert traces[2].metrics.model_inference_s > 0
    assert Trace.model_validate_json(traces[2].model_dump_json()) == traces[2]


@pytest.mark.integration
def test_ranker_cannot_change_candidates():
    class DroppingRanking(UniformRanking):
        def rank_candidates(self, state, candidates):
            return []

    trace = search(get_task("imp_chain"), ranking=DroppingRanking())
    assert trace.status == "execution_error"
    assert "altered candidate availability" in trace.error
