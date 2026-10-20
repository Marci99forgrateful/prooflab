from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from prooflab import splits
from prooflab.dataset import get_task


def test_frozen_evaluation_is_new_and_disjoint() -> None:
    frozen = splits.check_freeze()
    assert len(frozen["evaluation_ids"]) == 24
    assert frozen["evaluation_family_count"] == 6
    assert not frozen["duplicate_pairs"]
    assert len(frozen["permitted_development_ids"]) == 48
    assert not set(frozen["evaluation_ids"]) & set(frozen["permitted_development_ids"])
    assert not set(frozen["selection_train_ids"]) & set(frozen["selection_validation_ids"])


def test_tampered_frozen_data_blocks_training(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("evaluation.json", "protocol.json", "frozen.json"):
        shutil.copy2(splits.PHASE2 / name, tmp_path / name)
    monkeypatch.setattr(splits, "PHASE2", tmp_path)
    rows = json.loads((tmp_path / "evaluation.json").read_text())
    rows[0]["target"] = "False"
    (tmp_path / "evaluation.json").write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="Frozen"):
        splits.check_freeze()


@pytest.mark.integration
def test_native_alpha_and_parameter_reordering_leakage_is_detected() -> None:
    original = get_task("imp_chain")
    renamed = original.model_copy(
        update={
            "id": "renamed_structure",
            "binders": "(A B C : Prop) (f : A → B) (g : B → C) (a : A)",
            "target": "C",
        }
    )
    reordered = original.model_copy(
        update={
            "id": "reordered_structure",
            "binders": "(R Q P : Prop) (hp : P) (hqr : Q → R) (hpq : P → Q)",
        }
    )
    different = original.model_copy(update={"id": "different_structure", "target": "P ∧ R"})
    trees = splits.native_structures([original, renamed, reordered, different])
    assert splits.equivalent(trees[original.id], trees[renamed.id])
    assert splits.equivalent(trees[original.id], trees[reordered.id])
    assert not splits.equivalent(trees[original.id], trees[different.id])


def test_unresolved_lean_terms_cannot_be_fingerprinted() -> None:
    with pytest.raises(ValueError, match="Unresolved"):
        splits.expression_graph(["UNEXPECTED_METAVARIABLE"])
