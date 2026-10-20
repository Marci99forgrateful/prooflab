"""Development-only baseline difficulty pilot, never final-test model selection."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from prooflab.models import Budget, Task
from prooflab.search import metadata, search

root = Path(__file__).resolve().parents[1]
tasks = [
    Task.model_validate(t) for t in json.loads((root / "benchmarks/phase3/pilot.json").read_text())
]
directory = root / "experiments/phase3/pilot-v1"
(directory / "traces").mkdir(parents=True, exist_ok=False)
budget = Budget(max_depth=10, max_expansions=70, max_attempts=500, timeout_s=12, tactic_timeout_s=2)
with ThreadPoolExecutor(max_workers=2) as pool:
    futures = [pool.submit(search, t, a, budget) for t in tasks for a in ["bfs", "best_first"]]
    for future in as_completed(futures):
        trace = future.result()
        (directory / "traces" / f"{trace.task.id}--{trace.algorithm}.json").write_text(
            trace.model_dump_json(indent=2) + "\n"
        )
        print(
            trace.task.id,
            trace.algorithm,
            trace.status,
            trace.termination,
            trace.metrics.attempted_candidates,
            flush=True,
        )
(directory / "provenance.json").write_text(
    json.dumps(
        {
            "metadata": metadata(),
            "budget": budget.model_dump(),
            "purpose": "Development-only difficulty calibration; no final evaluation searches or model comparison",
            "tasks": len(tasks),
        },
        indent=2,
    )
    + "\n"
)
