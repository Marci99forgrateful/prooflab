# Phase 2: learned candidate ordering

ProofLab v0.2.0 adds a locally fitted **pairwise logistic linear state–action
ranker**. It is machine learning: its coefficients are optimized from collected
Lean executions, rather than assigned by hand. It is small conventional machine
learning, not a language model, neural theorem prover, or learned value function.
No paid API, external inference service, GPU, or pretrained model is used.

## Architecture and interfaces

For an actual Lean state `s` and an existing generated candidate `a`, the score
is `w · features(s, a)`. `LearnedRanking` implements the existing typed
`RankingPolicy` interface and inherits `HeuristicRanking.state_priority`.
Candidates are stably sorted by decreasing learned score, with original
candidate-generation order breaking ties. The frontier still uses the original
handcrafted state score and insertion-ID ties. The learned policy changes
**candidate ordering only**; it does not filter the pool or generate new tactics.
All three ProofLab policies receive identical bounded pools at a given state.
The scheduler checks the complete candidate multiset before and after ranking.

`src/prooflab/features.py` defines a versioned, inspectable sparse feature space:

- Lean goal shape: conjunction, disjunction, equality, existential, iff, false,
  dependent function/implication, order, or other.
- Tactic operation and goal-shape × operation interactions; identities of the
  existing bounded Mathlib lemma index.
- Normalized goal count, target text length, context size and proof-context size.
- Candidate-specific overlap with the referenced local hypothesis type, exact
  target/conclusion match, premise availability, function shape and rewrite
  occurrence tests; reflexive target and available conjunction/existential context.

Feature extraction reads genuine serialized Lean goals, hypotheses and candidate
metadata. No theorem ID, split, title, answer script, state ID, or search node ID
enters the model. Local hypothesis names are resolved to their actual types,
not embedded as categorical IDs. Some features compare pretty-printed text or
count characters; this is **not** a fully alpha-invariant semantic encoder.
State-only features cancel in within-state comparisons and cannot learn a value
function. Unobserved features have coefficient zero. The exported artifact has
73 coefficients; not every possible feature is represented in collected pairs.

Weights use a non-executable, validated JSON format with finite coefficients,
known feature names, schema version and feature version. Model SHA-256, source
revision, data digest, validation trials and hyperparameters accompany the model.
Scores are uncalibrated ordering values, not correctness probabilities. A high
score does not certify that Lean will accept a tactic or that it will find a proof.

## Genuine training evidence

Only the 48 Phase 1 `development` tasks are permitted. The collector chooses
the shortest independently verified Phase 1 v3 BFS/heuristic proof (deterministic
algorithm tie-break), rechecks the complete proof in a fresh Lean process, then
replays each positive action in a persistent native session. At each visited
state it regenerates the unchanged capped candidate pool and actually calls
Lean on **every** candidate. The recorded outcome has three label categories:

1. The action on this fresh-verified solution path is positive evidence.
2. A sibling with a completed native `invalid_candidate` response may form a
   contrast for applicability in this particular state.
3. Valid alternatives remain unlabeled, even if they were not on the chosen
   solution. Unexecuted candidates and timeouts are never negative labels.

An invalid application in one state does not make a tactic or theorem
mathematically incorrect. A verified solution is not necessarily optimal.
Collection errors abort model selection; unsolved source tasks remain explicit
in the collection ledger. `set_inter_comm` has no verified development
BFS/heuristic demonstration and contributes no examples. The other 47 tasks
supply 114 states and 230 positive-versus-observed-invalid pairs. Valid
alternatives and states without contrasts are preserved in the raw evidence.
This is biased, small, on-path applicability evidence; it does not teach which
of several valid branches will ultimately succeed.

## Optimization and selection

Minimize the mean pairwise loss
`log(1 + exp(-w · (features_positive - features_rejected))) + (l2 / 2) ||w||²`.
The implementation uses stable scalar arithmetic and full-batch gradient descent
in pure Python on CPU. Fixed settings: 200 epochs, initial learning rate 0.15,
schedule `0.15 / sqrt(1 + epoch / 30)`, zero initialization, deterministic seed 0.

The protocol and evaluation statements were committed in `ceb3e18` before
model selection. Selection training uses the 36 permitted non-order tasks
(188 observed pairs); order development tasks are validation (42 pairs).
The fixed L2 grid is `[0.001, 0.01, 0.1]`; minimum validation pairwise loss selects
L2. Final refit uses all 230 permitted development pairs. Selected L2 is 0.1. The precise selected
value and every trial are in the [training report](../experiments/phase2-training/training-report.json).
The frozen model and evaluation runner were committed in `1b9262d` before the
first Phase 2 evaluation search. No test outcome is used to tune the model.

Full-refit pair loss is 0.516680 versus 0.693147 at zero weights. This establishes
that fitting changed the training objective; it does **not** establish better
held-out search. See the separate evaluation report for measured search behavior.

## Reproduction

After `bash scripts/bootstrap.sh`:

```bash
uv run --frozen prooflab collect-training --output /tmp/prooflab-training-replay
uv run --frozen prooflab train --data /tmp/prooflab-training-replay --output /tmp/prooflab-ranker.json
uv run --frozen prooflab search imp_chain --algorithm learned --output learned.json
uv run --frozen prooflab evaluate-phase2 --output experiments/phase2/my-run
uv run --frozen python scripts/export_phase2.py experiments/phase2/my-run
npm --prefix web run build
```

The committed model runs immediately; recollection is optional. To reproduce
only optimization from the stored evidence, run
`uv run --frozen prooflab train --output /tmp/refitted-ranker.json`.
Use `--model /tmp/prooflab-ranker.json` on `search` or `evaluate-phase2` to
explicitly evaluate a freshly exported artifact. Collection requires a new
output directory and never overwrites the committed evidence.
Collection reruns actual Lean calls and refreshes execution timings. Training
from the committed `examples.jsonl` is deterministic in weights on the pinned
Python runtime; provenance revision and collection timing are not invariant
across new collections. `test_exported_model_reproduces_from_permitted_evidence`
recomputes every exported coefficient from the stored real pairs. Evaluation
uses a fresh output directory and refuses an altered frozen dataset, protocol,
candidate generator or trusted Lean layer. Treat further selection after test
inspection as a new study requiring new unseen evaluation data.

Inference is local. Search traces retain both heuristic and learned scores,
actual scheduling order, full candidate availability and top feature
contributions for each expanded state. The three original policies all record
these annotations in Phase 2 experiments; model inference/explanation time is
included in planning and wall time. Lean interaction time measures tactic calls;
startup and independent verification are reported separately. No change to the
candidate generator, native bridge, fresh proof checker or axiom policy is needed.
