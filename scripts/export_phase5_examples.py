"""Export actual audited search proofs, retaining generator/reference identities."""

from __future__ import annotations

import json

from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.research_io import read_json

EXAMPLES = [
    ("p5_compose_terminal", "typed_p3"),
    ("p5_product_graph", "learned_p3"),
    ("p5_conjugate_identity", "typed_hand"),
    ("p5_relation_middle", "learned_p3"),
    ("p5_exclusion_transport", "phase4_p3"),
]


def main() -> None:
    output = ROOT / "examples/phase5"
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for task, arm in EXAMPLES:
        trace_path = ROOT / f"experiments/phase5/evaluation-v1/traces/{task}--{arm}--r0.json.gz"
        trace = read_json(trace_path)
        if not trace["verification"]["verified"] or trace["status"] != "verified":
            raise ValueError("Requested genuine proof is unavailable")
        source = trace["lean_source"]
        target = output / f"{task}--{arm}.lean"
        target.write_text(
            f"-- Actual frozen execution: {task}, {arm}, repetition 0.\n"
            f"-- Source trace: {trace_path.relative_to(ROOT)}\n" + source
        )
        records.append(
            dict(
                task_id=task,
                arm=arm,
                source=str(target.relative_to(ROOT)),
                source_sha256=digest(target),
                trace=str(trace_path.relative_to(ROOT)),
                trace_sha256=digest(trace_path),
                original_audit=trace["verification"],
                proof=trace["proof"],
            )
        )
    (output / "index.json").write_text(json.dumps(records, indent=2) + "\n")
    print("Exported", len(records), "actual proof examples; no invented scripts")


if __name__ == "__main__":
    main()
