# Phase 7: completion before conditional cost

The Phase 6 controller minimizes a predicted cost conditional on finding a proof. A cheap successful symbolic run can therefore outrank a typed expert even when symbolic search usually never finishes. The preserved Phase 6 repeat-zero traces give 22/48 for learned selection and 30/48 for staged hybrid. These old evaluation outcomes are diagnosis only, never Phase 7 training labels. The machine-readable diagnosis records exact archive hashes and root cost vectors in `research/phase7/phase6-diagnosis.json`.

Phase 7 estimates two distinct quantities for a native Lean state, a fixed expert and a remaining resource budget:

1. The probability of independent proof verification before the stated limits.
2. Candidate attempts conditional on independently verified completion.

A bounded failure is a negative **completion event**, not a false theorem or an invalid tactic. An execution error, unavailable observation or unrun expert is missing. Mere Lean acceptance never creates a successful-completion or low-cost label. Both goals and local hypotheses come from the native elaborator; Python does not simulate proof semantics.

## CPU models and selection

The completion candidates are L2 logistic regression and 48 depth-two logistic-gradient trees. Training uses task-balanced row weights; validation averages Brier error equally over whole mathematical families. The linear fit starts at zero coefficients and empirical log-odds, uses 800 full-batch steps with rate `0.15 / sqrt(1 + epoch/100)` and L2 0.01. The deterministic booster uses rate 0.15, all columns, minimum twelve rows per leaf and the existing histogram CART implementation. There is no pretrained representation, paid service, GPU or external inference dependency.

The cost candidates are the existing ridge/48 depth-two squared-residual regressors, trained only on successful `log(1 + attempts)` outcomes. Whole-family successful-validation log-MSE chooses the architecture. A Duan smearing factor from successful **training rows only** is folded into the exported bias to obtain an arithmetic conditional-attempt estimate. This pre-selection clarification is recorded in `benchmarks/phase7/cost-semantics.json`. Validation labels do not train either model, and there is no refit on validation families. Smearing is an approximation under heteroscedasticity and distribution shift, not an unbiased-cost guarantee.

Features contain current native context descriptors, visible goal heads/typeclasses, functions/equalities/set/product structure, depth, and remaining attempts, expansions and seconds. Method interactions use the same explicit `mode:*` encoding for all experts. Task IDs, native saved-state IDs, proof prefixes, future successes and answer scripts are excluded. Family/task IDs are used for splitting and weighting only.

The completion arm maximizes predicted completion. The cost-only arm minimizes successful conditional cost. The joint arm maximizes `p - 0.25*p*min(cost/remaining_attempts, 2)`, an explicitly bounded successful-cost penalty. The conservative arm additionally requires a completion-probability advantage over the staged fallback. The margin is selected from 0.1/0.2/0.3 by matched whole-family validation completion, with larger-margin ties. This is an empirical guard, not a statistical confidence bound or a proof of non-regression.

The root-trained ablation fits the identical pipeline on root rows only and then uses the same conservative inference. It isolates the intermediate-state training contribution from changing the feature/model family. The separate Phase 7 staged engine control uses no Phase 7 model.

## Real intermediate-state continuations

There are 64 development statements: 32 explicitly registered recollections of permitted Phase 6 development statements and 32 new statements. No historical held-out statement supplies a training label. Four whole families are validation-only, including the two reused Phase 6 families that were also excluded from its candidate-ranker training. New evaluation schemata differ from the development families; shared elementary tactics and mathematical primitives remain unavoidable.

For each task, a fixed staged source run supplies the root and first expanded nonterminal nonroot state. If no such expansion occurs, the first accepted nonterminal successor is used. The source need not succeed. Three fixed experts (`symbolic`, `hybrid`, `typed`) run from exactly the same restored prefix under both registered budgets. Every session is fresh; the original theorem is replayed to establish that source state. Initialization and prefix replay consume the outer wall budget and are recorded separately from suffix attempt counts.

A successful continuation is certified by a fresh Lean process checking the **original theorem and full prefix plus suffix**, including the transitive axiom audit. A source-state acceptance or reduced goal count alone is insufficient. Missing intermediate states are retained as unavailable; no artificial state or outcome is manufactured to fill a matrix.

## Search and algorithm controls

`budget_search.py` owns a native state frontier and exact tactic-prefix identity. Current budgets are recomputed at each expansion, so decisions can change with context and resources. Switching experts does not discard earlier states or restart search. Distinct states with similar printed goals are not merged. Duplicate exact tactic prefixes are not executed twice. All earlier productive branches remain eligible under the same bounded priority queue.

The symbolic, hybrid and typed generators, native type-directed callable construction and Phase 3 candidate/state priorities are inherited unchanged. All Phase 7 experts use the **deterministic** Phase 6 candidate allocation, so a gain is not silently attributed to a changed novelty ranker. The controller changes expert availability, while the unchanged score and explicit tactic-string ties order available actions. `simp_all`, `ring` and other strong symbolic tactics remain visible actions with a two-second call cap. Native Aesop and grind are separate opaque references; their internal work is not equated to ProofLab attempt counts.

The strongest Phase 4 search, actual Phase 6 staged and learned methods run through their preserved engine. The new staged engine control distinguishes the new runner/annotation overhead from learned decisions. Consequently, a difference against Phase 6 alone does not isolate learning; comparisons with the new staged and root-trained controls are also reported. The system adds no unmeasured lookahead or free fallback computation.

## Trust and limitations

Every reported success has an independent Lean source hash, verified proof and allowed-axiom audit. The old bridge, generator, search engine, models, results and frozen protocols are preserved. Check the Phase 6 execution freeze and the final preservation artifact to verify that boundary.

Probabilities describe the finite, observed development regime. They are not probabilities of mathematical provability and are not guaranteed calibrated at every intermediate deployment state. Conditional costs remain success-selected; complete failure data corrects the completion objective but does not remove every distribution shift. Prefix-restoration overhead and resource censoring can affect measured wall time. There is one registered final repetition per arm, only twelve new evaluation families, and no external blinding or claim of mathematical novelty. Negative findings, regressions and errors remain first-class results.
