"""Build-time export from canonical research; no duplicated large Git datasets."""

from __future__ import annotations

import json
import shutil

from prooflab.lean import ROOT
from prooflab.research import bundle, manifest
from prooflab.research_io import read_json, trace_paths


def main() -> None:
    experiment = ROOT / "experiments/phase3/evaluation-v1"
    if not (experiment / "summary.json").exists():
        raise RuntimeError("Complete frozen Phase 3 experiment before exporting its demo")
    destination = ROOT / "web/public/phase3"
    (destination / "data/traces").mkdir(parents=True, exist_ok=True)
    (destination / "data/continuations").mkdir(exist_ok=True)
    for source, target in [
        (ROOT / "benchmarks/phase3/evaluation.json", "tasks.json"),
        (experiment / "summary.json", "summary.json"),
    ]:
        shutil.copy2(source, destination / target)
    traces = []
    for path in trace_paths(experiment / "traces"):
        data = read_json(path)
        # Every original trace remains canonical in experiments; generated assets
        # are faithful minified JSON, not another checked-in copy of large data.
        filename = path.name.removesuffix(".gz")
        target = destination / "data/traces" / filename
        target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
        traces.append(
            {
                "task_id": data["task"]["id"],
                "algorithm": data["algorithm"],
                "repeat": int(data["metadata"]["repeat"]),
                "status": data["status"],
                "url": f"phase3/data/traces/{filename}",
            }
        )
    (destination / "manifest.json").write_text(json.dumps(traces, indent=2) + "\n")
    entries = manifest()
    (destination / "continuations.json").write_text(json.dumps(entries, indent=2) + "\n")
    for role, ident in sorted({(e["role"], e["task_id"]) for e in entries}):
        payload = bundle(role, ident)
        (destination / "data/continuations" / f"{role}--{ident}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
    print(
        f"Exported {len(traces)} actual traces and {len(entries)} continuation states "
        "into ignored build assets"
    )


if __name__ == "__main__":
    main()
