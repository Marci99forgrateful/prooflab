# Phase 3: difficulty calibration, frozen families and controlled evaluation

The final dataset has **32 mathematical tasks across eight theorem families**:
disjunctive routes, higher-order routes, relational diamonds, ordered route
products, noncommutative rewrite routes, contextual polynomial routes, nested set
routes and set exclusion routes. Each family has four statements. These are
statement-only tasks with no target answer scripts in the generator.

## Development-only calibration

Eight separate development pilot tasks were executed with BFS and the original
heuristic before freezing final evaluation or selecting the new model. The
pilot uses neither Phase 2 held-out outcomes nor the final-test candidates for
model selection. Its original traces and budget decision are preserved in
`experiments/phase3/pilot-v1/`. The set-chain pilot takes 160 BFS attempts versus
38 heuristic attempts. A monoid rewrite pilot remains unsolved under the
500-attempt cap. Thus the chosen envelope exhibits both successful substantial
search and bounded failure. Final tasks are not selected or removed according
to which trained policy wins; all 32 remain in the report, including unsolved
and resource-limited problems.

The final budget retains the pilot envelope: depth 10, 70 expansions, 24
candidates per state, 500 attempts, 12 seconds wall time including startup and
fresh audit, two seconds per tactic. All controlled ProofLab policies receive
this same envelope and the unchanged bounded candidate generator.

The frozen family registry, pilot/final statement hashes, protocol, allowed
training IDs and protected-code hashes are in `benchmarks/phase3/`. Freeze occurs
before final hyperparameter selection. The selected model artifacts are committed
separately before any final evaluation search.

## Leakage checks and research preservation

Actual Lean elaboration/reducible normalization produces expression trees for
all **128** relevant statements: 64 Phase 1, 24 Phase 2, eight development pilot
and 32 final Phase 3 statements. The audit erases binder names and universe
levels, represents bound-variable dependencies explicitly, permits independent
forall-parameter permutation, and uses exact labeled graph isomorphism after a
hash prefilter. No normalized structural duplicate exists between final tasks
and prior/pilot statements or within final evaluation. The full native trees
and hashes are exported.

This is stronger than title/text deduplication; it is not a decision procedure
for all logical equivalence or proof-primitive/subgoal overlap. Related statements
within a family are not guaranteed statistically independent. All mathematical
results are elementary and not claimed novel. Training versus validation is
separated by the whole original order-domain development family where feasible;
final families are new whole-theorem constructions but reuse logical primitives.
Authors know the statements, so this is not a third-party blind benchmark.

`check_freeze()` additionally preserves hashes of Phase 1–2 benchmark/results,
Phase 2 training data and model, and the unchanged candidate generator, native
bridge and independent checker. Existing Phase 2 review artifacts remain intact.
The Phase 3 feature branch is based on the current Phase 2 head and its separate
draft PR targets that branch. Neither phase is merged into main by this work.

## Experiments and statistical units

Primary comparisons are BFS, handcrafted best-first, the frozen Phase 2 ranker,
Phase 3 outcome-aware ordering and separately identified native Aesop. Each
primary policy has two executions per theorem. Two controlled ablations have
one execution per theorem: identical features without the outcome objective,
and the combined objective with the old representation. This is **384 actual
searches**, with two workers; the extra repetitions measure execution variability
and are not independent mathematical samples.

All original/learned ProofLab policies use the same available pools, caps,
verifier and frontier score (BFS retains FIFO). Full candidate multisets are
checked around ranking. Every successful empty-goal path must pass fresh full
proof elaboration and transitive axiom auditing. Native Aesop has its own internal
search and candidate universe; one external call cannot be equated to one
ProofLab internal search or candidate attempt.

Policy order rotates by task/repetition. Repeat zero interleaves primary and
ablation policies; repeat one repeats primary policies. Wall time shares the
host and includes collection of both model explanations for every ProofLab
policy; no extra native computation is hidden in scoring. Search wall time is
reported as total elapsed minus initialization minus fresh verification,
including cleanup overhead. Native tactic-interaction, verification, model
inference/planning, proof length, expansions, attempts, failures and family
breakdowns are separately preserved. Dedicated-hardware speed claims are not
supported by these timings.

The preregistered percentile bootstrap uses 10,000 seeded theorem-cluster
resamples, keeping repeats together. Ablations with one repeat are compared by
theorem, not by pretending equal run counts. All-task effort includes censored
failures and can reward early stopping; common-verified subsets are reported
separately. Treat shared family structure as an additional limitation; a small
hand-designed sample cannot establish broad theorem-proving generalization.

## Canonical data, compression and replay

Large final traces are stored once as lossless deterministic gzip JSON, with
exact original-byte SHA-256 and size indices. Inspect using `gzip -dc`, or:

```bash
uv run --frozen prooflab unpack-traces \
  --experiment experiments/phase3/evaluation-v1 --output /tmp/prooflab-p3-raw
uv run --frozen python scripts/export_phase3.py
npm --prefix web run build
```

The exporter builds faithful offline replay payloads from canonical research
artifacts into **ignored** `web/public/phase3/`; they are not another large Git
copy. Bootstrap and the manual Pages build generate them automatically. Model
scores added to continuation-view records use actual stored pre-action states,
with model/source hashes. They are annotations, not substituted search outcomes.

Development continuation evidence is clearly labeled as training evidence.
Any final-test continuation diagnostics are collected **after** frozen model
selection and primary experiments, explicitly labeled post-evaluation, and
never fed back into fitting or task selection. They illustrate actual successes,
bounded failures and unexamined alternatives rather than asserting optimal
proof paths.
