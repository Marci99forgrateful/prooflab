"""Export real Phase 2 repeats without changing Phase 1 replay assets."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    destination = ROOT / "web/public/phase2"
    (destination / "traces").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "benchmarks/phase2/evaluation.json", destination / "tasks.json")
    shutil.copy2(args.experiment / "summary.json", destination / "summary.json")
    shutil.copy2(ROOT / "models/phase2/ranker.json", destination / "model.json")
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
                "repeat": int(data["metadata"]["repeat"]),
                "status": data["status"],
                "url": f"phase2/traces/{path.name}",
            }
        )
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Exported {len(manifest)} actual search traces; native Aesop stays in measured summary")


if __name__ == "__main__":
    main()
