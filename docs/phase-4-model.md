# Learned frontier-state model

`frontier.py` defines a genuinely fitted scalar state estimator distinct from the Phase 2/3 candidate rankers. `frontier_training.py` reuses genuine, independently verified Phase 3 development continuation outcomes. No pretrained model or external inference is involved; the implementation is pure Python on CPU.

## Architecture and objective

The transparent baseline has 28 named state features: goal count and target/context sizes; local hypothesis and equality/implication counts; exact-target and head coverage; lexical context overlap; goal-head/forall fractions; path depth and log accumulated path transitions; target/goal reduction against the actual parent; visible metavariable markers; and available generated application/rewrite/normalization counts. Generated-operation features use the existing pure candidate generator; no candidate is executed to score a state. Text matching approximates relationships and is not Lean unification.

A second model adds 21 fixed quadratic interactions among six features, for 49 coefficients. This is a modest nonlinear basis with a convex linear-regression fit, not a neural network. Each model standardizes features using training statistics (bias remains one), then uses deterministic full-batch gradient descent to minimize one-half squared error of **log(1 + observed remaining attempts)** with theorem-balanced weights and L2 regularization. Bias is not regularized. Normalization statistics are unweighted over states; the loss averages states within each theorem, then theorems. The CPU experiment does not assume a nonlinear model is superior.

The selected state priority is `clamp(predicted_log_cost, 0, log(601)) + 0.15 * depth`, stable node-ID ties, evaluated once at insertion. Higher predicted continuation cost lowers expansion priority. The complete remaining goal list stays in one native elaboration state; shared metavariables are not decomposed into independent subproblems. This is learned best-first, with no admissibility, optimality or probability-calibration guarantee. A separate width-12 bounded best-first beam evicts the worst queued entry and records its ID; eviction does not assert impossibility and can lose completeness.

Accumulated *path transitions* are the cost-related feature available consistently in both collection and deployment. Global attempts elapsed before a state is selected are logged but deliberately not trained as a feature: their distribution depends on the scheduler itself. Parent-relative simplification uses the observed native successor and its actual parent, both already available at insertion. Future proof outcomes are offline labels only. There are zero native lookahead calls in model scoring.

## Genuine supervision and splits

Only original Phase 1 development IDs are permitted. The immutable Phase 3 collection contains 199 explored continuations: 183 verified and 16 censored. Of the 183 successes, 44 immediately terminal states are excluded because a solved state is independently audited rather than queued. The 139 nonterminal verified successors span 39 development theorems. Invalid probes (230), valid unselected alternatives (51), censored outcomes and the empty unsolved-source ledger provide no point regression targets.

The first accepted action is already paid when the state enters the queue, so its cost target subtracts that action from the actual recorded continuation attempt count. Each successful source's native full-proof audit, proof-prefix hash, observed successor and node-count accounting are checked. `phase4_data.check_freeze` also checks immutable earlier collection/model/results hashes. No previous held-out trace, failure diagnostic, pilot outcome or new evaluation outcome is a training row.

All order development theorems are held aside for model selection: 81 training states and 58 validation states. Final selected weights refit all 139 permitted states. The original 48-ID whitelist is broader than the 39 theorems with usable nonterminal successful evidence; no missing theorem receives invented rows.

## Frozen hyperparameters and actual selection

The pre-selection protocol fixes L2 ∈ {0.01, 0.1}, model basis ∈ {linear, quadratic}, 400 full-batch epochs, learning rate `0.08 / sqrt(1 + epoch / 30)`, zero initialization and deterministic seed 0 (no stochastic fit operations). Selection minimizes whole-theorem mean validation MSE. All four grid entries and CPU/wall cost are in `models/phase4/training-report.json`.

| Basis | L2 | Validation theorem MSE |
|---|---:|---:|
| Linear | .01 | .642692 |
| Linear | .1 | **.611837** |
| Quadratic | .01 | .671922 |
| Quadratic | .1 | .703855 |

The selected model is linear / L2 .1. Training the grid and final artifacts took 1.973 seconds wall / 1.957 seconds CPU on this host. `selected.json` and `linear.json` are byte-identical, SHA-256 `9c8f18b87c26a47aed0ef75c4e622977fd88213fe322cf44a1d14c8e36ff0f1b`. The linear evaluation arm therefore provides a repeatability control, not independent evidence. The inference microbenchmark records 2,780 genuine development state scores per artifact at roughly 254–317 CPU microseconds each, host-specific, without Lean calls.

A post-selection explanatory constant baseline fitted to training-theorem mean log-cost has validation MSE .464651, better than the selected model. It was not used to redesign the selection grid or deploy a new test-tuned policy. This negative result and the final 21/32 versus handcrafted 22/32 success are preserved.

## Limitations

Targets describe completion cost under one fixed, bounded handcrafted continuation search, conditional on its successful observations. They are not shortest-proof costs or judgments of mathematical provability. Excluding censored rows avoids false negative labels but creates survivorship bias. Even a verified state may be explored badly by a different scheduler; lexical state features miss coupled constraints, useful unseen lemmas and global proof structure. Quadratic interactions did not improve held-aside development prediction. No extra seeds or architectures were retrospectively selected from the final test.
