from __future__ import annotations

import csv
import hashlib
import json

import pytest

from prooflab.candidates import generate_candidates
from prooflab.evaluation import summarize
from prooflab.lean import ROOT, theorem_source
from prooflab.learning import LearnedRanking
from prooflab.models import Trace
from prooflab.outcome import MODELS, OutcomeRanking
from prooflab.phase3_data import DIRECTORY, check_freeze, digest, read_tasks
from prooflab.phase3_evaluation import report_protocol
from prooflab.research_io import raw_bytes, trace_paths
from prooflab.search import path_to
from prooflab.splits import native_structures


def test_final_phase3_execution_archive_and_controls_are_real_and_complete() -> None:
    directory = ROOT / "experiments/phase3/evaluation-v1"
    protocol = report_protocol()
    frozen = check_freeze()
    storage = json.loads((directory / "trace-storage.json").read_text())
    report = json.loads((directory / "summary.json").read_text())
    expected = {
        (t, a, str(r))
        for t in frozen["evaluation_ids"]
        for a in protocol["algorithms"]
        for r in range(
            protocol["ablation_repetitions"]
            if a in protocol["ablation_algorithms"]
            else protocol["repetitions"]
        )
    }
    paths = trace_paths(directory / "traces")
    assert len(paths) == len(expected) == 384
    traces = []
    pools = {}
    p2, p3 = LearnedRanking(), OutcomeRanking()
    assert report["provenance"]["models"]["outcome"] == p3.model_hash
    assert report["provenance"]["phase2_model_sha256"] == p2.model_hash
    for path in paths:
        raw = raw_bytes(path)
        assert (
            storage["traces"][path.name.removesuffix(".gz")]["raw_sha256"]
            == hashlib.sha256(raw).hexdigest()
        )
        t = Trace.model_validate_json(raw)
        traces.append(t)
        assert t.metrics.attempted_candidates == len(t.nodes) - 1
        assert t.metadata["outcome_model_sha256"] == p3.model_hash
        assert t.budget.model_dump() == protocol["budget"]
        if t.status == "verified":
            assert t.verification.verified
            assert t.lean_source == theorem_source(t.task, t.proof)
            assert (
                t.verification.source_sha256 == hashlib.sha256(t.lean_source.encode()).hexdigest()
            )
            assert set(t.verification.axioms) <= {"propext", "Classical.choice", "Quot.sound"}
        for ranking in t.rankings:
            state = t.nodes[ranking.node_id].state
            assert state is not None
            generated = generate_candidates(
                state, t.budget.max_candidates, frozenset(t.task.forbidden_lemmas)
            )
            actual = {c.tactic: c for c in generated}
            assert set(actual) == {c.tactic for c in ranking.candidates}
            key = (t.task.id, tuple(t.nodes[i].tactic for i in path_to(t.nodes, ranking.node_id)))
            pool = tuple(
                c.tactic for c in sorted(ranking.candidates, key=lambda c: c.generated_order)
            )
            assert pools.setdefault(key, pool) == pool
            # Recompute every stored main-model score from the actual state;
            # no future nodes/outcomes enter scoring or candidate availability.
            for c in ranking.candidates:
                assert c.learned_score == p2.score(state, actual[c.tactic])
                assert c.outcome_score == p3.score(state, actual[c.tactic])
    assert {(t.task.id, t.algorithm, t.metadata["repeat"]) for t in traces} == expected
    assert {t.metadata["code_commit"] for t in traces} == {report["provenance"]["code_commit"]}
    analysis = summarize(
        traces,
        {**protocol, "evaluation_families": json.loads((DIRECTORY / "families.json").read_text())},
    )
    assert analysis["paired_differences"] == report["paired_differences"]
    assert analysis["per_theorem"] == report["per_theorem"]
    for algorithm, group in analysis["results"].items():
        assert all(report["results"][algorithm][k] == v for k, v in group.items() if k != "metrics")
    rows = list(csv.DictReader((directory / "results.csv").open()))
    assert len(rows) == 384


@pytest.mark.integration
def test_phase3_native_structures_reproduce_without_new_equivalent_tasks() -> None:
    frozen = check_freeze()
    actual = native_structures(read_tasks())
    assert all(actual[ident] == frozen["expression_trees"][ident] for ident in actual)


def test_post_evaluation_diagnostics_cannot_enter_training() -> None:
    from prooflab.outcome_training import outcome_pairs
    from prooflab.research import DIAGNOSTICS

    frozen = check_freeze()
    records = [
        json.loads(p.read_text()) for p in DIAGNOSTICS.glob("*.json") if p.name != "manifest.json"
    ]
    assert records
    for record in records:
        assert record["split"] == "held_out"
        assert record["model_freeze_sha256"] == digest(MODELS / "frozen.json")
        with pytest.raises(ValueError, match="Forbidden"):
            outcome_pairs([record], set(frozen["permitted_development_ids"]))
