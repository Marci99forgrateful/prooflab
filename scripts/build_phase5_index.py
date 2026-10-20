"""Materialize a bounded native declaration index before the Phase 5 freeze."""

import json
import subprocess
import tempfile
from pathlib import Path

from prooflab.lean import ROOT, lake_command, lean_environment
from prooflab.phase3_data import digest
from prooflab.search import metadata


def main():
    destination = ROOT / "benchmarks/phase5/declarations.json"
    if (destination.parent / "frozen.json").exists():
        raise ValueError("The Phase 5 index is frozen")
    seed = ROOT / "research/phase5/declaration-seeds.txt"
    names = list(dict.fromkeys(seed.read_text().split()))
    with tempfile.TemporaryDirectory(prefix="prooflab-index-") as directory:
        source = Path(directory) / "Index.lean"
        source.write_text(
            "import ProofLab.Retrieval\n#prooflab_declarations "
            + json.dumps(",".join(names))
            + "\n"
        )
        result = subprocess.run(
            [*lake_command(), str(source)],
            cwd=ROOT,
            env=lean_environment(),
            capture_output=True,
            text=True,
            check=True,
        )
    rows = []
    for line in result.stdout.splitlines():
        if "PROOFLAB_INDEX:" in line:
            rows = json.loads(line.split("PROOFLAB_INDEX:", 1)[1])
    good = [r for r in rows if "error" not in r][:128]
    bad = [r for r in rows if "error" in r]
    assert len(good) > 70
    output = dict(
        metadata=metadata(),
        declarations=good,
        unavailable_seeds=bad,
        excluded_after_cap=[r["name"] for r in rows if "error" not in r][128:],
        native_module_sha256=digest(ROOT / "ProofLab/Retrieval.lean"),
        seed_sha256=digest(seed),
        policy="Only explicit general mathematical declarations already imported by the unchanged Bridge. Native types and source modules; no whole-Mathlib import or proof corpus.",
    )
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print("Indexed", len(good), "native declarations; unavailable", [(r["name"]) for r in bad])


if __name__ == "__main__":
    main()
