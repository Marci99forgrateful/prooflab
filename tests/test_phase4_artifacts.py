"""Scientific provenance, causal controls and real state-scheduling evidence."""

import json
from collections import defaultdict

import pytest

from prooflab.candidates import generate_candidates
from prooflab.frontier import FrontierModel
from prooflab.lean import ROOT
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.phase4_data import DIRECTORY, check_freeze
from prooflab.research_io import read_json, trace_paths

DATA = ROOT / "experiments/phase4/evaluation-v1"


@pytest.fixture(scope="module")
def traces():
    return [Trace.model_validate(read_json(p)) for p in trace_paths(DATA / "traces")]


def test_all_real_experiments_and_preserved_data(traces):
    freeze = check_freeze()
    assert len(freeze["expression_trees"]) == 166 and not freeze["duplicate_pairs"]
    protocol = read_json(DIRECTORY / "protocol.json")
    assert (
        len(traces) == 640
        and len({(t.task.id, t.algorithm, t.metadata["repeat"]) for t in traces}) == 640
    )
    for t in traces:
        assert t.budget.model_dump() == protocol["budget"]
        assert t.status != "execution_error"
        assert t.metrics.attempted_candidates == len(t.nodes) - 1
        assert t.metadata["generator"] == "prooflab.candidates.generate_candidates"
        if t.status == "verified":
            assert t.verification.verified and t.verification.source_sha256 and t.proof
            assert not set(t.verification.axioms) - {"propext", "Classical.choice", "Quot.sound"}
        else:
            assert not t.verification.verified
    assert read_json(DATA / "analysis.json")["repeat_structural_differences"] == []


def test_candidate_controls_and_state_values(traces):
    model = FrontierModel()
    for t in traces:
        if t.algorithm in ("automation", "grind"):
            continue
        for r in t.rankings:
            state = t.nodes[r.node_id].state
            assert state
            pool = generate_candidates(state, 24, frozenset(t.task.forbidden_lemmas))
            assert {c.tactic for c in pool} == {c.tactic for c in r.candidates}
        values = {v.node_id: v for v in t.state_values}
        for v in t.state_values:
            node = t.nodes[v.node_id]
            assert node.state
            parent = t.nodes[node.parent].state if node.parent is not None else None
            expected = model.score(node.state, node.depth, parent)
            assert v.learned_value == expected
            if t.algorithm in ("joint", "frontier", "beam", "linear_frontier"):
                assert v.priority == model.priority(expected, node.depth)
        for d in t.frontier_decisions:
            assert d.selected == min(d.frontier)[1]
            assert d.selected in values
            if t.algorithm == "beam":
                assert len(d.frontier) <= 12
        assert len(t.beam_evictions) == len(set(t.beam_evictions))


def test_negative_result_and_separate_generator_not_hidden(traces):
    counts = defaultdict(int)
    for t in traces:
        counts[t.algorithm] += t.status == "verified"
    assert counts["joint"] == 42 and counts["best_first"] == 44
    summary = read_json(DATA / "summary.json")
    for reference in ("automation", "grind"):
        assert "attempted_candidates" not in summary["paired_differences"][reference]
    study = read_json(ROOT / "experiments/phase4/generator-v1/summary.json")
    new = [
        v for v in study["per_theorem"].values() if v["cohort"] == "separate_new_test_generator_arm"
    ]
    assert sum(r["extended"]["status"] == "verified" for r in new) == 30
    assert all("extended_candidates" not in t.metadata["generator"] for t in traces)


def test_native_repeated_states_are_only_diagnostic(traces):
    index = read_json(ROOT / "experiments/phase4/native-states-v1/index.json")
    paths = {p.name: p for p in trace_paths(DATA / "traces")}
    assert len(index["tasks"]) == 32
    statistics = {}
    for task in index["tasks"]:
        path = ROOT / "experiments/phase4/native-states-v1" / task["file"]
        assert digest(path) == task["sha256"]
        native = read_json(path)
        for name, reference in native["trace_references"].items():
            assert reference["source_sha256"] == digest(paths[name])
        statistics.update(task["statistics"])
    assert len(statistics) == 640
    assert sum(s["repeated_native_shapes"] for s in statistics.values()) > 0
    assert all("no semantic merging" in t.metadata["state_identity"] for t in traces)


def test_research_inventory_pins_real_sources_and_license_caveats():
    sources = json.loads((ROOT / "research/phase4/sources.json").read_text())
    successful = [r for r in sources if "commit" in r]
    assert len(successful) >= 29
    assert all(
        len(r["commit"]) == 40 and all(len(f["sha256"]) == 64 for f in r["files"])
        for r in successful
    )
    report = (ROOT / "docs/phase-4-related-work.md").read_text()
    assert "CC-BY-NC" in report and "LICENSE retrieval returned 404" in report
