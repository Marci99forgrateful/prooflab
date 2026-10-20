# ProofLab v0.3.0 — Phase 3 delivery report

## Outcome

Phase 3 delivers a working outcome-aware CPU search model trained on **actual
alternative valid proof continuations**, a harder frozen benchmark, controlled
ablations and an interactive continuation laboratory. It is a substantial change
in research evidence and training objective from Phase 2, not a parameter-only
update. **No improvement over the existing heuristic or Phase 2 policy is
established by this experiment.** The negative and mixed findings are preserved.

Development uses `feature/phase3-outcome-aware`, based on current Phase 2 head
`4373233f54ccc46e3d321814c8da384f8f2d20df`. Its separate draft PR targets
`feature/phase2-learned-ranking` while Phase 2 is under review. Neither Phase 2
nor Phase 3 is merged into `main` by this delivery. MathVerify is untouched.
No paid AI API, hosted/pretrained model, external inference or GPU is used.

## Completed functionality

| Requirement | Delivered implementation and evidence |
|---|---|
| Learn from multiple valid futures | 199 actually explored accepted actions, 183 independently audited completions, 16 censored searches |
| Genuine nonterminal alternatives | 155 unequal-cost valid/verified preferences across 36 development theorems; 81 compare two nonterminal successors |
| Preserve unknowns correctly | Censored and unexamined actions never become losing labels; finite failure never means mathematical impossibility |
| CPU outcome-aware model | From-scratch regularized multitask linear policy, 108 exported coefficients, deterministic scalar CPU fitting |
| Distinct Phase 2 baseline | Original 73-coefficient applicability ranker and all Phase 2 results remain unchanged |
| Appropriate ablations | Identical full representation with no outcome loss; same combined objective with old features; common selected hyperparameters |
| Development-only selection | Order-domain development validation, fixed L2/outcome-weight grid, no final or Phase 2 held-out outcome selection |
| Harder frozen evaluation | 32 statements in eight families; eight separate development pilot tasks; all unsolved tasks retained |
| Structural leakage audit | Actual native Lean structures for 128 statements; reducible normalization, alpha/parameter-order graph invariance, exact isomorphism; no duplicates |
| Equal primary controls | Original generator, cap 24, same budgets; original heuristic frontier; no hidden native lookahead during scoring |
| Independent correctness | Trusted bridge, separate full-proof checker and transitive axiom auditing preserved byte-for-byte |
| Real controlled experiments | 384 actual searches including two objective/representation ablations, complete timings/counts/proofs/failures and provenance |
| Statistical transparency | Theorem-cluster paired intervals, common-verified subset, supplementary whole-family cluster sensitivity |
| Advanced interactive interface | All candidates and native outcomes, both model ranks/features, actual successor changes, distinct verified/censored/unexplored futures, selectable branch trees and native node inspection |
| Honest examples | Recorded local benefit, regression and different verified paths; separate held-out diagnostics after evaluation |
| Practical storage | Canonical lossless gzip traces with byte-exact original hashes; large replay payloads generated into ignored build files |
| Compatibility | Original default 64 tasks, algorithms, local/static replay and exports retained; Phase 1–2 artifacts protected by hashes |
| Reproduction | Collection/training/evaluation/archive commands, model/data/protocol hashes, deterministic coefficient tests, full raw evidence |

## Chronology and integrity

- `5fa6187` commits the development pilot, final statements, native structural
  audit and evaluation protocol before final model selection.
- `65fa241` implements and runs actual alternative continuation collection.
- `fc652ac` and `99e3598` implement cost-preference fitting and correct handling
  of an explicitly unsolved source ledger. The latter contributes no examples.
- `7c3d1f2` commits the collected evidence, three selected model artifacts and
  evaluation runner **before any final evaluation search**.
- Later interface, storage, validation and documentation work does not retune
  the models, alter the frozen data/budgets or replace measured outcomes.
  Training also refuses to overwrite an existing frozen model bundle.

Model SHA-256:
`5a86274e3a6f5b534e0822b2723229d6eac8895c6003ebcdd17be5122fd1963a`.
Exact evaluation/protocol/source/model hashes are retained in
[provenance](../experiments/phase3/evaluation-v1/provenance.json),
[data freeze](../benchmarks/phase3/frozen.json) and
[model freeze](../models/phase3/frozen.json).

Phase 1–2 benchmark data, measured results, development evidence and original
model are checked against their pre-existing hashes. The candidate generator,
`ProofLab/Bridge.lean` and the independent Python Lean checker are unchanged.

## Actual training and experimental evidence

The collector replays real development source paths, probes the unchanged
candidate pool in native Lean, and explores selected accepted successors using
one documented deterministic bounded heuristic procedure. It retains every
actual pool/outcome/state and freshly checks each successful full proof.
Only two verified valid continuations with unequal observed attempt costs form
an outcome pair. Invalid applicability contrasts remain a separate objective;
unknown/censored continuations are excluded from the losing side.

Collection: **275.194 seconds wall** with two workers. Fitting plus grid/refits:
**1.343 seconds wall, 1.338 seconds CPU**. Selection uses 108 non-order outcome
pairs for training and 47 order-family outcome pairs for validation. Selected
L2=0.1 and outcome weight=2.0. Final refit uses all permitted development.
The isolated CPU inference benchmark is exported separately, with actual model,
sample and script hashes; no native calls or future-state input are hidden in it.

| Policy | Independently verified runs | Unique theorems solved in every repeat | Mean attempts | Mean expansions |
|---|---:|---:|---:|---:|
| BFS | 40/64 | 20/32 | 189.219 | 32.469 |
| Handcrafted | 46/64 | 23/32 | 144.500 | 23.812 |
| Phase 2 | 46/64 | 23/32 | 145.500 | 24.219 |
| Phase 3 outcome | 46/64 | 23/32 | 144.188 | 23.969 |
| Native Aesop reference | 34/64 | 17/32 | 1 external call | 1 external state |
| Full features, no outcome signal | 23/32 | 23/32 | 145.906 | 24.250 |
| Old features with outcome signal | 23/32 | 23/32 | 143.625 | 23.938 |

All 384 executions and unsolved tasks are preserved. There are 96 explicit
resource-limited executions and zero execution-error runs. Native resource-limit
messages inside tactic outcomes are also counted separately (zero observed).
Structural counts/statuses repeat identically; wall times vary. Primary policies
have two executions and ablations one; neither repetitions nor extra ablation
runs create independent mathematical observations.

The main policy has no success difference from the heuristic or Phase 2.
Mean attempt differences (Phase 3 minus baseline):

| Comparison | Difference | Theorem-cluster 95% interval | Supplementary family-cluster 95% interval |
|---|---:|---|---|
| Handcrafted | −0.3125 | [−2.156, +1.906] | [−3.219, +2.344] |
| Phase 2 | −1.3125 | [−3.562, +0.906] | [−3.781, +1.406] |
| Same features, no outcome signal | −1.71875 | [−3.625, −0.188] | [−3.719, +0.188] |
| Old features with outcomes | +0.5625 | [0.000, +1.562] | [−0.062, +1.531] |

The outcome-signal ablation is suggestive but sensitive to mathematical family
clustering. The added representation does not establish a benefit and harms a
recorded case. This supports neither a broad gain nor a claim that ML is better
than the existing heuristic. All-task effort includes censored failures; the
[full results](phase-3-results.md) additionally report common-verified-subset
comparisons, proof lengths, every theorem/family, complete component timings,
resource terminations and uncertainty assumptions. Aesop's internal search and
one-command proof length cannot be treated as comparable internal work units.

## Actual qualitative analysis and interface

- **Local benefit:** `p3_order_guard` needs 109 Phase 3 attempts versus 133 in
  Phase 2 for the same seven-step verified proof. At a real successor state,
  Phase 3 puts `assumption` ahead of redundant transitivity. The separate
  diagnostic records a verified completion for that branch and a bounded
  unresolved alternative; it never turns the latter into an incorrect label.
- **Local regression:** `p3_monoid_distractor` needs 39 attempts versus 18 for
  Phase 2, ending in the same two-step proof. The new features move `rw [k]`
  narrowly ahead of `rw [h]`. Actual diagnostic rollouts show an audited proof
  from `rw [h]` and a finite unresolved search from `rw [k]`. Full-precision
  scores and feature products are exported; no corrective retuning follows.
- **Different proof paths:** `p3_relation_reverse` has a four-step BFS proof in
  28 attempts and a different five-step Phase 3 proof in 40 attempts. Both are
  independently checked, and both actual paths and trees are displayed.

Open the local application after bootstrap and choose **Alternative
continuations**. Every generated candidate has its native accepted/rejected
status, both model rankings, inspected actual successor changes and any explored
future. Green verified, amber censored and neutral unexplored outcomes remain
distinct. Select two alternatives, pan/zoom their actual trees, click or focus a
node to inspect native context/goals, and export the complete evidence JSON.
Development evidence is explicitly identified as training data; three held-out
illustrative records are collected after frozen evaluation and excluded from
all fitting loaders. Their rollout costs are separate from primary measurements.

The Phase 3 theorem selector compares five actual policy trees, while benchmark
views include both ablations and all 384 runs. Static subdirectory replay,
responsive layout, theme controls, exports and fresh local outcome-guided search
are preserved. Continuation trees load when opened and their interaction is
scoped independently from the original proof explorer.

[Continuation screenshot](assets/phase3-continuations.png) ·
[Actual node inspection](assets/phase3-node-inspection.png) ·
[Benefit case](assets/phase3-benefit.png) ·
[Five policies](assets/phase3-policies.png) ·
[Mobile](assets/phase3-mobile.png) ·
[Measured plot SVG](assets/phase3-results.svg), [PNG](assets/phase3-results.png),
[PDF](assets/phase3-results.pdf).

## Validation and review delivery

Local validation is complete:

- **76 Pytest tests pass**, including model-label correctness, censored alternative
  handling, held-out exclusion, exact reproduction of every exported coefficient,
  complete 384-trace/archive/score/pool consistency, native split structures,
  original Phase 1–2 regression and Chromium interaction.
- The latest continuation-tree controls also have a separate full **16-test
  browser regression**, including native node inspection, zoom, static replay,
  live outcome search, exports and responsive layout.
- Lean project build passes (678 jobs). All **six actual exported Phase 3 proof
  scripts compile and axiom-audit** independently. Ruff lint/format, strict Mypy,
  frontend build/format and seven Node tests pass.
- Actual screenshots cover a beneficial case, a regression with a censored branch,
  a selected native node, five policies, benchmark results and the mobile view.
- Two dependency notices remain: Starlette's HTTPX TestClient deprecation and
  NetworkX's documented directed-hash version change. The pinned version and
  exact isomorphism checks preserve the audit; neither notice is a test failure.

[Machine-readable local validation](../artifacts/phase3-validation.json) retains
command results, test counts and tested-source hashes. The separate [draft PR #2](https://github.com/Marci99forgrateful/prooflab/pull/2)
targets the existing Phase 2 feature branch. The [observed hosted CI run](https://github.com/Marci99forgrateful/prooflab/actions/runs/39413004917)
fails **before any step starts**. GitHub states: “The job was not started because
recent account payments have failed or your spending limit needs to be
increased. Please check the 'Billing & plans' section in your settings”.

This is account/billing infrastructure, not evidence of a code/test failure;
hosted CI is **not claimed passing**. No billing settings are changed or paid
service enabled. [Exact hosted evidence](../artifacts/phase3-hosted-ci.json),
[full local JUnit](../artifacts/phase3-pytest.xml), and
[latest browser JUnit](../artifacts/phase3-browser.xml) are retained for review.

## Remaining limitations

- Only 36 development theorems yield unequal-cost valid-success preferences.
  Sampling follows already solved source paths; chosen actions include the
  demonstration action. This is small, biased evidence, not broad coverage.
- Targets are costs under a fixed heuristic continuation policy/budget, not
  optimal proof lengths, success probabilities or universal mathematical value.
  Censored observations are retained but their possible lower bounds are unused.
- Features use already returned native expression heads and approximate textual
  relations. They do not implement Lean's unification/definitional equality.
  Actual successor features are deliberately offline evidence, not free model input.
- The matched-feature ablation tests the delivered objective under common
  selected hyperparameters. It is not an independently optimized baseline and
  does not fully separate extra valid-action exposure from its comparative labels.
- The frontier score remains handcrafted. No learned value function, RL system,
  new generator, neural encoder, pretrained model or mathematical novelty is claimed.
- Nine theorems remain unsolved by each heuristic/learned variant. Budget depth,
  expansion/attempt caps and generator coverage limit the system. Finite failure
  never establishes a false or impossible mathematical statement.
- Structural deduplication excludes documented normalized expression equivalence,
  not every logical equivalence, shared subgoal or curriculum similarity. The
  authors know the statements; this is not third-party blind evaluation.
- Thirty-two curated statements come in eight related families. Repeats are
  correlated; family resampling weakens the small ablation result and eight
  clusters still give limited uncertainty information. No robust general gain.
- Two workers share the host and instrumentation records both score explanations.
  No portable wall-time speed claim is justified. The inference microbenchmark
  is host-specific and excludes explanations/native proof work by definition.
- Linux/POSIX, the pinned Lean/Mathlib project and the checkout are required.
  The local finite-task service is not an arbitrary-code Internet Lean sandbox.
- This is a draft review candidate, with no automatic main merge, public release
  or deployment. Hosted infrastructure results are separated from local evidence.

The deliverable establishes real outcome-aware learning and transparent original
experimentation. It preserves the scientifically important finding that the
new signal and representation do not establish an advantage over the existing
heuristic on this harder benchmark. Further tuning requires new unseen data.
