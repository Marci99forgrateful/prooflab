"""Refetch the exact pinned, individually hashed research files; no model download.

Usage: python scripts/inspect_phase4_sources.py --output /tmp/prooflab-source-review
The destination must be new. This reconstructs the inspected subset, not whole repos.
"""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    for row in json.loads((root / "research/phase4/sources.json").read_text()):
        if "commit" not in row:
            continue
        for file in row["files"]:
            path = file["path"]
            if ".." in Path(path).parts or Path(path).is_absolute():
                raise ValueError("Unsafe source inventory path")
            url = f"https://raw.githubusercontent.com/{row['repository']}/{row['commit']}/{path}"
            raw = urllib.request.urlopen(url, timeout=40).read()
            if hashlib.sha256(raw).hexdigest() != file["sha256"]:
                raise ValueError("Pinned source hash mismatch")
            target = args.output / row["repository"] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        print(row["repository"], row["commit"], flush=True)


if __name__ == "__main__":
    main()
