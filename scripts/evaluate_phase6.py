"""Frozen Phase 6 execution. Refuses incomplete or changed-source evidence."""

import argparse
from pathlib import Path

from prooflab.phase6_evaluation import EXPERIMENT, finalize, freeze_execution, run


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("freeze", "run", "finalize"))
    p.add_argument("--output", type=Path, default=EXPERIMENT)
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    if a.action == "freeze":
        freeze_execution()
    elif a.action == "run":
        run(a.output, a.resume)
    else:
        s = finalize(a.output)
        print(s["runs"], {a: r["verified"] for a, r in s["results"].items()})


if __name__ == "__main__":
    main()
