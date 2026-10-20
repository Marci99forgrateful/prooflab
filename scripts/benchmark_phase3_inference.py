"""Isolated CPU scoring costs on stored development states; no native lookahead."""

import json
import time
from pathlib import Path

from prooflab.continuations import DATA
from prooflab.lean import ROOT
from prooflab.models import Candidate, ProofState
from prooflab.outcome import MODELS, OutcomeRanking
from prooflab.phase3_data import digest

examples = []
for path in sorted((DATA / "tasks").glob("*.json")):
    record = json.loads(path.read_text())
    for row in record["states"]:
        state = ProofState.model_validate(row["state"])
        examples.extend(
            (state, Candidate.model_validate(o["candidate"])) for o in row["observations"]
        )
results = {}
for variant in ("outcome", "applicability_only", "old_features_outcome"):
    ranker = OutcomeRanking(MODELS / f"{variant}.json")
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    accumulator = 0.0
    for _ in range(10):
        for state, candidate in examples:
            accumulator += ranker.score(state, candidate)
    wall = time.perf_counter() - wall_start
    cpu = time.process_time() - cpu_start
    calls = 10 * len(examples)
    results[variant] = {
        "model_sha256": ranker.model_hash,
        "calls": calls,
        "wall_s": wall,
        "cpu_s": cpu,
        "mean_wall_us_per_score": 1e6 * wall / calls,
        "checksum": accumulator,
    }
report = {
    "sample": "All collected development pre-action candidates, 10 passes; no evaluation data",
    "script_sha256": digest(Path(__file__)),
    "collection_sha256": digest(DATA / "collection.json"),
    "note": (
        "Single-process scalar scoring, excludes explanation rendering and "
        "every Lean call; host-specific"
    ),
    "results": results,
}
(ROOT / "experiments/phase3/inference-cost.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(results, indent=2))
