"""Phase 6 development-only counterfactual collection and reproducible CPU fitting."""

import argparse
import json
from pathlib import Path

from prooflab.adaptive_fit import train
from prooflab.adaptive_model import MODELS
from prooflab.adaptive_training import DATA, collect


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("collect", "fit"))
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--output", type=Path, default=MODELS)
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    if a.action == "collect":
        collect(a.data, a.resume)
    else:
        print(json.dumps(train(a.data, a.output), indent=2))


if __name__ == "__main__":
    main()
