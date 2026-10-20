from __future__ import annotations

import subprocess
import time
from pathlib import Path
from threading import Event

import pytest

from prooflab.candidates import LEMMAS
from prooflab.dataset import get_task, load_tasks
from prooflab.lean import ROOT, Cancelled, LeanSession, lake_command, lean_environment, verify
from prooflab.models import Budget, Task
from prooflab.search import search

pytestmark = pytest.mark.integration


def run_lean(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*lake_command(), str(path)],
        cwd=ROOT,
        env=lean_environment(),
        capture_output=True,
        text=True,
        timeout=45,
    )


def test_all_benchmark_statements_and_lemma_names_elaborate(tmp_path: Path) -> None:
    source = (
        "import ProofLab.Bridge\n"
        + "\n".join(f"example : Prop := ∀ {t.binders}, {t.target}" for t in load_tasks())
        + "\n"
        + "\n".join(f"#check {lemma.name}" for lemma in LEMMAS)
    )
    path = tmp_path / "Dataset.lean"
    path.write_text(source)
    outcome = run_lean(path)
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr


def test_native_snapshot_branch_restoration_and_invalid_tactics() -> None:
    with LeanSession(get_task("and_build")) as lean:
        root = lean.initial
        assert root.goals[0].target.head == "And"
        split = lean.step(0, "constructor", 3)
        assert len(split["goals"]) == 2
        parent = split["state_id"]
        bad = lean.step(parent, "exact hq", 3)
        assert bad["status"] == "invalid_candidate"
        left = lean.step(parent, "exact hp", 3)
        assert len(left["goals"]) == 1
        again = lean.step(parent, "exact hp", 3)
        assert left["goals"] == again["goals"]
        restored = lean.step(0, "constructor", 3)
        assert len(restored["goals"]) == 2
        assert lean.step(left["state_id"], "exact hq", 3)["goals"] == []
    assert lean.process is not None and lean.process.poll() is not None


@pytest.mark.parametrize("algorithm", ["bfs", "best_first"])
def test_constructed_unseen_implication_is_independently_verified(algorithm: str) -> None:
    # This theorem is deliberately absent from the benchmark IDs and statement dataset.
    task = Task(
        id="unseen_test",
        title="Unseen renamed chain",
        domain="logic",
        difficulty="moderate",
        split="held_out",
        binders="(A B C : Prop) (f : A → B) (g : B → C) (a : A)",
        target="C",
        display="",
        description="",
    )
    result = search(task, algorithm, Budget(timeout_s=20))  # type: ignore[arg-type]
    assert result.status == "verified", result.model_dump_json()
    assert len(result.proof) >= 3
    assert result.verification.source_sha256
    assert set(result.verification.axioms) <= {"propext", "Classical.choice", "Quot.sound"}
    assert result.metrics.rejected_candidates > 0
    assert any(n.on_proof_path for n in result.nodes)


def test_independent_checker_rejects_wrong_and_admitted_proofs() -> None:
    task = get_task("imp_chain")
    assert not verify(task, ["exact hp"]).verified
    assert not verify(task, ["sorry"]).verified
    assert not verify(task, ["admit"]).verified
    assert verify(task, ["apply hqr", "apply hpq", "assumption"]).verified


def test_transitive_axiom_audit_rejects_untrusted_dependency(tmp_path: Path) -> None:
    path = tmp_path / "Untrusted.lean"
    path.write_text(
        "import ProofLab.Bridge\naxiom untrusted : False\n"
        "theorem prooflab_result : False := untrusted\n#prooflab_audit prooflab_result\n"
    )
    outcome = run_lean(path)
    assert outcome.returncode != 0
    assert "trust policy rejected" in outcome.stdout


def test_budget_failure_does_not_assert_falsity() -> None:
    result = search(get_task("imp_chain"), budget=Budget(max_attempts=1))
    assert result.status == "not_found_within_budget"
    assert result.termination == "resource_limit:attempts"
    assert not result.verification.verified


def test_timeout_is_bounded_and_cleans_up() -> None:
    tick = time.monotonic()
    result = search(get_task("imp_chain"), budget=Budget(timeout_s=0.05))
    assert time.monotonic() - tick < 5
    assert result.status == "not_found_within_budget"
    assert result.termination.startswith("resource_limit")


def test_cancellation_closes_native_process() -> None:
    cancelled = Event()
    with LeanSession(get_task("imp_chain"), cancel=cancelled) as lean:
        cancelled.set()
        with pytest.raises(Cancelled):
            lean.step(0, "apply hqr", 3)
    assert lean.process is not None and lean.process.poll() is not None
