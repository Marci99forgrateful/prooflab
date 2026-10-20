"""Isolated pure-Python state inference microbenchmark; no native Lean queries."""

import json
import statistics
import time

from prooflab.frontier import MODELS, FrontierModel
from prooflab.frontier_training import examples
from prooflab.lean import ROOT
from prooflab.models import ProofState
from prooflab.phase4_data import check_freeze
from prooflab.search import metadata

rows, _ = examples(set(check_freeze()["permitted_development_ids"]))
data = [
    (ProofState.model_validate(r["state"]), r["depth"], ProofState.model_validate(r["parent"]))
    for r in rows
]
results = {}
for name in ["selected", "linear"]:
    model = FrontierModel(MODELS / f"{name}.json")
    start, cpu = time.monotonic(), time.process_time()
    checksum = 0.0
    for _ in range(20):
        for state, depth, parent in data:
            checksum += model.score(state, depth, parent)
    elapsed, used = time.monotonic() - start, time.process_time() - cpu
    results[name] = dict(
        model_sha256=model.sha256,
        score_calls=len(data) * 20,
        wall_s=elapsed,
        cpu_s=used,
        cpu_microseconds_per_call=used / (len(data) * 20) * 1e6,
        checksum=checksum,
    )
validation = set(check_freeze()["validation_ids"])
training = [r for r in rows if r["task_id"] not in validation]
per_task = {
    ident: statistics.mean(r["target"] for r in training if r["task_id"] == ident)
    for ident in {r["task_id"] for r in training}
}
mean = statistics.mean(per_task.values())
errors = {
    ident: statistics.mean((r["target"] - mean) ** 2 for r in rows if r["task_id"] == ident)
    for ident in {r["task_id"] for r in rows if r["task_id"] in validation}
}
output = dict(
    metadata=metadata(),
    models=results,
    development_constant_baseline=dict(
        mean=mean, validation_theorem_mse=statistics.mean(errors.values())
    ),
    note=(
        "Host-specific CPU score/explanation cost over development states; "
        "isolated from Lean, primary full-search costs reported separately"
    ),
)
(ROOT / "experiments/phase4/inference-cost.json").write_text(json.dumps(output, indent=2) + "\n")
print(results)
