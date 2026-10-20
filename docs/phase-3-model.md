# Phase 3: learning from alternative verified futures

Phase 3 fits a CPU-only linear ranker to **downstream search costs of multiple
Lean-accepted actions**, not just whether a tactic applies. This changes both
the evidence and the optimization target from Phase 2. The implementation is
standard regularized pairwise learning; the project contribution is the real
Lean continuation experiment, controlled comparisons and inspectable research
interface, not a claim of a novel ML algorithm.

## Actual evidence and its limits

The source is exclusively the 48 permitted Phase 1 development theorems.
Neither Phase 1 held-out nor Phase 2 evaluation outcomes enter training or
selection. Eight new development-only pilot tasks calibrate difficulty and are
also excluded from fitting. One development theorem, `set_inter_comm`, has no
verified BFS/heuristic source demonstration; it remains explicit in the ledger
and provides no labels.

For the other 47 tasks the collector freshly audits the chosen Phase 1 v3 proof,
replays its actual tactic prefix in native Lean, and executes **every generated
candidate** at each visited state. It retains accepted successor states,
rejected attempts and native messages. It prefers up to three states per task
with multiple nonterminal accepted alternatives, then earlier prefix depth.
At each chosen state it explores up to six accepted candidates in generator
order, ensuring inclusion of the demonstration action. Selection is independent
of rollout outcomes. This is intentionally small, biased on-path sampling.

Rollouts use the unchanged candidate generator and handcrafted best-first policy:
maximum six downstream levels, 20 expansions, 24 candidates/state, 80 attempts
including the first action, five seconds downstream search and 1.5 seconds per
tactic. The already observed first action counts as one attempt; native
pool-probing and session startup are separately retained collection costs.
A fresh complete-proof audit has its own 20-second limit and is timed separately.
All actual trees, candidate pools, full proof paths, successor states and audits
are in `experiments/phase3/continuations-v1/tasks/`.

Collection took **275.194 seconds wall time** with two workers and explored
**199 valid alternatives**. Of these, **183 independently verified completions**
and **16 censored unresolved continuations** were observed. Across all probed
states, 230 native-invalid candidates and 51 valid but unexplored alternatives
are also retained. A Lean-accepted empty-goal transition without a fresh audit
is not automatically a verified completion.

A preference exists only when **both** accepted alternatives have independently
verified full proofs and their measured attempt counts differ. The lower-cost
continuation is preferred under this particular rollout policy/budget. Equal
costs yield no preference. This produces **155 preferences across 36 theorems**;
**81 compare two nonterminal successor states**. The remaining preferences may
include a closing action. Thus the new evidence is demonstrably richer than
immediate proof-closing or applicability classification.

Censored, errored and unexplored valid continuations never become losing labels.
No finite failure is described as mathematically impossible. This conservative
choice discards useful possible lower bounds; it is not survival analysis and
can bias the observed preferences toward continuations solved by the rollout
policy. Measured search cost is not intrinsic minimal proof length or an optimal
value function. A different continuation policy could reverse the ordering.

## Objective, selection and ablations

Let `d = features(state, preferred action) − features(state, other action)`.
The model minimizes:

```text
mean log(1 + exp(−w·d_applicability))
  + λ mean log(1 + exp(−w·d_verified_valid_cost))
  + L2/2 · ||w||²
```

Applicability contrasts are exactly the 230 permitted Phase 2 development
contrasts, recomputed with the selected representation. Their labels remain
verified-path action versus an actually native-invalid sibling. The new cost
preferences compare valid alternatives and are a separate loss term; raw costs
are not fabricated scores or correctness labels. Each term averages its own
pairs; tasks with more collected pairs can influence fitting more strongly.

Initialization is zero. Optimization is deterministic full-batch scalar CPU
Python, 200 epochs, learning rate `0.15/sqrt(1+epoch/30)`, seed 0. L2 grid
`[0.01, 0.1]`, outcome-weight grid `[0.5, 2.0]`, and selection objective were
fixed before final selection. The 12 whole order-domain development tasks are
held apart during hyperparameter selection (47 outcome pairs); the other
permitted development tasks supply 108 selection-training outcome pairs.
Selection minimizes validation **valid-success cost preference loss**, not
applicability loss or final-test search performance. Selected L2 is 0.1 and
outcome weight is 2.0. Final refit uses all permitted development evidence.

The full model is trained from scratch, with **no frozen Phase 2 score or weights
as input**, so prior Phase 2 fitting on order tasks does not leak into the new
model's selection representation. Phase 2 remains a separate frozen baseline.

Three exported models use the same selected hyperparameters:

| Variant | Representation | Training objective | Purpose |
|---|---|---|---|
| `outcome` | Extended pre-action features | Applicability + verified-valid cost pairs | Main Phase 3 policy |
| `applicability_only` | Identical extended features | Applicability only (λ=0) | Isolate the new downstream training signal |
| `old_features_outcome` | Original Phase 2 feature representation | Same combined objective | Isolate representation improvements |

The shared full feature extractor/vocabulary is identical in the main and
no-outcome ablation. Sparse coefficient counts differ because features observed
only through cost pairs have no fitting signal in the ablation and implicitly
stay zero. These controls test the delivered objectives under common selected
hyperparameters; they do not establish that each ablated model was independently
optimized or isolate extra valid-action exposure from its comparative cost labels.

No ablation is selected using final-test outcomes. All three models and their
hashes are frozen before final evaluation. The main model has 108 fitted
coefficients, versus 104 in the applicability-only ablation and 77 in the
old-feature ablation. Training including the selection grid and all refits took
1.343 seconds wall and 1.338 seconds Python CPU on the recorded host.
Full-refit outcome pair losses are 0.3681 (main), 0.7450 (no outcome signal), and
0.4051 (old representation). These are **training** observations, not held-out
search improvements or confidence estimates.

## Features and deployment computation

All deployed features are computed from the current **pre-execution** native
Lean state and existing candidate metadata. In addition to the original
state/action representation, Phase 3 includes candidate-conditioned context
matching, projected conjunction types, implication conclusion/premise matches,
textual self-application estimates, rewrite direction/occurrence/context gain,
syntactic closing/reflexivity estimates, estimated goal-count changes and
operation × current-goal-count interactions.

For example, context availability is conditioned on `assumption` instead of
being identical for every action and cancelling within a pair. Reverse rewriting
can receive a feature when a syntactic replacement reaches a hypothesis type.
Some semantic information comes from Lean's already returned expression heads;
textual matching, conjunction decomposition and rewrite estimates are approximate
and do not implement Lean's definitional equality or unification.

**No actual successor feature is given to the deployed model.** Real goal
reduction and successor complexity are retained for offline analysis and shown
in the interface, clearly separated from model input. Estimated successor
features are explicitly syntactic estimates. There is no hidden probing, extra
Lean call, cached future outcome or test-theorem answer access during ranking.
The unchanged bounded generator supplies exactly the same candidates. Learned
ordering retains the original handcrafted state-frontier score and insertion-ID
ties. Candidate order can indirectly change frontier tie order.

Model files are validated finite JSON weights with versioned feature names;
there is no executable pickle, model download or remote inference. No paid API,
pretrained model, GPU, Torch or hosted training service is used. Scores are
uncalibrated ranking values, not probabilities or proof certificates.

## Reproduction

```bash
bash scripts/bootstrap.sh
# Optional fresh native collection, in a new directory:
uv run --frozen prooflab collect-continuations --output /tmp/prooflab-p3-data
# Fit from committed evidence, preserving the frozen deliverable:
uv run --frozen prooflab train-outcome --output /tmp/prooflab-p3-models
# Or use the fresh evidence explicitly:
uv run --frozen prooflab train-outcome --data /tmp/prooflab-p3-data --output /tmp/prooflab-p3-models-fresh
uv run --frozen prooflab search imp_chain --algorithm outcome --output /tmp/outcome-proof.json
uv run --frozen prooflab evaluate-phase3 --output experiments/phase3/my-run
uv run --frozen prooflab compact-traces --experiment experiments/phase3/my-run
```

Coefficients reproduce exactly from the stored evidence on the pinned Python
runtime; metadata, new collection timings and machine-dependent duration do not.
Once test outcomes are inspected, changes to the model or selection procedure
require a new study with new evaluation data. See the [frozen benchmark](phase-3-data.md)
and the separate [measured results](phase-3-results.md).

## Measured isolated scoring cost

The reproducible `scripts/benchmark_phase3_inference.py` scores all 480
stored development state/action observations ten times, without any Lean call.
This isolated single-process measurement excludes UI explanations and is
host-specific; end-to-end experiment timings separately include both models’
score explanations.

| Variant | Calls | Mean wall microseconds / score | CPU seconds |
|---|---:|---:|---:|
| `outcome` | 4800 | 20.393 | 0.0978 |
| `applicability_only` | 4800 | 19.288 | 0.0926 |
| `old_features_outcome` | 4800 | 11.129 | 0.0534 |

The exact sample/model/script hashes and measured values are exported in
[`experiments/phase3/inference-cost.json`](../experiments/phase3/inference-cost.json).
No latency result is used for model selection or a portable hardware speed claim.
