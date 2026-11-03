"""Export actual verified Phase 7 proof sources, never per-task answer templates."""

from __future__ import annotations

from prooflab.lean import ROOT
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.phase7_data import save
from prooflab.phase7_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def main() -> None:
    summary = read_json(EXPERIMENT / "summary.json")
    selected = []
    seen = set()
    for row in summary["per_run"]:
        if not row["verified"] or row["arm"] not in ("conservative", "joint", "completion"):
            continue
        trace = Trace.model_validate(read_json(EXPERIMENT / row["file"]))
        if trace.task.domain in seen:
            continue
        seen.add(trace.task.domain)
        target = ROOT / "examples/phase7" / f"{trace.task.id}--{row['arm']}.lean"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(trace.lean_source or "")
        selected.append(
            dict(
                task_id=trace.task.id,
                arm=row["arm"],
                file=str(target.relative_to(ROOT)),
                source_trace=row["file"],
                trace_sha256=digest(EXPERIMENT / row["file"]),
                source_sha256=trace.verification.source_sha256,
                verification=trace.verification.model_dump(),
            )
        )
    save(ROOT / "examples/phase7/manifest.json", selected)
    print("Exported", len(selected), "independently audited examples across", sorted(seen))


if __name__ == "__main__":
    main()
