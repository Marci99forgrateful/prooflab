"""Post-evaluation exact-prefix diagnostics, without modifying frozen algorithms."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from prooflab.models import Trace
from prooflab.phase6_evaluation import EXPERIMENT
from prooflab.research_io import read_json


def prefixes(trace: Trace) -> dict[int, tuple[str, ...]]:
    result: dict[int, tuple[str, ...]] = {0: ()}
    for node in trace.nodes[1:]:
        if node.parent is not None and node.tactic:
            result[node.id] = (*result[node.parent], node.tactic)
    return result


def compare_queries(left: Trace, right: Trace) -> dict[str, Any]:
    lp, rp = prefixes(left), prefixes(right)
    lq = {lp[q["node_id"]]: q for q in left.retrievals}
    rq = {rp[q["node_id"]]: q for q in right.retrievals}
    lr = {r.node_id: r for r in left.rankings}
    rr = {r.node_id: r for r in right.rankings}
    counts = Counter()
    changes = []
    for prefix in sorted(lq.keys() & rq.keys()):
        a, b = lq[prefix], rq[prefix]
        sa, sb = set(a["selected"]), set(b["selected"])
        counts["matched_prefixes"] += 1
        counts["same_membership"] += sa == sb
        ar = lr.get(a["node_id"])
        br = rr.get(b["node_id"])
        ao = [c.tactic for c in ar.candidates] if ar else []
        bo = [c.tactic for c in br.candidates] if br else []
        shared = sa & sb
        arel = [t for t in ao if t in shared]
        brel = [t for t in bo if t in shared]
        counts["shared_relative_order_differs"] += arel != brel
        if sa == sb:
            counts["same_pool_execution_order_differs"] += ao != bo
        if sa != sb or a.get("decision") != b.get("decision"):
            changes.append(
                dict(
                    prefix=list(prefix),
                    left_node=a["node_id"],
                    right_node=b["node_id"],
                    left_decision=a.get("decision"),
                    right_decision=b.get("decision"),
                    left_only=sorted(sa - sb),
                    right_only=sorted(sb - sa),
                    left_selected=sorted(sa),
                    right_selected=sorted(sb),
                    left_allocation=a.get("allocation"),
                    right_allocation=b.get("allocation"),
                )
            )
    return dict(counts=dict(counts), changes=changes)


def main() -> None:
    summary = read_json(EXPERIMENT / "summary.json")
    indexed = {(r["task_id"], r["arm"]): r for r in summary["per_theorem"]}
    result = {}
    mode_choices = {}
    known = summary["comparisons"]
    for name in (
        "learned minus phase4",
        "deterministic minus phase4",
        "learned minus deterministic",
        "deterministic minus no_synthesis",
        "staged minus deterministic",
        "phase4_canonical minus phase4",
    ):
        contrast = known[name]
        a, b = name.split(" minus ")
        cases = []
        audit = Counter()
        common = contrast["common_verified"]["attempted_candidates"]["differences"]
        effort_cases = [
            i for i, v in sorted(common.items(), key=lambda item: -abs(item[1]))[:4] if v
        ]
        chosen = sorted(set(contrast["gains"] + contrast["losses"] + effort_cases))
        for ident in sorted({i for i, arm in indexed if arm == a}):
            la, rb = indexed[(ident, a)], indexed[(ident, b)]
            count = min(la["repetitions"], rb["repetitions"])
            for repeat in range(count):
                left = Trace.model_validate(
                    read_json(EXPERIMENT / "traces" / la["trace_files"][repeat])
                )
                right = Trace.model_validate(
                    read_json(EXPERIMENT / "traces" / rb["trace_files"][repeat])
                )
                matched = compare_queries(left, right)
                audit.update(matched["counts"])
                if a in ("learned", "deterministic"):
                    for t in (left,):
                        key = t.metadata["arm"]
                        mode_choices.setdefault(key, Counter())
                        for q in t.retrievals:
                            mode_choices[key][q.get("decision", "historical")] += 1
                if ident in chosen:
                    cases.append(
                        dict(
                            task_id=ident,
                            repeat=repeat,
                            family=la["family"],
                            left=dict(
                                status=left.status,
                                termination=left.termination,
                                attempts=left.metrics.attempted_candidates,
                                proof=left.proof,
                                verification=left.verification.model_dump(),
                                trace_file=la["trace_files"][repeat],
                            ),
                            right=dict(
                                status=right.status,
                                termination=right.termination,
                                attempts=right.metrics.attempted_candidates,
                                proof=right.proof,
                                verification=right.verification.model_dump(),
                                trace_file=rb["trace_files"][repeat],
                            ),
                            matched=matched,
                        )
                    )
        result[name] = dict(
            gains=contrast["gains"],
            losses=contrast["losses"],
            matched_prefix_counts=dict(audit),
            case_studies=cases,
        )
    # Root decisions are observed, and each run counts once here.
    roots = []
    for row in summary["per_theorem"]:
        if row["arm"] not in ("learned", "deterministic", "staged"):
            continue
        for path in row["trace_files"]:
            t = Trace.model_validate(read_json(EXPERIMENT / "traces" / path))
            q = t.retrievals[0] if t.retrievals else None
            roots.append(
                dict(
                    task_id=t.task.id,
                    arm=row["arm"],
                    family=row["family"],
                    trace_file=path,
                    decision=q.get("decision") if q else None,
                    predicted_log_costs=q.get("predicted_log_costs") if q else None,
                    verified=t.verification.verified,
                    attempts=t.metrics.attempted_candidates,
                )
            )
    payload = dict(
        case_studies=result,
        root_decisions=roots,
        mode_choice_counts_scope=(
            "Use summary results.observations for unique expansion counts; "
            "comparison case lists can repeat a run."
        ),
        limits=(
            "Post-hoc inspection only, no algorithm/model changes. Matched exact "
            "tactic prefixes do not label unobserved actions or infer universal "
            "mathematical impossibility. Root strategy predictions are "
            "success-conditioned fixed-mode costs, not adaptive rollout guarantees."
        ),
    )
    (EXPERIMENT / "analysis.json").write_text(json.dumps(payload, indent=2) + "\n")
    print({n: dict(gains=len(v["gains"]), losses=len(v["losses"])) for n, v in result.items()})


if __name__ == "__main__":
    main()
