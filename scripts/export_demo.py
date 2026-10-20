"""Package authentic recorded runs for an entirely static, offline-capable demo."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    destination = ROOT / "web/public"
    (destination / "traces").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "benchmarks/tasks.json", destination / "tasks.json")
    shutil.copy2(args.experiment / "summary.json", destination / "summary.json")
    manifest = []
    for path in sorted((args.experiment / "traces").glob("*.json")):
        data = json.loads(path.read_text())
        if data["algorithm"] == "automation":
            continue
        shutil.copy2(path, destination / "traces" / path.name)
        manifest.append(
            {
                "task_id": data["task"]["id"],
                "algorithm": data["algorithm"],
                "status": data["status"],
                "file": path.name,
            }
        )
    (destination / "traces/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Exported {len(manifest)} authentic runs")


if __name__ == "__main__":
    main()
