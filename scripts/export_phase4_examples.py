"""Export actual frozen proof paths and freshly recompile each with axiom audit."""

import json

from prooflab.lean import ROOT, verify
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.research_io import read_json

out = ROOT / "examples/phase4"
out.mkdir(exist_ok=True)
entries = []
for ident, a in [
    ("p4_contra_disj", "best_first"),
    ("p4_cubic_pair", "best_first"),
    ("p4_cubic_pair", "joint"),
    ("p4_partition_nested", "joint"),
    ("p4_witness_exists", "joint"),
]:
    source = ROOT / f"experiments/phase4/evaluation-v1/traces/{ident}--{a}--r0.json.gz"
    t = Trace.model_validate(read_json(source))
    assert t.verification.verified
    path = out / f"{ident}--{a}.lean"
    path.write_text(t.lean_source)
    audit = verify(t.task, t.proof, 30)
    assert audit.verified, audit.error
    entries.append(
        dict(
            file=path.name,
            trace=str(source.relative_to(ROOT)),
            source_sha256=digest(source),
            audit=audit.model_dump(),
        )
    )
(out / "manifest.json").write_text(json.dumps(entries, indent=2) + "\n")
print("Freshly recompiled and axiom-audited", len(entries), "actual exported Lean proofs")
