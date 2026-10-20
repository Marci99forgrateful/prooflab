from __future__ import annotations

import hashlib
import json

from prooflab.candidates import generate_candidates
from prooflab.evaluation import summarize
from prooflab.lean import ROOT, theorem_source
from prooflab.learning import LearnedRanking
from prooflab.models import Trace
from prooflab.search import path_to
from prooflab.splits import PHASE2, check_freeze


def test_phase2_evidence_is_complete_verified_and_reproducible() -> None:
    directory = ROOT / "experiments/phase2/evaluation-v1"
    protocol = json.loads((PHASE2 / "protocol.json").read_text())
    frozen = check_freeze()
    report = json.loads((directory / "summary.json").read_text())
    ranker = LearnedRanking()
    traces = [
        Trace.model_validate_json(p.read_text())
        for p in sorted((directory / "traces").glob("*.json"))
    ]
    expected = {
        (t, a, str(r))
        for t in frozen["evaluation_ids"]
        for a in protocol["algorithms"]
        for r in range(protocol["repetitions"])
    }
    assert len(traces) == len(expected) == 288
    assert {(t.task.id, t.algorithm, t.metadata["repeat"]) for t in traces} == expected
    assert {t.budget.model_dump_json() for t in traces} == {traces[0].budget.model_dump_json()}
    assert report["provenance"]["model_sha256"] == ranker.model_hash
    assert report["provenance"]["evaluation_sha256"] == frozen["evaluation_sha256"]
    assert {t.metadata["code_commit"] for t in traces} == {report["provenance"]["code_commit"]}
    for key, value in summarize(traces, protocol).items():
        assert report[key] == value
    # Shared exact tactic prefixes must expose the same generated candidates,
    # even when different policies reach or expand them at different times.
    pools = {}
    for t in traces:
        assert t.metrics.attempted_candidates == len(t.nodes) - 1
        assert t.task.split == "held_out"
        assert t.metadata["model_sha256"] == ranker.model_hash
        if t.status == "verified":
            assert t.verification.verified and t.proof
            source = theorem_source(t.task, t.proof)
            assert t.lean_source == source
            assert t.verification.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
            assert set(t.verification.axioms) <= {"propext", "Classical.choice", "Quot.sound"}
        for record in t.rankings:
            node = t.nodes[record.node_id]
            assert node.state is not None
            generated = generate_candidates(
                node.state, t.budget.max_candidates, frozenset(t.task.forbidden_lemmas)
            )
            by_tactic = {c.tactic: c for c in generated}
            assert set(by_tactic) == {c.tactic for c in record.candidates}
            key = (t.task.id, tuple(t.nodes[i].tactic for i in path_to(t.nodes, node.id)))
            pool = tuple(
                c.tactic for c in sorted(record.candidates, key=lambda c: c.generated_order)
            )
            assert pools.setdefault(key, pool) == pool
            for c in record.candidates:
                assert c.learned_score == ranker.score(node.state, by_tactic[c.tactic])
                assert c.heuristic_score == by_tactic[c.tactic].prior
