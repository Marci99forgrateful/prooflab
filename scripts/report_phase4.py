# ruff: noqa: E501
"""Regenerate actual Phase 4 per-theorem/family results and Phase 3 failure taxonomy."""

import gzip
import json

from prooflab.lean import ROOT

root = ROOT


def read(p):
    p = root / p
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes())


s = read("experiments/phase4/evaluation-v1/summary.json")
analysis = read("experiments/phase4/evaluation-v1/analysis.json")
training = read("models/phase4/training-report.json")
native = read("experiments/phase4/native-states-v1/index.json")
fail = read("experiments/phase4/failures-v1/index.json")
nfail = read("experiments/phase4/native-failures-v1/index.json")
gen = read("experiments/phase4/generator-v1/summary.json")
inf = read("experiments/phase4/inference-cost.json")
model = read("models/phase4/selected.json")
name = {
    "bfs": "BFS",
    "best_first": "Handcrafted",
    "learned": "Phase 2",
    "outcome": "Phase 3",
    "frontier": "Frontier + handcrafted",
    "joint": "Frontier + Phase 3",
    "beam": "Bounded beam",
    "linear_frontier": "Linear control (identical selected model)",
    "automation": "Native Aesop",
    "grind": "Native grind",
}
text = """# Phase 4 — Experimental results

The learned frontier did **not** improve verified success over handcrafted or Phase 3 scheduling: it solves 21/32 theorems, compared with 22/32. Both repetitions have identical statuses, terminations, attempt/expansion counts and proof paths. Timing varies. The selected linear model also loses to a constant predictor on the held-aside development cost-regression check (MSE 0.61184 versus 0.46465); the latter is an explanatory post-selection baseline, not an additional test-tuned policy.

## Frozen controlled protocol

Commit `68ee157` fixes the 32 tasks / eight families and procedure before fitting. Commit `b5ecb2e` records the trained weights and search runner before the 640 final executions. Each algorithm uses two repetitions, interleaved and rotated by theorem/repetition on two workers. Budgets: depth 12, expansions 80, candidates per state 24, attempted candidates 600, total wall 15s and tactic wall 2s. Native Aesop and grind are separately labelled single-call references with independent complete-proof verification.

Primary traces, every attempted native action, complete verified scripts, axiom audits, queue decisions and insertion values are retained losslessly in `experiments/phase4/evaluation-v1/traces/*.json.gz`. `trace-storage.json` preserves original-byte hashes. `results.csv` contains every theorem/policy/repeat, all timing components and resource terminations. `analysis.json` adds common-verified and family-aware uncertainty. No test task or failed run was removed; no policy was retuned after evaluation.

## Aggregate actual measurements

| Policy | Verified runs / 64 | Theorems / 32 | Mean attempts | Mean expanded | Wall s | Lean interaction s | Planning s | Scores/explanations s | Resource-limited runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
"""
for a, r in s["results"].items():
    external = a in ("automation", "grind")
    text += f"| {name[a]} | {r['verified']}/64 | {r['verified'] // 2}/32 | {'1 external call' if external else f'{r["mean_candidates"]:.3f}'} | {'internal work separate' if external else f'{r["mean_expansions"]:.3f}'} | {r['mean_wall_s']:.3f} | {r['mean_lean_execution_s']:.3f} | {r['metrics']['planning_s']['mean']:.3f} | {r['metrics']['model_inference_s']['mean']:.3f} | {r['resource_limits']} |\n"
text += """
All 640 executions completed with zero infrastructure/execution errors. The ProofLab arms record the same candidate-score comparators and state-score explanations; their costs are counted. Full elapsed time includes initialization, interaction, Python planning, verification and cleanup. Planning includes model scoring, so the timing components are nested and must not be summed. The pure score microbenchmark is a separate host-specific measurement. A short overlap with local regression work at the start and normal host sharing mean wall-clock comparisons are indicative, not isolated throughput measurements.

Aesop/grind's one external tactic call cannot be equated to one ProofLab primitive attempt or expansion. Their internal search is not instrumented; internal-work paired differences are deliberately omitted. This also applies to the extended generator's `simp_all`, which performs substantial internal work.

The linear control is byte-identical to the selected model because development selection preferred linear. It is a repeatability/implementation control, **not** independent architectural evidence or a nonlinear test-set ablation. Quadratic features were evaluated only on development validation and not promoted after their weaker scores.

## Paired uncertainty and success-conditioned effort

Differences below are joint learned frontier minus handcrafted. The 10,000 seeded bootstrap resamples repeat-averaged theorems; family sensitivity resamples whole families with their theorem multiplicities. Families are only eight small hand-authored clusters. Repetition is not treated as new independent theorem evidence.

"""
for cohort in ["all_theorems", "common_verified"]:
    text += f"**{cohort.replace('_', ' ')}:**\n\n| Metric | Estimate | Theorem 95% interval | Family 95% interval |\n|---|---:|---|---|\n"
    for metric in [
        "success",
        "attempted_candidates",
        "expanded_states",
        "elapsed_s",
        "lean_execution_s",
    ]:
        d = analysis["comparisons"]["best_first"][cohort][metric]
        a = d["theorem"]
        b = d["family"]
        text += f"| {metric} | {a['estimate']:.5f} | [{a['lower']:.5f}, {a['upper']:.5f}] | [{b['lower']:.5f}, {b['upper']:.5f}] |\n"
text += """
The common-verified subset has 21 theorems from six families. Its mean attempt difference −13.524 has an interval crossing zero at both cluster levels. This subset excludes the theorem lost by the learned frontier and cannot justify an overall performance advantage. All-task effort means also include bounded failures. A failing run can consume fewer attempts or avoid fresh verification; this is not a speed win.

## Factorial interpretation and concrete cases

- **Candidate ordering alone:** Phase 3 and handcrafted frontiers both solve 22/32; their mean attempt difference is −1.0625. Adding Phase 3 candidate scores on top of the learned frontier changes mean attempts by −1 with unchanged 21/32 success. The separately reported paired intervals, including family sensitivity, are in `analysis.json`.
- **Frontier scheduling:** Handcrafted candidates with learned state values already lose the same theorem as the joint policy. This isolates the success regression to scheduling under this budget rather than the Phase 3 candidate ranker.
- **Beam:** Width 12 has the same 21/32 success and mean 147.688 attempts versus joint 147.844, with recorded eviction IDs. This is not evidence of a robust beam advantage; discarded states can contain a proof. The beam is a bounded global best-first queue, not layer-synchronous beam or MCTS.
- **`p4_contra_disj` regression:** Handcrafted and Phase 3 find the same nine-step audited proof in 382 attempts / 59 expansions. Learned frontier (with either candidate policy) stops after 80 expansions / 482 attempts. Early learned decisions project the negative conjunction and explore `R`/`S` subgoals before sufficiently exploiting the disjunction split. Low estimated-cost local states and repeated contexts crowd the finite frontier budget. No claim of mathematical impossibility is made.
- **`p4_cubic_pair` benefit:** Handcrafted 386 attempts / 26 expansions; Phase 3 375; joint 146 / 11. Joint discovers a different six-step verified proof through constructor, local rewrites and ring normalization, while handcrafted uses a four-step proof. Lower search effort here does not imply a shorter proof.
- **`p4_partition_nested` regression:** Handcrafted 70 attempts / 12 expansions versus joint 103 / 24, with a longer 11-step proof versus eight. The learned scheduler also explores accepted but poorly constrained set-lemma applications introducing `Set (Set α)` metavariable obligations. Native acceptance alone is not useful progress.
- **`p4_witness_exists` benefit:** Handcrafted 61 attempts / 10 expansions versus joint 33 / 7, using a different seven-step proof. Actual states, ranked candidates and queue choices can be inspected side by side in the Explorer.

## Per-theorem controlled results

Every cell reports verified status and mean attempted candidates across two structurally identical repetitions; references report only verified status (their internal effort is incomparable).

| Theorem | Family | BFS | Handcrafted | Phase 2 | Phase 3 | Frontier | Joint | Beam | Aesop | grind |
|---|---|---|---|---|---|---|---|---|---|---|
"""
for ident, row in s["per_theorem"].items():
    cells = []
    for a in [
        "bfs",
        "best_first",
        "learned",
        "outcome",
        "frontier",
        "joint",
        "beam",
        "automation",
        "grind",
    ]:
        v = row["algorithms"][a]
        status = "✓" if v["verified"] == v["runs"] else "bounded failure"
        cells.append(
            status
            if a in ["automation", "grind"]
            else f"{status} · {v['attempted_candidates']:.0f}"
        )
    text += f"| {ident} | {row['family']} | " + " | ".join(cells) + " |\n"
text += "\n## Family success (theorems / four)\n\n| Family | BFS | Handcrafted | Phase 2 | Phase 3 | Frontier | Joint | Beam | Aesop | grind |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
for fam in sorted(s["results"]["joint"]["families"]):
    text += (
        "| "
        + fam
        + " | "
        + " | ".join(
            str(s["results"][a]["families"][fam]["verified"] // 2)
            for a in [
                "bfs",
                "best_first",
                "learned",
                "outcome",
                "frontier",
                "joint",
                "beam",
                "automation",
                "grind",
            ]
        )
        + " |\n"
    )
text += """
## Native repeated-state diagnostics

Every primary trace was mapped to offline replayed native expression sequents. Shared prefixes are replayed once per theorem and referenced across policies/repetitions. All local context types, target structure, native representations and unresolved-metavariable flags are retained. Alpha/universe-erased reducible sequent shapes are **diagnostic**, not full elaboration-state identity. Any visible unresolved expression metavariables exclude a state from shared grouping. Hidden constraints, assignments and proof reconstruction still preclude sound merging.

| Policy, first repeat | Observed nonterminal states | Repeated native shapes | Unresolved-mvar states |
|---|---:|---:|---:|
"""
for a in ["best_first", "outcome", "joint", "beam"]:
    stats = [
        v
        for task in native["tasks"]
        for file, v in task["statistics"].items()
        if f"--{a}--r0" in file
    ]
    text += f"| {name[a]} | {sum(v['states'] for v in stats)} | {sum(v['repeated_native_shapes'] for v in stats)} | {sum(v['unresolved_mvar_states'] for v in stats)} |\n"
text += """
No repeated-shape counts are claimed as achievable speedups: the groups have not been shown semantically interchangeable. No transposition pruning or cached transition reuse is enabled. Native replay time is outside primary timed search and its purpose/source hashes are recorded separately.

## Separate generator investigation

The extended arm adds general local `simp_all`, head-filtered lattice premise proposals and rewriting normalization to the same 24-candidate cap; it uses unchanged handcrafted scheduling and budgets. It is a small local corpus expansion, **not** a complete type-unification retriever or a new learned model.

- On the new cohort: original handcrafted 22/32 versus extended 30/32, one separately identified run per task.
- On the previous nine Phase 3 failures: the matched current budget solves 0/9 with the original generator and 6/9 with the extended one. These older held-out outcomes are exploratory and never train/select the model.

These differences support expressiveness/retrieval as a promising next direction, but do not establish ML scheduling gains or rigorous external-system superiority. Strong simplification packs many inferences into a single candidate call; call-count savings are not primitive-inference savings. All extended traces, failures and full audits are retained separately in `experiments/phase4/generator-v1`.

## Error analysis and limits

The learned scalar is fitted only to verified nonterminal continuation successes under a specific fixed downstream collector; 16 censored continuations and 51 valid unselected alternatives remain without point targets. This introduces survivorship and policy bias. The final problem families introduce negative obligations, function transport, lattices, group inverses and larger contexts absent from the tiny curriculum. Textual/native-description features do not encode metavariable coupling, derivability or a mathematical model of progress. A constant validation cost baseline outperforming the fitted model reinforces the weak generalization signal.

The benchmark is original and structurally audited, but shared mathematical primitives and semantically related subgoals remain. Two deterministic repetitions test stability and timing variation, not independent training seeds. The host is shared. No large-model system, Duper, Sledgehammer, CoqHammer or published benchmark leaderboard was reproduced. Survey architecture comparisons are not performance measurements. No test-set retuning, dropped failures or invented proof states occurred.
"""
text += """
Two extended-generator failures are instructive. `p4_cubic_pair` was solved by the original generator (386 handcrafted attempts) but fails in the extended arm at 600 attempts; extra locally accepted normalization branches can consume the budget and change the bounded candidate pool. Thus broader generation is not monotonically better. `p4_witness_transport` remains unresolved by both ProofLab generator variants, while native Aesop and grind audit successfully: the original existential generator proposes local terms but does not synthesize the required function-applied witness `f a`. This is a concrete structural candidate-generation limitation, not a bad learned ranking of an available witness. Both failures are retained.
"""
(root / "docs/phase-4-results.md").write_text(text)
# Failure taxonomy from independent genuine replay evidence.
f = """# Phase 4 — Phase 3 failure analysis

This is exploratory research over all nine Phase 3 theorems unsolved by handcrafted and learned scheduling. Their outcomes were already known; none is new unseen-test evidence, and no diagnostic data enters frontier training/selection. Raw records and original-source hashes: `experiments/phase4/failures-v1`; actual native structural replays: `native-failures-v1`; separate generator arm: `generator-v1`.

Original budget: depth 10 / 70 expansions / 500 attempts / 12s. Diagnostic extension: depth 14 / 160 expansions / 1200 attempts / 25s, same generator/handcrafted policy. The latter changes limits, so success is evidence of a reachable generated path under more work, not of an improved algorithm. Root `simp_all`, `grind` and `aesop` were each actually executed; a claimed success requires a fresh complete-proof and transitive axiom audit.

| Phase 3 theorem | Original stop | Larger original search | Root simp_all | Root grind | Root Aesop | Native repeats / nonterminal states in extension |
|---|---|---|---|---|---|---|
"""
ns = {t["task_id"]: next(iter(t["statistics"].values())) for t in nfail["tasks"]}
for r in fail["results"]:
    p = {q["tactic"]: bool(q["audit"] and q["audit"]["verified"]) for q in r["probes"]}
    n = ns[r["task"]["id"]]
    f += f"| {r['task']['id']} | {r['termination']} | {r['extended']['status']} | {'✓' if p['simp_all'] else 'no audited closure'} | {'✓' if p['grind'] else 'no audited closure'} | {'✓' if p['aesop'] else 'no audited closure'} | {n['repeated_native_shapes']}/{n['states']} |\n"
f += """
## Failure taxonomy and supported conclusions

1. **Resource-bounded reachable paths:** Five of nine are solved by the larger original search: `order_cycle_product`, `set_complement_product`, `set_diff_nested`, `set_excluded_join`, `set_join_product`. This establishes candidate-path reachability for those cases. It does not show that a better frontier would find them within the old budget.
2. **Missing normalization / weak candidate coverage:** `monoid_reverse` and `monoid_three` remain unresolved even at 1200 attempts, while root `simp_all` and Aesop independently close them. The original generator has raw equality rewrites and a few identity/associativity lemmas, but no general normalization candidate. This is strong evidence of a generator/normalization gap; bounded original failure alone would not prove a useful sequence absent. The separately extended generator solves both.
3. **Combined search and generation difficulty:** `set_join_product` is solved by larger original search and by all three general root tactics. Both path search effort and richer internal automation matter. Set exclusion/complement proofs benefit from grind's internal propositional/congruence machinery, whereas Aesop fails these root calls.
4. **Poor candidate applications / metavariable branching:** Accepted set/order lemma applications can introduce underconstrained type/object obligations and many siblings. Native structural output records unresolved metavariables and repeated full-context shapes. Lean acceptance is not a proof-progress guarantee. Existing features see target text/head and partial overlaps, not full semantic relevance.
5. **Frontier and candidate ordering:** Phase 3 controls provide no established global advantage. New Phase 4 controlled scheduling gives actual local benefits/regressions on a new cohort, including a lost contraposition theorem. We do not attribute an old unsolved theorem to frontier ordering solely from a resource-limited trace. Root ranking cannot create missing normalization or globally useful premises.
6. **Repeated structures:** Native diagnostics record substantial repeated reduced sequent shapes, including many monoid rewrite cycles. Visible unresolved-mvar states are deliberately excluded from shared grouping. Other hidden assignments/context constraints still prevent claiming these groups are safely mergeable. No states are merged, pruned or treated as mathematically equivalent.
7. **Unresolved order products:** `order_routes` and `order_square` remain unsolved by larger original search and all three root reference calls. Separate general generator probes do not automatically solve them either. The relation/antisymmetry/dependent-context branching combination remains a limitation, not evidence that the theorem is unprovable.

The three cases solved by native Aesop but not original Phase 3 are exactly `monoid_reverse`, `monoid_three` and `set_join_product`; all three root successes are re-executed and audited here. No Aesop benchmark solution was copied into candidate generation. Broader local automation belongs in its own experiment because it changes both candidate availability and the amount of internal work per call.
"""
(root / "docs/phase-4-failure-analysis.md").write_text(f)
print("results words", len(text.split()), "failure words", len(f.split()))
