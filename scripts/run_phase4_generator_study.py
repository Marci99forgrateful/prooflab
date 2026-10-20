"""Separate general-purpose candidate/lemma arm; never primary ML evidence."""

import json
from concurrent.futures import ThreadPoolExecutor

from prooflab.generator_study import extended_candidates
from prooflab.lean import ROOT
from prooflab.models import Budget, Task, Trace
from prooflab.phase4_data import DIRECTORY, read_tasks
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.search import metadata, search


def main():
    directory = ROOT / "experiments/phase4/generator-v1"
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "traces").mkdir()
    failures = read_json(ROOT / "experiments/phase4/failures-v1/index.json")["results"]
    old = [Task.model_validate(r["task"]) for r in failures]
    tasks = [*old, *read_tasks()]
    protocol = read_json(DIRECTORY / "protocol.json")
    budget = Budget.model_validate(protocol["budget"])
    originals = {}
    for path in trace_paths(ROOT / "experiments/phase4/evaluation-v1/traces"):
        if "--best_first--r0" in path.name:
            trace = Trace.model_validate(read_json(path))
            originals[trace.task.id] = dict(
                source=str(path.relative_to(ROOT)),
                status=trace.status,
                metrics=trace.metrics.model_dump(),
            )

    def work(task):
        if task.id not in originals:
            original = search(task, "best_first", budget)
            (directory / "traces" / f"{task.id}--original.json").write_text(
                original.model_dump_json(indent=2) + "\n"
            )
            originals[task.id] = dict(status=original.status, metrics=original.metrics.model_dump())
        extended = search(task, "best_first", budget, generator=extended_candidates)
        (directory / "traces" / f"{task.id}--extended.json").write_text(
            extended.model_dump_json(indent=2) + "\n"
        )
        print(
            task.id,
            originals[task.id]["status"],
            extended.status,
            extended.metrics.attempted_candidates,
            flush=True,
        )
        return task.id, dict(
            cohort="exploratory_previous_test"
            if task.id.startswith("p3_")
            else "separate_new_test_generator_arm",
            original=originals[task.id],
            extended=dict(
                status=extended.status,
                termination=extended.termination,
                metrics=extended.metrics.model_dump(),
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = dict(pool.map(work, tasks))
    (directory / "summary.json").write_text(
        json.dumps(
            dict(
                metadata=metadata(),
                budget=budget.model_dump(),
                per_theorem=rows,
                caveat=(
                    "Different candidates, unchanged handcrafted scheduling. "
                    "simp_all internal work is not primitive candidate effort. "
                    "This exploratory arm never selects models; no gains attributed to ML."
                ),
            ),
            indent=2,
        )
        + "\n"
    )
    compact(directory)


if __name__ == "__main__":
    main()
