from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from prooflab.benchmark import Algorithm, run_benchmark
from prooflab.dataset import get_task, load_tasks
from prooflab.learning import DEFAULT_MODEL, LearnedRanking
from prooflab.models import Budget
from prooflab.outcome import MODELS, OutcomeRanking
from prooflab.search import search


def main() -> None:
    parser = argparse.ArgumentParser(description="ProofLab — Lean-verified proof search")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tasks", help="List benchmark statements")
    solve = sub.add_parser("search", help="Search a repository-owned theorem")
    solve.add_argument("task")
    solve.add_argument(
        "--algorithm",
        choices=[
            "bfs",
            "best_first",
            "learned",
            "outcome",
            "automation",
            "applicability_only",
            "old_features_outcome",
        ],
        default="best_first",
    )
    solve.add_argument("--output", type=Path)
    solve.add_argument("--model", type=Path, help="Local JSON weights for learned search")
    benchmark = sub.add_parser("benchmark", help="Run real comparative experiments")
    benchmark.add_argument("--output", type=Path, required=True)
    benchmark.add_argument("--split", choices=["all", "development", "held_out"], default="all")
    benchmark.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    for command in (solve, benchmark):
        command.add_argument("--timeout", type=float, default=15)
        command.add_argument("--depth", type=int, default=7)
        command.add_argument("--expansions", type=int, default=60)
        command.add_argument("--attempts", type=int, default=400)
    serve = sub.add_parser("serve", help="Start the loopback-only research application")
    serve.add_argument("--port", type=int, default=8000)
    collect = sub.add_parser(
        "collect-training", help="Replay permitted development evidence in Lean"
    )
    collect.add_argument("--output", type=Path, required=True, help="New evidence directory")
    train_parser = sub.add_parser(
        "train", help="Select and refit the deterministic CPU ranking model"
    )
    train_parser.add_argument("--data", type=Path)
    train_parser.add_argument("--output", type=Path, default=DEFAULT_MODEL)
    evaluate = sub.add_parser("evaluate-phase2", help="Run the frozen Phase 2 protocol")
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    collect3 = sub.add_parser(
        "collect-continuations", help="Explore valid development alternatives"
    )
    collect3.add_argument("--output", type=Path, required=True)
    train3 = sub.add_parser("train-outcome", help="Train outcome model and controlled ablations")
    train3.add_argument("--data", type=Path)
    train3.add_argument("--output", type=Path, required=True)
    evaluate3 = sub.add_parser("evaluate-phase3", help="Run frozen Phase 3 controlled evaluation")
    evaluate3.add_argument("--output", type=Path, required=True)
    compact_parser = sub.add_parser("compact-traces", help="Losslessly archive actual JSON traces")
    compact_parser.add_argument("--experiment", type=Path, required=True)
    unpack_parser = sub.add_parser("unpack-traces", help="Restore exact original trace bytes")
    unpack_parser.add_argument("--experiment", type=Path, required=True)
    unpack_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "tasks":
        print(json.dumps([t.model_dump() for t in load_tasks()], indent=2, ensure_ascii=False))
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("prooflab.server:app", host="127.0.0.1", port=args.port)
    elif args.command == "collect-training":
        from prooflab.training import collect_data

        collect_data(args.output)
    elif args.command == "train":
        from prooflab.training import DATA_DIR, train

        train(args.data or DATA_DIR, args.output)
    elif args.command == "evaluate-phase2":
        from prooflab.evaluation import run_evaluation

        run_evaluation(args.output, args.model)
    elif args.command == "compact-traces":
        from prooflab.research_io import compact

        compact(args.experiment)
    elif args.command == "unpack-traces":
        from prooflab.research_io import unpack

        unpack(args.experiment, args.output)
    elif args.command == "collect-continuations":
        from prooflab.continuations import collect as collect_continuations

        collect_continuations(args.output)
    elif args.command == "train-outcome":
        from prooflab.continuations import DATA
        from prooflab.outcome_training import train as train_outcome

        train_outcome(args.data or DATA, args.output)
    elif args.command == "evaluate-phase3":
        from prooflab.phase3_evaluation import run

        run(args.output)
    else:
        budget = Budget(
            timeout_s=args.timeout,
            max_depth=args.depth,
            max_expansions=args.expansions,
            max_attempts=args.attempts,
        )
        if args.command == "search":
            is_outcome = args.algorithm in ("outcome", "applicability_only", "old_features_outcome")
            outcome = (
                OutcomeRanking(args.model or MODELS / f"{args.algorithm}.json")
                if is_outcome
                else None
            )
            ranker = LearnedRanking(args.model) if args.model and not is_outcome else None
            result = search(
                get_task(args.task),
                cast(Algorithm, args.algorithm),
                budget,
                ranking=outcome if is_outcome else ranker if args.algorithm == "learned" else None,
                comparison_ranker=ranker,
            )
            data = result.model_dump_json(indent=2)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(data + "\n")
            print(data)
            if result.status != "verified":
                raise SystemExit(2)
        elif args.command == "benchmark":
            print(
                json.dumps(run_benchmark(args.output, budget, args.split, args.workers), indent=2)
            )


if __name__ == "__main__":
    main()
