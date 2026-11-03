"""Reproduce Phase 7 without altering historical evidence: python -m prooflab.phase7."""

from __future__ import annotations

import argparse
from pathlib import Path

from prooflab.budget_policy import MODEL_DIR
from prooflab.phase7_data import DATA, collect
from prooflab.phase7_evaluation import EXPERIMENT, freeze_execution, run
from prooflab.phase7_training import fit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "fit", "freeze", "evaluate"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "collect":
        collect(args.output or DATA, args.resume)
    elif args.command == "fit":
        fit(args.output or MODEL_DIR, args.data)
        fit(args.output or MODEL_DIR, args.data, root_only=True)
    elif args.command == "freeze":
        freeze_execution()
    else:
        run(args.output or EXPERIMENT, args.resume)


if __name__ == "__main__":
    main()
