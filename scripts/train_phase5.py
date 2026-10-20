"""Reproducible Phase 5 development collection and CPU fitting."""

import argparse
import json
from prooflab.retrieval_training import collect, train


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("collect", "fit"))
    a = p.parse_args()
    if a.action == "collect":
        collect()
    else:
        print(json.dumps(train(), indent=2))


if __name__ == "__main__":
    main()
