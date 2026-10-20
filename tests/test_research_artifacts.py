from __future__ import annotations

import hashlib
import json

from prooflab.benchmark import summary
from prooflab.dataset import load_tasks
from prooflab.lean import ROOT, theorem_source
from prooflab.models import Trace


def test_recorded_experiments_are_complete_and_consistent() -> None:
    runs = list((ROOT / "experiments").glob("*/summary.json"))
    assert runs, "At least one actual measured run must accompany the portfolio"
    for result in runs:
        traces = [
            Trace.model_validate_json(p.read_text())
            for p in (result.parent / "traces").glob("*.json")
        ]
        report = json.loads(result.read_text())
        selected = [t for t in load_tasks() if report["provenance"]["split"] in ("all", t.split)]
        expected = {(t.id, a) for t in selected for a in report["provenance"]["algorithms"]}
        assert len(traces) == len(expected)
        assert {(t.task.id, t.algorithm) for t in traces} == expected
        assert summary(traces) == report["results"]
        assert len({t.budget.model_dump_json() for t in traces}) == 1
        assert {t.metadata["code_commit"] for t in traces} == {report["provenance"]["code_commit"]}
        for trace in traces:
            if trace.status == "verified":
                assert trace.verification.verified and trace.proof
                source = theorem_source(trace.task, trace.proof)
                assert source == trace.lean_source
                assert (
                    hashlib.sha256(source.encode()).hexdigest() == trace.verification.source_sha256
                )
                assert set(trace.verification.axioms) <= {
                    "propext",
                    "Classical.choice",
                    "Quot.sound",
                }
                assert all(n.tactic != "sorry" for n in trace.nodes)
            assert trace.metrics.attempted_candidates == len(trace.nodes) - 1
            assert sum(n.on_proof_path for n in trace.nodes) == (
                len(trace.proof) + 1 if trace.status == "verified" else 0
            )
