"""Recreate reports from complete original execution traces without rerunning Lean.

Also supports recovering reporting after interruption: all expected executions and
frozen provenance must exist. Refuses incomplete/duplicate experiment matrices.
"""

import argparse
import csv
import json
from pathlib import Path

from prooflab.evaluation import METRICS
from prooflab.lean import ROOT
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.phase4_data import DIRECTORY, check_freeze
from prooflab.phase4_evaluation import extra_metrics, report
from prooflab.research_io import compact, read_json, trace_paths


def finalize(directory: Path):
    check_freeze()
    protocol = json.loads((DIRECTORY / "protocol.json").read_text())
    provenance = read_json(directory / "provenance.json")
    if provenance["protocol_sha256"] != digest(DIRECTORY / "protocol.json"):
        raise ValueError("Experiment protocol changed")
    traces = [Trace.model_validate(read_json(p)) for p in trace_paths(directory / "traces")]
    actual = [(t.task.id, t.algorithm, int(t.metadata["repeat"])) for t in traces]
    expected = {
        (t["id"], a, r)
        for t in json.loads((DIRECTORY / "evaluation.json").read_text())
        for a in protocol["algorithms"]
        for r in range(protocol["repetitions"])
    }
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Incomplete or duplicate execution matrix")
    traces.sort(key=lambda t: (t.task.id, t.algorithm, t.metadata["repeat"]))
    families = read_json(DIRECTORY / "families.json")
    result = dict(
        provenance=provenance, **report(traces, {**protocol, "evaluation_families": families})
    )
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    with (directory / "results.csv").open("w", newline="") as out:
        columns = [
            "task",
            "family",
            "algorithm",
            "repeat",
            "status",
            "termination",
            *METRICS,
            *extra_metrics(traces[0]),
        ]
        writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for t in traces:
            writer.writerow(
                dict(
                    task=t.task.id,
                    family=families[t.task.id],
                    algorithm=t.algorithm,
                    repeat=t.metadata["repeat"],
                    status=t.status,
                    termination=t.termination,
                    **{m: getattr(t.metrics, m) for m in METRICS},
                    **extra_metrics(t),
                )
            )
    compact(directory)
    print("Finalized", len(traces), "unaltered native executions")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--experiment", type=Path, default=ROOT / "experiments/phase4/evaluation-v1"
    )
    finalize(parser.parse_args().experiment)
