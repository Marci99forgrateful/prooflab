"""Freeze execution, run the immutable matrix, or rebuild reports from saved traces."""

import argparse
from pathlib import Path

from prooflab.phase5_evaluation import EXPERIMENT, finalize, freeze_execution, run


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("freeze", "run", "finalize"))
    p.add_argument("--output", type=Path, default=EXPERIMENT)
    a = p.parse_args()
    if a.action == "freeze":
        freeze_execution()
    else:
        {"run": run, "finalize": finalize}[a.action](a.output)


if __name__ == "__main__":
    main()
