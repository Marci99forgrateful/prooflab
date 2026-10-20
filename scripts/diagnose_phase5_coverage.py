"""Matched Phase 4 diagnosis, excluded from all fresh test scores and training."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from prooflab.dataset import get_task
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, Trace
from prooflab.native_retrieval import RetrievalSession
from prooflab.outcome import OutcomeRanking
from prooflab.phase3_data import digest
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.retrieval import TypedProvider
from prooflab.search import metadata, search


def main():
    import sys

    report_only = "--report-only" in sys.argv
    d = ROOT / "experiments/phase5/coverage-v1"
    ids = ["p4_witness_transport", "p4_cubic_pair", "p4_inverse_right", "p4_lattice_meet"]
    rows = []
    if report_only:
        for path in trace_paths(d / "traces"):
            t = Trace.model_validate(read_json(path))
            rows.append(
                dict(
                    task_id=t.task.id,
                    generator=t.metadata["generator_mode"],
                    status=t.status,
                    termination=t.termination,
                    metrics=t.metrics.model_dump(),
                    proof=t.proof,
                    verification=t.verification.model_dump(),
                    trace=path.name if path.suffix == ".gz" else path.name + ".gz",
                    root_selected=t.retrievals[0]["selected"] if t.retrievals else [],
                )
            )
    else:
        (d / "traces").mkdir(parents=True, exist_ok=False)
        ids = ["p4_witness_transport", "p4_cubic_pair", "p4_inverse_right", "p4_lattice_meet"]
        with ThreadPoolExecutor(max_workers=2) as p:
            jobs = {
                p.submit(
                    search,
                    get_task(i),
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
                    comparison_ranker=LearnedRanking(),
                    comparison_outcome=OutcomeRanking(),
                ): (i, m)
                for i in ids
                for m in ("original", "phase4", "typed")
            }
            for f in as_completed(jobs):
                i, m = jobs[f]
                t = f.result()
                t.metadata.update(generator_mode=m, cohort="exploratory_previous_test")
                path = d / "traces" / f"{i}--{m}.json"
                path.write_text(t.model_dump_json(indent=2) + "\n")
                rows.append(
                    dict(
                        task_id=i,
                        generator=m,
                        status=t.status,
                        termination=t.termination,
                        metrics=t.metrics.model_dump(),
                        proof=t.proof,
                        verification=t.verification.model_dump(),
                        trace=path.name if path.suffix == ".gz" else path.name + ".gz",
                        root_selected=t.retrievals[0]["selected"] if t.retrievals else [],
                    )
                )
                print(i, m, t.status, t.metrics.attempted_candidates, flush=True)
    if len(rows) != 12:
        raise ValueError("Incomplete matched diagnosis")
    references = []
    for i in ids:
        for mode in ("original", "extended"):
            path = (
                ROOT / f"experiments/phase4/evaluation-v1/traces/{i}--best_first--r0.json.gz"
                if mode == "original"
                else ROOT / f"experiments/phase4/generator-v1/traces/{i}--{mode}.json.gz"
            )
            t = read_json(path)
            references.append(
                dict(
                    task_id=i,
                    role="historical_" + mode,
                    file=str(path.relative_to(ROOT)),
                    sha256=digest(path),
                    status=t["status"],
                    termination=t["termination"],
                    metrics=t["metrics"],
                    proof=t["proof"],
                )
            )
        for mode in ("automation", "grind"):
            path = ROOT / f"experiments/phase4/evaluation-v1/traces/{i}--{mode}--r0.json.gz"
            t = read_json(path)
            references.append(
                dict(
                    task_id=i,
                    role="historical_" + mode,
                    file=str(path.relative_to(ROOT)),
                    sha256=digest(path),
                    status=t["status"],
                    termination=t["termination"],
                    metrics=t["metrics"],
                    proof=t["proof"],
                )
            )
    (d / "summary.json").write_text(
        json.dumps(
            dict(
                metadata=metadata(),
                cohort="Exploratory Phase 4; never fresh evaluation or training",
                matched=rows,
                historical=references,
            ),
            indent=2,
        )
        + "\n"
    )
    compact(d)


if __name__ == "__main__":
    main()
