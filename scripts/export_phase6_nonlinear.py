"""Export the non-selected boosted validation expert for independent inspection."""

from __future__ import annotations

import gzip
import json

from prooflab.adaptive_fit import boosted_pairs, pair_loss
from prooflab.adaptive_model import MODELS, VERSION
from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.phase6_data import check_freeze
from prooflab.research_io import read_json


def main() -> None:
    frozen = check_freeze()
    report = read_json(MODELS / "training-report.json")
    pairs = json.loads(gzip.decompress((MODELS / "preferences.json.gz").read_bytes()))
    train = [p for p in pairs if p["task_id"] in frozen["training_ids"]]
    validation = [p for p in pairs if p["task_id"] in frozen["validation_ids"]]
    config = min(
        (c for c in report["candidates"] if c["kind"] == "boosted"),
        key=lambda c: c["validation_loss"],
    )["configuration"]
    model = boosted_pairs(train, **config, seed=0)
    artifact = dict(
        feature_version=VERSION,
        evaluation_accessed=False,
        selector_ready=False,
        role="Non-selected validation-only reference; not an evaluated search policy",
        training_ids=frozen["training_ids"],
        validation_ids=frozen["validation_ids"],
        relevance=model,
        validation_loss=pair_loss(validation, model),
        selected_configuration_by_mean_seed_loss=config,
        seed=0,
        preferences_sha256=digest(MODELS / "preferences.json.gz"),
        fitter_sha256=digest(ROOT / "src/prooflab/adaptive_fit.py"),
        procedure_sha256=digest(ROOT / "scripts/export_phase6_nonlinear.py"),
    )
    path = MODELS / "boosted-validation-reference.json"
    if path.exists():
        raise ValueError("Refuse to overwrite trained reference")
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print("Exported rejected boosted validation expert:", artifact["validation_loss"])


if __name__ == "__main__":
    main()
