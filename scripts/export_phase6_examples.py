"""Export real audited search paths and freshly recheck five genuine examples."""

from __future__ import annotations

import json

from prooflab.lean import ROOT, theorem_source, verify
from prooflab.models import Trace
from prooflab.phase6_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def main() -> None:
    summary = read_json(EXPERIMENT / "summary.json")
    indexed = {(r["task_id"], r["arm"]): r for r in summary["per_theorem"]}
    chosen = []
    for name in (
        "learned minus phase4",
        "deterministic minus phase4",
        "learned minus deterministic",
    ):
        a, b = name.split(" minus ")
        for field, arm in [("gains", a), ("losses", b)]:
            for ident in summary["comparisons"][name][field]:
                if indexed[(ident, arm)]["verified"] and ident not in {i for i, _ in chosen}:
                    chosen.append((ident, arm))
                    break
    for row in summary["per_theorem"]:
        if len(chosen) >= 5:
            break
        if (
            row["arm"] in ("learned", "deterministic", "phase4", "staged")
            and row["verified"]
            and row["task_id"] not in {i for i, _ in chosen}
        ):
            chosen.append((row["task_id"], row["arm"]))
    if len(chosen) < 5:
        raise ValueError("Insufficient actual verified examples; never manufacture a proof")
    directory = ROOT / "examples/phase6"
    directory.mkdir(parents=True, exist_ok=True)
    audits = []
    for ident, arm in chosen[:5]:
        entries = indexed[(ident, arm)]["trace_files"]
        trace = next(
            t
            for name in entries
            if (
                t := Trace.model_validate(read_json(EXPERIMENT / "traces" / name))
            ).verification.verified
        )
        source = theorem_source(trace.task, trace.proof)
        path = directory / f"{ident}--{arm}.lean"
        path.write_text(source)
        audit = verify(trace.task, trace.proof, 30)
        if not audit.verified or audit.source_sha256 != trace.verification.source_sha256:
            raise ValueError("Genuine example failed exact fresh verification")
        audits.append(
            dict(
                task_id=ident,
                arm=arm,
                source=str(path.relative_to(ROOT)),
                trace_files=entries,
                proof=trace.proof,
                verification=audit.model_dump(),
            )
        )
    (ROOT / "artifacts/phase6-example-audits.json").write_text(
        json.dumps(
            dict(
                examples=audits,
                scope=(
                    "Freshly compiled actual complete paths from final experiments, "
                    "independently audited; examples not training"
                ),
            ),
            indent=2,
        )
        + "\n"
    )
    print("Freshly verified", len(audits), "genuine exported examples")


if __name__ == "__main__":
    main()
