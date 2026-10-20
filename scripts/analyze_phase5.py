# ruff: noqa: E501
"""Post-freeze analysis of actual candidate outcomes; never feeds model selection."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from typing import Any

from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.phase5_evaluation import EXPERIMENT
from prooflab.research_io import read_json, trace_paths


def main() -> None:
    summary = read_json(EXPERIMENT / "summary-canonical.json")
    families = read_json(ROOT / "benchmarks/phase5/families.json")
    applications: dict[str, Counter[str]] = defaultdict(Counter)
    repeats: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    resource_messages: Counter[str] = Counter()
    selection_records: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = defaultdict(dict)
    for path in trace_paths(EXPERIMENT / "traces"):
        trace = read_json(path)
        arm = trace["metadata"]["arm"]
        repeats[(trace["task"]["id"], arm)].append(
            dict(
                status=trace["status"],
                termination=trace["termination"],
                proof=trace["proof"],
                attempts=trace["metrics"]["attempted_candidates"],
                expanded=trace["metrics"]["expanded_states"],
                wall_s=trace["metrics"]["elapsed_s"],
                file=path.name,
                sha256=digest(path),
            )
        )
        for node in trace["nodes"]:
            error = (node.get("error") or "").lower()
            for word in ("heartbeat", "timeout", "recursion", "memory"):
                resource_messages[word] += int(word in error)
        prefix_by_node: dict[int, tuple[str, ...]] = {0: ()}
        if arm in ("typed_p3", "learned_p3", "typed_hand", "learned_hand"):
            for node in trace["nodes"][1:]:
                prefix_by_node[node["id"]] = (*prefix_by_node[node["parent"]], node["tactic"])
            ranks = {r["node_id"]: r["candidates"] for r in trace["rankings"]}
            for query in trace["retrievals"]:
                key = (
                    trace["task"]["id"],
                    trace["metadata"]["repeat"],
                    prefix_by_node[query["node_id"]],
                )
                ranking = ranks.get(query["node_id"], [])
                selection_records[key][arm] = dict(
                    selected=query["selected"],
                    actual_order=[r["tactic"] for r in ranking],
                    scores={
                        r["tactic"]: r["policy_score"]
                        if r["policy_score"] is not None
                        else r["heuristic_score"]
                        for r in ranking
                    },
                )
        for query in trace["retrievals"]:
            counts = applications[arm]
            counts["expanded_with_pool"] += 1
            counts["selected"] += len(query["selected"])
            counts["entered"] += len(query.get("entered", []))
            counts["displaced"] += len(query.get("displaced", []))
            rows = {r["candidate"]["tactic"]: r for r in query.get("pool", [])}
            for raw in query.get("native", {}).get("rows", []):
                if raw.get("tactic"):
                    rows.setdefault(raw["tactic"], raw)
            children = {n["tactic"]: n for n in trace["nodes"] if n["parent"] == query["node_id"]}
            for tactic in query["selected"]:
                node = children.get(tactic)
                row = rows.get(tactic, {})
                if node:
                    outcome = (
                        "accepted" if node["status"] in ("accepted", "solved") else node["status"]
                    )
                    counts["all_actual_" + outcome] += 1
                    counts["verified_path_actions"] += int(node["on_proof_path"])
                else:
                    outcome = "unexplored"
                    counts["selected_unexplored"] += 1
                if "compatible" in row and row.get("family") != "normalizer":
                    tag = "compatible" if row["compatible"] else "incompatible"
                    counts[tag + "_" + outcome] += 1
                if row.get("family"):
                    counts[row["family"] + "_" + outcome] += 1
    stability = []
    for (task, arm), runs in repeats.items():
        if len(runs) < 2:
            continue
        a, b = runs
        if any(a[n] != b[n] for n in ("status", "termination", "proof", "attempts", "expanded")):
            stability.append(dict(task_id=task, arm=arm, runs=runs))
    rows = {(r["task_id"], r["arm"]): r for r in summary["per_theorem"]}
    case_studies = {}
    comparisons = [
        ("typed_p3", "original_p3"),
        ("learned_p3", "typed_p3"),
        ("phase4_p3", "typed_p3"),
        ("typed_joint", "typed_p3"),
        ("automation", "learned_p3"),
        ("grind", "learned_p3"),
    ]
    for left, right in comparisons:
        good, bad, effort = [], [], []
        for task in sorted(families):
            a, b = rows[(task, left)], rows[(task, right)]
            delta = a["verified"] / a["repetitions"] - b["verified"] / b["repetitions"]
            item = dict(
                task_id=task,
                family=families[task],
                left=a,
                right=b,
                success_difference=delta,
                attempt_difference=statistics.mean(a["attempts"]) - statistics.mean(b["attempts"]),
            )
            if delta > 0:
                good.append(item)
            elif delta < 0:
                bad.append(item)
            elif a["verified"] == a["repetitions"] and b["verified"] == b["repetitions"]:
                effort.append(item)
        case_studies[left + " minus " + right] = dict(
            success_gains=good,
            success_regressions=bad,
            common_verified_effort=sorted(effort, key=lambda r: r["attempt_difference"]),
            selection_note="Post-hoc descriptive examples; no model, generator or budget changes follow them.",
        )
    family_points = {}
    for name, comparison in summary["comparisons"].items():
        for population in ("all_runs", "common_verified"):
            for metric, result in comparison[population].items():
                groups: dict[str, list[float]] = defaultdict(list)
                for task, delta in result["differences"].items():
                    groups[families[task]].append(delta)
                family_points[name + " / " + population + " / " + metric] = dict(
                    theorem_weighted_point=result["mean_difference"],
                    family_balanced_point=statistics.mean(
                        statistics.mean(v) for v in groups.values()
                    )
                    if groups
                    else None,
                    ci95_family_balanced=result["ci95_family"],
                    families=len(groups),
                    note="Equal-family sensitivity differs from the theorem-weighted estimand when common-success family sizes differ; this is not a second interval for the same weighted point.",
                )
    selection_effects = {}
    for symbolic, learned in (("typed_p3", "learned_p3"), ("typed_hand", "learned_hand")):
        counts: Counter[str] = Counter()
        examples = []
        for (task, repeat, prefix), observed in selection_records.items():
            if symbolic not in observed or learned not in observed:
                continue
            a, b = observed[symbolic], observed[learned]
            counts["matched_exact_prefixes"] += 1
            same = set(a["selected"]) == set(b["selected"])
            counts["same_available_set" if same else "different_available_set"] += 1
            counts["different_input_order"] += a["selected"] != b["selected"]
            counts["actual_order_changed_with_same_set"] += (
                same and a["actual_order"] != b["actual_order"]
            )
            counts["shared_action_score_disagreements"] += sum(
                abs(score - b["scores"][tactic]) > 1e-12
                for tactic, score in a["scores"].items()
                if tactic in b["scores"]
            )
            if not same and len(examples) < 20:
                examples.append(
                    dict(
                        task_id=task,
                        repeat=repeat,
                        prefix=list(prefix),
                        learned_entered=sorted(set(b["selected"]) - set(a["selected"])),
                        learned_displaced=sorted(set(a["selected"]) - set(b["selected"])),
                    )
                )
        selection_effects[learned + " minus " + symbolic] = dict(
            counts=dict(counts),
            examples=examples,
            limits="Actual matched exact prefixes only. Retrieval changes selection and generated input order; downstream stable rankings preserve retrieval order among equal action scores. This is not a pure availability-only intervention.",
        )
    stratified: dict[str, Counter[str]] = defaultdict(Counter)
    for record in summary["availability"]["records"]:
        for tactic in record["observed_verified_actions"]:
            family = (
                "broad_simp_all"
                if tactic.startswith("simp_all")
                else "normalization"
                if tactic in ("ring", "omega") or tactic.startswith("simp only")
                else "witness"
                if tactic.startswith("exists ")
                else "structural_or_lemma"
            )
            stratified[record["arm"]][family + "_observed_verified_actions"] += 1
            stratified[record["arm"]][family + "_available"] += tactic in record["available"]
    result = dict(
        summary_sha256=digest(EXPERIMENT / "summary-canonical.json"),
        applications={a: dict(v) for a, v in applications.items()},
        selection_order_intervention=selection_effects,
        stratified_partial_availability={a: dict(v) for a, v in stratified.items()},
        repeat_disagreements=stability,
        native_resource_error_messages=dict(resource_messages),
        case_studies=case_studies,
        family_sensitivity=family_points,
        limits="Conditional observed applicability excludes unexecuted and resource-error actions. Accepted is not useful unless on an audited full path. Family-balanced sensitivity has its own point estimand. No counterfactual correctness labels or final-test tuning.",
    )
    (EXPERIMENT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Analyzed actual outcomes; repeat disagreements:", len(stability))


if __name__ == "__main__":
    main()
