# ruff: noqa: E501
# Markdown paragraphs and tables intentionally remain complete prose strings.
"""Read-only scientific analysis/reporting of the frozen Phase 7 experiment."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from typing import Any, cast
from xml.etree import ElementTree as ET

from prooflab.budget_policy import BudgetModel
from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.phase7_data import DATA, DIRECTORY, protocol, save
from prooflab.phase7_evaluation import EXPERIMENT, check_execution
from prooflab.research_io import read_json

NAMES = {
    "phase4": "Phase 4 symbolic",
    "phase6_staged": "Phase 6 staged",
    "phase6_learned": "Phase 6 learned cost",
    "completion": "Phase 7 completion",
    "cost": "Phase 7 cost only",
    "joint": "Phase 7 joint",
    "conservative": "Phase 7 conservative",
    "root_trained": "Phase 7 root-trained",
    "staged": "Phase 7 staged control",
    "automation": "Native Aesop",
    "grind": "Native grind",
}


def prefixes(trace: dict[str, Any]) -> dict[int, tuple[str, ...]]:
    paths = {0: ()}
    for n in trace["nodes"][1:]:
        paths[n["id"]] = (*paths[n["parent"]], n["tactic"])
    return paths


def inspect_pair(task: str, left_arm: str, right_arm: str) -> dict[str, Any]:
    lp = EXPERIMENT / "traces" / f"{task}--{left_arm}.json.gz"
    rp = EXPERIMENT / "traces" / f"{task}--{right_arm}.json.gz"
    left, right = read_json(lp), read_json(rp)
    a, b = prefixes(left), prefixes(right)
    aq = {a[q["node_id"]]: q for q in left["retrievals"]}
    bq = {b[q["node_id"]]: q for q in right["retrievals"]}
    matched = []
    for prefix in sorted(aq.keys() & bq.keys()):
        x, y = aq[prefix], bq[prefix]
        if x.get("decision") != y.get("decision") or set(x.get("selected", [])) != set(
            y.get("selected", [])
        ):
            matched.append(
                dict(
                    prefix=prefix,
                    left_decision=x.get("decision"),
                    right_decision=y.get("decision"),
                    predictions=x.get("predictions"),
                    reason=x.get("decision_reason"),
                    left_only=sorted(set(x.get("selected", [])) - set(y.get("selected", []))),
                    right_only=sorted(set(y.get("selected", [])) - set(x.get("selected", []))),
                )
            )
    observed_path = []
    if right["verification"]["verified"]:
        for depth, tactic in enumerate(right["proof"]):
            prefix = tuple(right["proof"][:depth])
            query = aq.get(prefix)
            observed_path.append(
                dict(
                    prefix=prefix,
                    tactic=tactic,
                    expanded=query is not None,
                    selected=tactic in query["selected"] if query else None,
                )
            )
    return dict(
        task_id=task,
        left_arm=left_arm,
        right_arm=right_arm,
        left_status=left["status"],
        right_status=right["status"],
        left_termination=left["termination"],
        right_termination=right["termination"],
        left_proof=left["proof"] if left["verification"]["verified"] else [],
        right_proof=right["proof"] if right["verification"]["verified"] else [],
        left_attempts=left["metrics"]["attempted_candidates"],
        right_attempts=right["metrics"]["attempted_candidates"],
        matched_changes=matched,
        witnessed_right_path_in_left=observed_path,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in (lp, rp)},
    )


def calibration() -> dict[str, Any]:
    model = BudgetModel()
    rows = cast(list[dict[str, Any]], read_json(DATA / "rows.json.gz"))
    selected = [
        r
        for r in rows
        if r["task_id"] in model.artifact["validation_ids"]
        and r["completion"] is not None
        and r["features"]
    ]
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    bins: dict[int, list[tuple[float, float]]] = defaultdict(list)
    costs = []
    for row in selected:
        pred = model.predictions(row["features"])[row["mode"]]
        p, y = pred["completion_probability"], float(row["completion"])
        for key in (
            "all",
            "root" if row["source_state"] == 0 else "intermediate",
            "budget_" + str(row["budget_level"]),
        ):
            groups[key].append((p, y))
        bins[min(4, int(p * 5))].append((p, y))
        if row["completion"] == 1:
            costs.append(abs(pred["conditional_attempts"] - row["conditional_attempts"]))
    paired: dict[tuple[str, int, str], list[tuple[int, float]]] = defaultdict(list)
    for row in selected:
        p = model.predictions(row["features"])[row["mode"]]["completion_probability"]
        paired[(row["task_id"], row["source_state"], row["mode"])].append((row["budget_level"], p))
    monotone_pairs = [sorted(v) for v in paired.values() if len(v) == 2]
    return dict(
        validation_rows=len(selected),
        paired_budget_comparisons=len(monotone_pairs),
        budget_monotonicity_violations=sum(v[1][1] + 1e-9 < v[0][1] for v in monotone_pairs),
        brier={k: statistics.mean((p - y) ** 2 for p, y in v) for k, v in groups.items()},
        empirical_bins={
            str(k): dict(
                n=len(v),
                mean_prediction=statistics.mean(p for p, y in v),
                observed_completion=statistics.mean(y for p, y in v),
            )
            for k, v in bins.items()
        },
        conditional_attempt_mae=statistics.mean(costs) if costs else None,
        limit="Validation only; no test-counterfactual calibration is inferred from adaptively selected final trajectories.",
    )


def policy_activity(summary: dict[str, Any]) -> dict[str, Any]:
    activity = {}
    for arm in ("completion", "cost", "joint", "conservative", "root_trained"):
        totals = Counter()
        choices = Counter()
        for row in (r for r in summary["per_run"] if r["arm"] == arm):
            trace = read_json(EXPERIMENT / row["file"])
            staged = read_json(EXPERIMENT / "traces" / f"{row['task_id']}--staged.json.gz")
            paths, staged_paths = prefixes(trace), prefixes(staged)
            own_queries = {paths[q["node_id"]]: q for q in trace["retrievals"]}
            base_queries = {staged_paths[q["node_id"]]: q for q in staged["retrievals"]}
            for q in trace["retrievals"]:
                choices[q["decision"]] += 1
                totals["decisions"] += 1
                totals["departures_from_staged"] += q["decision"] != q["baseline_decision"]
            for prefix in own_queries.keys() & base_queries.keys():
                totals["matched_prefixes"] += 1
                totals["changed_selected_pools"] += set(own_queries[prefix]["selected"]) != set(
                    base_queries[prefix]["selected"]
                )
            attempts = [(paths[n["id"]], n["status"]) for n in trace["nodes"][1:]]
            baseline_attempts = [(staged_paths[n["id"]], n["status"]) for n in staged["nodes"][1:]]
            totals["identical_full_attempt_sequences"] += attempts == baseline_attempts
        activity[arm] = dict(**totals, choices=dict(choices))
    return activity


def main() -> None:
    frozen = check_execution()
    summary = read_json(EXPERIMENT / "summary.json")
    training = read_json(ROOT / "models/phase7/training-report.json")
    manifest = read_json(DATA / "manifest.json")
    comparisons = summary["comparisons"]
    primary = comparisons["conservative minus phase6_staged"]
    cases = []
    for a, b in [
        ("conservative", "phase6_staged"),
        ("joint", "phase6_staged"),
        ("conservative", "staged"),
        ("conservative", "root_trained"),
    ]:
        c = comparisons[a + " minus " + b]
        cases.extend(inspect_pair(t, a, b) for t in c["gains"] + c["regressions"])
    cal = calibration()
    activity = policy_activity(summary)
    save(
        EXPERIMENT / "analysis.json",
        dict(
            calibration=cal,
            policy_activity=activity,
            cases=cases,
            diagnostic_only=True,
            no_retuning=True,
        ),
    )
    robust = primary["theorem_interval"]["lower"] > 0 and primary["family_interval"]["lower"] > 0
    finding = (
        "The registered conservative policy improves verified success on this finite benchmark with both descriptive intervals above zero."
        if robust
        else "No robust improvement over the strongest prior staged algorithm is established by this registered experiment."
    )
    lines = [
        "# ProofLab v0.7.0 — Budget-Aware Policy Learning",
        "",
        finding,
        "",
        "This is an implemented CPU learning/search study with native Lean continuations, frozen new mathematical evaluation, preserved negative outcomes and an integrated Policy Learning Explorer. It is a review candidate based on Phase 6 commit `a8af9eb8698819d07bb10f7f1bacd855f9b1213a`; no automatic merge, MathVerify change, paid AI service or GPU is part of the work.",
        "",
        "## What changed",
        "",
        "A trained completion classifier now learns whether a fixed expert independently finishes a proof within a stated resource budget. A separate success-conditional cost regressor estimates attempts on successful continuations. Completion-only, cost-only, joint and conservative policies share an explicitly metered native frontier. The conservative policy must earn a development-selected probability margin before leaving the deterministic staged fallback. A root-trained ablation and staged engine control separate learning/data effects from the runner.",
        "",
        "The previous Phase 6 sources, models and all original research artifacts remain byte-identical. Reading the original repeat-zero traces reproduces 22/48 for its conditional-cost learner and 30/48 for staged hybrid. Those are a different historical dataset: the table below measures every prior algorithm afresh on the new 48 statements. Historical evaluation supplies diagnosis only, never new training labels.",
        "",
        "## Data and executable boundaries",
        "",
        "The frozen input has 64 development statements in sixteen families and 48 new evaluation statements in twelve families. Thirty-two development statements are explicitly recollected from permitted Phase 6 development; thirty-two are new. Native typed-expression graph checks elaborate every statement and reject alpha/binder-permutation duplicates against historical data and across the new split. Four whole development families are validation-only. The evaluation data/protocol were committed before model selection; exact models/execution were frozen before any final search.",
        "",
        f"The recorded collection contains **{manifest['rows']} actual matched continuation runs** plus {len(manifest['sources'])} staged source searches: {manifest['verified']} independently verified completions, {manifest['bounded_noncompletion']} observed bounded noncompletions and {manifest['missing']} missing/error labels. Root and available intermediate states are restored by actual tactic-prefix replay. Every expert receives the same registered budget at a source state; source selection does not require source success.",
        "",
        f"Training uses {training['training_rows']} rows, including {training['training_intermediate_rows']} intermediate-state rows; validation uses {training['validation_rows']}. Validation does not fit parameters. Missing and unrun alternatives are never zeros; zero is a finite operational completion event, never a mathematically false statement. Every positive label requires a fresh-process Lean kernel and transitive-axiom audit of the original theorem with full prefix and suffix.",
        "",
        f"Input freeze: `{digest(DIRECTORY / 'frozen.json')}`. Execution freeze: `{digest(ROOT / 'models/phase7/frozen.json')}`. Collection source commit: `{read_json(DATA / 'provenance.json')['code_commit']}`. Execution source commit: `{frozen['code_commit']}`. Canonical trace/model/source hashes are retained in their manifests. This is locally recorded preregistration, not an externally blinded evaluation.",
        "",
        "## CPU models and development-only selection",
        "",
        "| Architecture | Family-mean validation completion Brier | Successful validation log-cost MSE |",
        "|---|---:|---:|",
    ]
    for architecture, row in training["validation_scores"].items():
        lines.append(
            f"| {architecture} | {row['completion_brier']:.6f} | {row['conditional_log_cost_mse']:.6f} |"
        )
    lines.extend(
        [
            "",
            f"Selected completion: **{training['selected_completion']}**. Selected cost: **{training['selected_cost']}**. Conservative completion margin: **{training['selected_margin']:.1f}**. The linear logistic model and bounded depth-two booster are both fitted and compared; inference is standard-library scalar arithmetic. The successful log-cost fit receives a training-only Duan smearing correction, recorded before model selection. The final conditional-attempt validation MAE is {cal['conditional_attempt_mae']:.3f}.",
            "",
            f"The selected-model fit takes {training['wall_s']:.3f} seconds wall / {training['trainer_cpu_s']:.3f} seconds process CPU; trainer-process high-water RSS is {training['trainer_process_peak_rss_kib']} KiB. Data collection is separate and much more expensive. Native session CPU/RSS and heartbeats are partial process observations, not a complete aggregate bill.",
            "",
            "The joint score is `p - 0.25*p*min(conditional_attempts/remaining_attempts,2)`. Features contain native goal/context structure and remaining attempts/expansions/time, with no task/state IDs, answer scripts, future outcome or unmetered lookahead. At each expansion, the current state and resource remainder can change the chosen expert; earlier frontier branches survive switching.",
            "",
            "## Independent new mathematical evaluation",
            "",
            "**528 actual runs: 48 theorems × 11 arms**, one registered repetition per arm, two workers. The common engine budget is 18 seconds, 600 attempts, eighty expansions, depth twelve and cap 24; tactic/query calls are capped at two seconds. Initialization, retrieval, predictions and fresh verification consume the engine wall budget. The preserved historical wrapper has small fixed artifact setup outside that clock, while Phase 7 includes model setup; complete `runner_wall_s` is retained per run, so no identical setup-clock scope is claimed. Aesop/grind are separately identified opaque references; their single external attempt is not equal to one primitive inference or one ProofLab attempt.",
            "",
            "![Actual frozen new-family results](assets/phase7-results.svg)",
            "",
            "| Method | Verified / 48 | Mean attempts (all runs) | Mean expanded states | Mean engine wall seconds | Mean strategy switches | Errors |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for arm in protocol()["arms"]:
        r = summary["results"][arm]
        m = r["means"]
        lines.append(
            f"| {NAMES[arm]} | {r['verified']}/48 | {m['attempts']:.2f} | {m['expansions']:.2f} | {m['wall_s']:.3f} | {m['switches']:.2f} | {r['errors']} |"
        )
    lines.extend(
        [
            "",
            "Attempts are not compared as a primitive cost against native automation. Low all-run effort can reflect early failure. Common-success effort is therefore reported separately below. Every final success retains an audited source hash, exact reconstructed proof path and complete native tree; bounded failures, query errors, timeouts and regressions remain in `results.csv` and the canonical gzip archives.",
            "",
            "| Contrast | Success difference (pp) | Paired theorem 95% interval (pp) | Family sensitivity interval (pp) | Gains / regressions | Common-verified attempt difference |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, c in comparisons.items():
        t, f = c["theorem_interval"], c["family_interval"]
        effort = c["common_verified_mean_attempt_difference"]
        lines.append(
            f"| {name} | {100 * t['estimate']:.2f} | [{100 * t['lower']:.2f}, {100 * t['upper']:.2f}] | [{100 * f['lower']:.2f}, {100 * f['upper']:.2f}] | {len(c['gains'])} / {len(c['regressions'])} | {effort:.2f} ({c['common_verified']} tasks) |"
            if effort is not None
            else f"| {name} | {100 * t['estimate']:.2f} | [{100 * t['lower']:.2f}, {100 * t['upper']:.2f}] | [{100 * f['lower']:.2f}, {100 * f['upper']:.2f}] | {len(c['gains'])} / {len(c['regressions'])} | unavailable |"
        )
    lines.extend(
        [
            "",
            "### Did the learned decision change actual search?",
            "",
            "| Policy | Decisions | Departures from staged | Changed pools at shared prefixes | Identical full action sequences / 48 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for arm, a in activity.items():
        lines.append(
            f"| {NAMES[arm]} | {a['decisions']} | {a['departures_from_staged']} | {a['changed_selected_pools']} | {a['identical_full_attempt_sequences']}/48 |"
        )
    lines.extend(
        [
            "",
            "A fitted coefficient or probability difference is not evidence of a downstream algorithmic contribution. Identical action sequences or nonbinding guards provide no measured learning benefit. These controls are reported even when they defeat the intended learning hypothesis.",
        ]
    )
    lines.extend(
        [
            "",
            finding,
            "",
            "Intervals use 10,000 paired theorem bootstrap samples, seed 707, with separate equal-family sensitivity. Secondary contrasts are descriptive, not multiplicity-adjusted significance claims. One repetition and twelve families limit timing stability and mathematical generalization. No threshold, model or generator was retuned after these results.",
            "",
            "## Observed mathematical continuations and regressions",
            "",
        ]
    )
    for case in cases[:8]:
        lines.extend(
            [
                f"### `{case['task_id']}`: {case['left_arm']} versus {case['right_arm']}",
                "",
                f"The recorded outcomes are **{case['left_status']} / {case['right_status']}**, with {case['left_attempts']} / {case['right_attempts']} attempts and terminations `{case['left_termination']}` / `{case['right_termination']}`.",
            ]
        )
        if case["matched_changes"]:
            q = case["matched_changes"][0]
            lines.extend(
                [
                    "",
                    f"At exact shared prefix `{q['prefix']}`, the executed choices are `{q['left_decision']}` / `{q['right_decision']}`. The new decision record says: {q['reason']}. Predicted fixed-expert outcomes: `{json.dumps(q['predictions'], sort_keys=True)}`.",
                ]
            )
        if case["right_proof"]:
            lines.extend(
                [
                    "",
                    "Independently checked comparison proof:",
                    "",
                    "```lean",
                    "\n".join(case["right_proof"]),
                    "```",
                ]
            )
        lines.extend(
            [
                "",
                "These are post-evaluation illustrations, not training labels or a causal guarantee. Unexpanded proof prefixes have unknown availability; an accepted or retained first action does not establish that its branch receives enough subsequent budget.",
            ]
        )
    lines.extend(
        [
            "",
            "All gain/regression cases and exact shared-prefix decisions are retained in `analysis.json`, including witnessed proof-path availability. The analysis does not infer outcomes of unsearched alternatives. Validation-only completion reliability bins and conditional-cost errors are also retained; adaptive final policy outcomes are not misused as calibration labels for unexecuted fixed experts.",
            "",
            "## Policy Learning Explorer and delivery",
            "",
            "The new module compares real final trajectories and matched initial/intermediate development continuations. It displays the three methods, executed completion/cost estimates, conservative reasons, remaining budgets, actual switches, preserved frontier, full native goals/context and genuine accepted/rejected/solved branches. Full-tree inspection, zoom/scroll, JSON export, cancellable local search, static replay and all previous explorers remain available. Development evidence is explicitly distinct from new held-out evaluation.",
            "",
            "[Architecture and limitations](phase-7-architecture.md) · [Exact reproduction commands](phase-7-reproduction.md) · [Frozen protocol](../benchmarks/phase7/protocol.json) · [Training report](../models/phase7/training-report.json) · [Complete summary](../experiments/phase7/evaluation-v1/summary.json).",
            "",
            "## Verification status",
            "",
        ]
    )
    xml = ROOT / "artifacts/local/phase7-pytest.xml"
    if xml.exists():
        root = ET.parse(xml).getroot()
        suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
        counts = {
            k: sum(int(s.get(k, "0")) for s in suites)
            for k in ("tests", "failures", "errors", "skipped")
        }
        lines.append(
            "Final local JUnit outcomes: `"
            + json.dumps(counts, sort_keys=True)
            + "`. See `artifacts/phase7-validation.json` for all executed build/lint/type/JS/browser checks and historical preservation evidence."
        )
    else:
        lines.append(
            "Final validation is still running; no completed full-suite claim is made by this intermediate report."
        )
    ci = ROOT / "artifacts/phase7-hosted-ci.json"
    if ci.exists():
        lines.extend(
            ["", "Hosted CI observation: `" + json.dumps(read_json(ci), sort_keys=True) + "`."]
        )
    else:
        lines.extend(
            [
                "",
                "Hosted CI is not yet verified. GitHub API access is currently blocked by the managed network policy; a successful local run or pushed branch is not a passing hosted run.",
            ]
        )
    pr_file = ROOT / "artifacts/phase7-pull-request.json"
    if pr_file.exists():
        pr = read_json(pr_file)
        lines.extend(
            [
                "",
                "Draft PR state: **"
                + pr["status"]
                + "**. Requested base `"
                + pr["base"]
                + "`, head `"
                + pr["head"]
                + "`. No pull request URL is claimed unless creation is confirmed. The complete proposed title/body and actual API error are retained in `artifacts/phase7-pull-request.json`. The `api.github.com` requirement is saved in the environment draft; applying/publishing that configuration remains outside the agent’s available runtime controls.",
            ]
        )
    lines.extend(
        [
            "",
            "![Actual Policy Learning Explorer](assets/phase7-policy-explorer.png)",
            "",
            "![Actual completion estimates and policy reasons](assets/phase7-policy-decisions.png)",
            "",
            "## Scope and limits",
            "",
            "This improves the learning target and implements measurable bounded strategy decisions; it does not establish a general theorem prover or novel mathematics. Success probabilities are finite-budget empirical predictions without enforced budget monotonicity, conditional costs remain selection-sensitive, and intermediate states can shift away from the sampled curriculum. Smearing and a validation-selected conservative margin are approximations, not confidence certificates. Native work per candidate differs; process CPU/RSS counters omit some startup/audit/aggregate work. The benchmark is elementary, internally frozen rather than externally blinded, and a single registered repetition cannot eliminate runtime noise. Failed methods and negative findings are retained rather than repaired using the test set.",
        ]
    )
    (ROOT / "docs/phase-7-final-report.md").write_text("\n".join(lines) + "\n")
    print(finding)


if __name__ == "__main__":
    main()
