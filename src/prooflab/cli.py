from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from prooflab.benchmark import Algorithm, run_benchmark
from prooflab.dataset import get_task, load_tasks
from prooflab.models import Budget
from prooflab.search import search


def main() -> None:
    parser = argparse.ArgumentParser(description="ProofLab — Lean-verified proof search")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tasks", help="List benchmark statements")
    solve = sub.add_parser("search", help="Search a repository-owned theorem")
    solve.add_argument("task")
    solve.add_argument(
        "--algorithm", choices=["bfs", "best_first", "learned", "automation"], default="best_first"
    )
    solve.add_argument("--output", type=Path)
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
    sub.add_parser("collect-training", help="Replay permitted development evidence in Lean")
    sub.add_parser("train", help="Select and refit the deterministic CPU ranking model")
    evaluate = sub.add_parser("evaluate-phase2", help="Run the frozen Phase 2 protocol")
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "tasks":
        print(json.dumps([t.model_dump() for t in load_tasks()], indent=2, ensure_ascii=False))
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("prooflab.server:app", host="127.0.0.1", port=args.port)
    elif args.command == "collect-training":
        from prooflab.training import collect_data

        collect_data()
    elif args.command == "train":
        from prooflab.training import train

        train()
    elif args.command == "evaluate-phase2":
        from prooflab.evaluation import run_evaluation

        run_evaluation(args.output)
    else:
        budget = Budget(
            timeout_s=args.timeout,
            max_depth=args.depth,
            max_expansions=args.expansions,
            max_attempts=args.attempts,
        )
        if args.command == "search":
            result = search(get_task(args.task), cast(Algorithm, args.algorithm), budget)
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
