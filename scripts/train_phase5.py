"""Reproducible Phase 5 development collection and CPU fitting."""

import argparse
import json
from pathlib import Path

from prooflab.retrieval_training import DATA, MODELS, collect, train


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("collect", "fit"))
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--output", type=Path, default=MODELS)
    a = p.parse_args()
    if a.action == "collect":
        collect(a.data)
    else:
        print(json.dumps(train(a.data, a.output), indent=2))


if __name__ == "__main__":
    main()
