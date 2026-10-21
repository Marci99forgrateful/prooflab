"""Phase 6 development-only counterfactual collection and reproducible CPU fitting."""

import argparse
import json
from pathlib import Path

from prooflab.adaptive_fit import fit_selector, train
from prooflab.adaptive_model import MODELS
from prooflab.adaptive_training import DATA, collect
from prooflab.phase6_counterfactuals import collect as collect_selector


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("collect", "fit", "collect-selector", "fit-selector"))
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--output", type=Path, default=MODELS)
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    if a.action == "collect":
        collect(a.data, a.resume)
    elif a.action == "collect-selector":
        collect_selector()
    elif a.action == "fit-selector":
        print(json.dumps(fit_selector(output=a.output), indent=2))
    else:
        print(json.dumps(train(a.data, a.output), indent=2))


if __name__ == "__main__":
    main()
