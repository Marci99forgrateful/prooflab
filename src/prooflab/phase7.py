"""Reproduce Phase 7 without altering historical evidence: python -m prooflab.phase7."""

from __future__ import annotations

import argparse
from pathlib import Path

from prooflab.budget_policy import MODEL_DIR
from prooflab.models import Budget
from prooflab.phase7_data import DATA, collect, protocol, save, tasks
from prooflab.phase7_evaluation import EXPERIMENT, execute_task, freeze_execution, run
from prooflab.phase7_training import fit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect", "fit", "freeze", "evaluate", "search"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--task")
    parser.add_argument("--policy", choices=protocol()["arms"], default="conservative")
    args = parser.parse_args()
    if args.command == "collect":
        collect(args.output or DATA, args.resume)
    elif args.command == "fit":
        fit(args.output or MODEL_DIR, args.data)
        fit(args.output or MODEL_DIR, args.data, root_only=True)
    elif args.command == "freeze":
        freeze_execution()
    elif args.command == "search":
        task = next((t for t in tasks("evaluation") if t.id == args.task), None)
        if task is None:
            parser.error("--task must name a registered Phase 7 evaluation statement")
        if args.output is not None and args.output.exists():
            parser.error("Refusing to overwrite an existing research output")
        trace = execute_task(
            task, args.policy, Budget.model_validate(protocol()["evaluation_budget"])
        )
        if args.output:
            save(args.output, trace.model_dump())
        import json

        print(
            json.dumps(
                {
                    "status": trace.status,
                    "proof": trace.proof,
                    "verification": trace.verification.model_dump(),
                    "metrics": trace.metrics.model_dump(),
                },
                indent=2,
            )
        )
        if not trace.verification.verified:
            raise SystemExit(2)
    else:
        run(args.output or EXPERIMENT, args.resume)


if __name__ == "__main__":
    main()
