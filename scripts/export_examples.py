"""Export representative discovered proofs; these files are never search inputs."""

import argparse
from pathlib import Path

from prooflab.models import Trace

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = (
    "imp_chain",
    "forall_intro",
    "order_antisymm",
    "chain_three",
    "rewrite_identity",
    "ring_expand",
    "set_inter_monotone",
    "set_union_elim",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    destination = ROOT / "examples/generated"
    destination.mkdir(parents=True, exist_ok=True)
    for ident in EXAMPLES:
        trace = Trace.model_validate_json(
            (args.experiment / "traces" / f"{ident}--best_first.json").read_text()
        )
        if trace.status != "verified" or trace.lean_source is None:
            raise RuntimeError(f"Cannot export unverified example {ident}")
        (destination / f"{ident}.lean").write_text(trace.lean_source)
    (destination / "README.md").write_text(
        "# Discovered Lean proofs\n\n"
        "These are actual, independently audited search outputs from the recorded "
        "best-first run. They are never imported or read by the candidate generator.\n\n"
        "Run each file separately with `lake env lean examples/generated/<name>.lean`. "
        "Each file contains its own `prooflab_result` theorem and transitive axiom audit.\n"
    )
    print(f"Exported {len(EXAMPLES)} genuine proof artifacts")


if __name__ == "__main__":
    main()
