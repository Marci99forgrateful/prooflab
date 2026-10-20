"""Pre-selection calibration, development-only original statements."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from prooflab.lean import ROOT
from prooflab.models import Task, Budget
from prooflab.search import search
from prooflab.retrieval import TypedProvider
from prooflab.native_retrieval import RetrievalSession


def main():
    d = ROOT / "experiments/phase5/pilot-v1"
    d.mkdir(parents=True, exist_ok=False)
    tasks = [
        Task.model_validate(t)
        for t in json.loads((ROOT / "benchmarks/phase5/pilot.json").read_text())
    ]
    with ThreadPoolExecutor(max_workers=2) as p:
        jobs = {
            p.submit(
                search,
                t,
                "best_first",
                Budget(
                    max_depth=12,
                    max_expansions=80,
                    max_candidates=24,
                    max_attempts=600,
                    timeout_s=18,
                    tactic_timeout_s=2,
                ),
                provider=TypedProvider(m),
                session_factory=RetrievalSession,
            ): (t.id, m)
            for t in tasks
            for m in ("original", "typed")
        }
        for future in as_completed(jobs):
            ident, mode = jobs[future]
            t = future.result()
            t.metadata["generator_mode"] = mode
            (d / f"{ident}--{mode}.json").write_text(t.model_dump_json(indent=2) + "\n")
            print(
                ident,
                mode,
                t.status,
                t.termination,
                t.metrics.attempted_candidates,
                t.proof,
                flush=True,
            )


if __name__ == "__main__":
    main()
