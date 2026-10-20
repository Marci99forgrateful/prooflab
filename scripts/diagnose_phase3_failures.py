"""Exploratory Phase 3 failure replay; never frontier training evidence."""

import json
from concurrent.futures import ThreadPoolExecutor

from prooflab.lean import ROOT, LeanSession, verify
from prooflab.models import Budget, Trace
from prooflab.phase3_data import digest
from prooflab.research_io import compact, read_json, trace_paths
from prooflab.search import metadata, search

root = ROOT
dest = root / "experiments/phase4/failures-v1"
dest.mkdir(exist_ok=False)
(dest / "traces").mkdir()
traces = [
    (p, Trace.model_validate(read_json(p)))
    for p in trace_paths(root / "experiments/phase3/evaluation-v1/traces")
    if "--best_first--r0" in p.name
]
failures = [(p, t) for p, t in traces if t.status != "verified"]


def work(item):
    p, t = item
    high = search(
        t.task,
        "best_first",
        Budget(
            max_depth=14, max_expansions=160, max_attempts=1200, timeout_s=25, tactic_timeout_s=2
        ),
    )
    (dest / "traces" / f"{t.task.id}--extended.json").write_text(
        high.model_dump_json(indent=2) + "\n"
    )
    probes = []
    with LeanSession(t.task, timeout=20) as lean:
        for tactic in ["simp_all", "grind", "aesop"]:
            m = lean.step(lean.initial.state_id, tactic, 4)
            closed = m.get("status") == "accepted" and not m["goals"]
            a = verify(t.task, [tactic], 20) if closed else None
            probes.append(dict(tactic=tactic, response=m, audit=a.model_dump() if a else None))
    result = dict(
        task=t.task.model_dump(),
        source=str(p.relative_to(root)),
        source_sha256=digest(p),
        original_metrics=t.metrics.model_dump(),
        termination=t.termination,
        extended=dict(
            status=high.status, termination=high.termination, metrics=high.metrics.model_dump()
        ),
        probes=probes,
    )
    (dest / f"{t.task.id}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        t.task.id,
        high.status,
        [(r["tactic"], bool(r["audit"] and r["audit"]["verified"])) for r in probes],
        flush=True,
    )
    return result


with ThreadPoolExecutor(max_workers=2) as ex:
    results = list(ex.map(work, failures))
(dest / "index.json").write_text(
    json.dumps(
        dict(
            metadata=metadata(),
            purpose="exploratory Phase 3 failures; NEVER training or new final-test evidence",
            results=results,
        ),
        indent=2,
    )
    + "\n"
)
compact(dest)
