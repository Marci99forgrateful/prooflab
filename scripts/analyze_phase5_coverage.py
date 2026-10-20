"""Observed versus inferred Phase 4 diagnosis, built from saved native executions."""

from __future__ import annotations

import json

from prooflab.lean import ROOT
from prooflab.models import Trace
from prooflab.phase3_data import digest
from prooflab.research_io import read_json


def prefixes(t: Trace) -> dict[int, tuple[str, ...]]:
    result = {0: ()}
    for n in t.nodes[1:]:
        assert n.parent is not None and n.tactic is not None
        result[n.id] = (*result[n.parent], n.tactic)
    return result


def main():
    d = ROOT / "experiments/phase5/coverage-v1"
    cases = []
    for ident in ["p4_witness_transport", "p4_cubic_pair", "p4_inverse_right", "p4_lattice_meet"]:
        traces = {
            m: Trace.model_validate(read_json(d / "traces" / f"{ident}--{m}.json.gz"))
            for m in ("original", "phase4", "typed")
        }
        reference = next(
            (t for m in ("original", "phase4", "typed") if (t := traces[m]).verification.verified),
            None,
        )
        probe = []
        if reference:
            for mode, t in traces.items():
                p = prefixes(t)
                by_prefix = {p[q["node_id"]]: q for q in t.retrievals}
                for depth, action in enumerate(reference.proof):
                    prefix = tuple(reference.proof[:depth])
                    q = by_prefix.get(prefix)
                    parents = {n.id for n in t.nodes if p[n.id] == prefix and n.state is not None}
                    children = [n for n in t.nodes if n.parent in parents and n.tactic == action]
                    probe.append(
                        dict(
                            mode=mode,
                            prefix=list(prefix),
                            reference_action=action,
                            state_reached=bool(parents),
                            state_expanded=q is not None,
                            action_available=action in q["selected"] if q else None,
                            actual_statuses=[n.status for n in children],
                        )
                    )
        cases.append(
            dict(
                task_id=ident,
                reference_proof=reference.proof if reference else None,
                observed_reference_path_coverage=probe,
                trace_sha256={m: digest(d / "traces" / f"{ident}--{m}.json.gz") for m in traces},
            )
        )
    data = dict(
        cases=cases,
        observations={
            "p4_witness_transport": (
                "Original/expanded exhaust after 6/7 attempts without f a. Typed "
                "native application construction emits f a, yielding an "
                "independently audited three-step proof in 37 attempts. Native "
                "Aesop/grind historical successes are separately linked."
            ),
            "p4_cubic_pair": (
                "Original verifies rw[h],constructor,ring,ring in 386 attempts/26 "
                "expansions. Expanded and typed both exhaust 600 attempts (36/49 "
                "expansions). Root original actions are not displaced in typed. "
                "Additional rewrite/generic-logic branches and ordering change "
                "exploration; no evidence that the baseline proof becomes "
                "mathematically invalid."
            ),
            "p4_inverse_right": (
                "Typed bounded noncommutative group normalization plus assumption "
                "verifies in 22 attempts. Expanded simp_all verifies in 2; "
                "original exhausts 600. This is stronger symbolic coverage, not a "
                "learned scheduling result."
            ),
            "p4_lattice_meet": (
                "Expanded le_trans,inf_le_left,assumption verifies in 13 attempts."
                " Original uses 80 expansions/240 attempts without a proof; typed "
                "exhausts 600/56. The index contains lattice rules but generic "
                "compatible branches and constrained selection do not supply an "
                "efficient successful sequence."
            ),
        },
        interpretations=(
            "Availability gaps are demonstrated by actual candidate pools; "
            "branching/priority contributions are mechanistic interpretations,"
            " not randomized causal attributions. New frozen evaluation "
            "remains separate. No diagnostic theorem trains the model."
        ),
    )
    (d / "analysis.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Analyzed", len(cases), "genuine Phase 4 cases")


if __name__ == "__main__":
    main()
