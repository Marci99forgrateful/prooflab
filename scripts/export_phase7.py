"""Generate ignored web assets from exact canonical Phase 7 execution archives."""

from __future__ import annotations

import shutil
from pathlib import Path

from prooflab.lean import ROOT
from prooflab.phase7_data import DATA, protocol, save, tasks
from prooflab.phase7_evaluation import EXPERIMENT, check_execution
from prooflab.research_io import read_json


def main() -> None:
    check_execution()
    target = ROOT / "web/public/phase7"
    target.mkdir(parents=True, exist_ok=True)
    manifest = []
    for role, directory in [("evaluation", EXPERIMENT), ("development", DATA)]:
        for path in sorted((directory / "traces").glob("*.json.gz")):
            trace = read_json(path)
            metadata = trace["metadata"]
            budget = trace["budget"]
            relative = Path(role) / path.name
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            manifest.append(
                dict(
                    role=role,
                    task_id=trace["task"]["id"],
                    arm=metadata["arm"],
                    source_state=int(metadata.get("source_state", 0)),
                    budget_level=int(metadata.get("budget_level", 0)),
                    attempt_budget=budget["max_attempts"],
                    wall_budget=budget["timeout_s"],
                    status=trace["status"],
                    verified=trace["verification"]["verified"],
                    attempts=trace["metrics"]["attempted_candidates"],
                    wall_s=trace["metrics"]["elapsed_s"],
                    url="phase7/" + relative.as_posix(),
                )
            )
    summary = read_json(EXPERIMENT / "summary.json")
    summary = {k: v for k, v in summary.items() if k != "per_run"}
    save(
        target / "explorer.json",
        dict(
            schema_version=1,
            manifest=manifest,
            tasks=[t.model_dump() for t in tasks("evaluation") + tasks()],
            summary=summary,
            budget=protocol()["evaluation_budget"],
            training=read_json(ROOT / "models/phase7/training-report.json"),
            protocol=protocol(),
            diagnosis=read_json(ROOT / "research/phase7/phase6-diagnosis.json"),
        ),
    )
    print("Exported", len(manifest), "actual Phase 7 executions; no model or result is fabricated.")


if __name__ == "__main__":
    main()
