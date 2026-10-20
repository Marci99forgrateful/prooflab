# ProofLab v0.2.0 — Phase 2 delivery report

## Outcome

A working CPU-trained search policy is implemented, trained on permitted
real Lean evidence, and evaluated transparently against the original policies
and native Aesop. **It does not outperform the handcrafted policy in this study.**
All three ProofLab policies verify every evaluation theorem; learned ordering
slightly increases mean attempts and expansions. The model, frozen test set and
negative result are preserved without test-driven tuning.

Development is on `feature/phase2-learned-ranking`, based on v0.1.0 commit
`833ed8063ead78afccbf4952a3cd894e39470f5c`. The delivery is a review candidate;
no Phase 2 change is merged into `main`. MathVerify is untouched. There is no
paid AI API, external model inference, pretrained model or GPU requirement.

## Completed functionality

| Requirement | Delivered implementation/evidence |
|---|---|
| Real local machine learning | Pure-Python CPU pairwise logistic optimization; 73 exported learned coefficients |
| Genuine goal/context input | Native Lean goal shapes, context types, candidate operations and state–action features |
| Reuse typed policy and candidate generator | `LearnedRanking` implements `RankingPolicy`; full candidate-pool invariant checked at runtime |
| Independent proof correctness | Original native bridge, fresh process verification and transitive axiom auditing preserved byte-for-byte |
| Permitted evidence only | 47/48 development tasks replayed; one explicitly unsolved source; 114 states and 230 observed comparisons |
| Correct label semantics | Verified path positive; actual Lean-invalid sibling contrast; valid/unexecuted alternatives unlabeled |
| Separate development validation | 36 permitted non-order tasks for selection training; 12 order tasks for validation; L2 grid selected without evaluation |
| New frozen evaluation | 24 statement-only tasks in six different whole-theorem families; committed before model selection |
| Structural leakage audit | Actual elaborated/reduced Lean expression graphs; alpha/forall-permutation invariance; exact isomorphism; all native trees exported |
| Fair original/learned comparison | Same candidates/caps/budgets; same handcrafted frontier score; learned candidate ordering only |
| Separate automation reference | Native Aesop identified separately; no attribution of its proofs or hidden internal effort to ProofLab |
| Real repeated measurements | 288 actual runs, per-run JSON/CSV, per-theorem tables, model/data/code provenance, failures retained |
| Uncertainty and regressions | Theorem-cluster bootstrap intervals; common-verified subset; four concrete recorded case analyses |
| Interactive comparison | Both scores/ranks/contributions at actual states; three genuine trees; three repeat selectors; live learned search |
| Compatibility | Original 64-task default, BFS/heuristic APIs, Phase 1 replays and CLI benchmark retained |
| Reproduction | Public collection/training/frozen evaluation/export commands, deterministic optimizer, validated JSON artifact |
| Documentation | Model/features/data/protocol/results/limitations, updated README, screenshots and standalone measured plots |

## Verified experimental evidence

The freeze is commit `ceb3e18`; collection/model implementation is `46b7e8f`;
selected model plus evaluation runner is `1b9262d`, committed before the first
new evaluation search. Evaluation uses that source revision. Later commits add
interface, tests, delivery documentation and CLI output options; they do not
retune weights or change the frozen experiment. Exact source hashes are in
[provenance](../experiments/phase2/evaluation-v1/provenance.json).

Model SHA-256:
`99633c7039471cceb0292b4634df2b7c4d60218a0882f156e9cc70b5bd75730e`.
Evaluation SHA-256:
`bc1f9f4a7627f41aded20befb333a04faa3139a36c7bb892e9a9f5c00fe0d8e3`.

| Policy | Fresh-verified runs | Mean attempts | Mean expanded states | Mean wall s | Mean Lean interaction s |
|---|---:|---:|---:|---:|---:|
| BFS | 72/72 | 14.667 | 3.500 | 3.940 | 0.0328 |
| Handcrafted best-first | 72/72 | 10.625 | 2.667 | 3.934 | 0.0234 |
| Learned ordering | 72/72 | 10.792 | 2.708 | 3.923 | 0.0237 |
| Native Aesop reference | 63/72 | 1 external call | 1 external state | 3.785 | 0.0500 |

No run hits a reported resource limit or execution error. Native Aesop has nine
incomplete runs (three theorems × three repeats); one task makes partial
progress with goals remaining, two reject with no progress. Its internal search
is not measured by the external candidate-attempt counter.

Learned minus handcrafted mean attempts: **+0.167** per theorem, 95% interval
**[−0.625, +1.083]**. Expanded states: +0.042 [0.000, +0.125]. Success difference:
0.0 percentage points on a saturated evaluation. Wall difference: −0.011 s
[−0.059, +0.037]. These observations do not support a success, effort or portable
wall-time improvement over the existing heuristic.

The trained objective decreases (0.693147 at zero weights to 0.516680 after
refit); development validation chooses L2=0.1. This confirms fitting, not
held-out search benefit. Reproduction through the public CLI recomputes all
73 coefficients exactly from the stored evidence on the pinned runtime.

See the [full result tables and error analysis](phase-2-results.md),
[model description](phase-2-model.md) and [frozen data/protocol](phase-2-data.md).
Plots are exported as [SVG](assets/phase2-results.svg),
[PNG](assets/phase2-results.png) and [PDF](assets/phase2-results.pdf).

## Interactive demonstration

Run `uv run --frozen prooflab serve` after bootstrap. Select **Phase 2 · learned
search**, choose a recorded repeat and theorem, then choose Learned. The ranking
panel shows actual scheduling rank, heuristic and learned ranks/scores,
top weighted feature contributions, and genuine Lean outcomes. Not-executed
and not-yet-replayed candidates are explicitly distinct. Scores are not
probabilities or truth certificates. Selecting an unexpanded node shows its
expanded parent ranking with an explicit explanation.

Compare strategies displays actual BFS, handcrafted and learned trees for the
same theorem/repeat. The full raw trace remains downloadable when the visible
tree is capped. The benchmark view reports all 288 runs and theorem-cluster
intervals. The local finite-task API can compute a new learned search, record
both score explanations and independently verify the resulting proof. Static
replay works from a subdirectory without a backend or CDN.

[Rankings screenshot](assets/phase2-rankings.png) ·
[Real regression comparison](assets/phase2-comparison.png) ·
[Benchmark screenshot](assets/phase2-benchmarks.png).

## Validation and hosted CI

Local validation completed successfully:

- **59 Pytest tests passed** in 75.34 seconds, including 13 Chromium browser
  tests, genuine Lean search/audit/cancellation, Phase 1 regression, deterministic
  coefficient reproduction, complete 288-trace consistency, score/pool invariants,
  and full 88-statement native split-audit reproduction.
- Lean project build passed (678 jobs). Ruff lint/format, strict Mypy (14 source
  modules), frontend format/build and all four Node tests passed.
- Public training CLI reproduced all 73 exported weights exactly. The actual
  live learned search and static subdirectory replay passed in Chromium.
- Two dependency notices remain: Starlette's HTTPX TestClient deprecation and
  NetworkX's documented directed-hash version change. Dependencies are pinned;
  exact isomorphism is used after hash prefiltering. Neither is a test failure.

[Machine-readable local validation and source hashes](../artifacts/phase2-validation.json).
Draft review PR: [#1](https://github.com/Marci99forgrateful/prooflab/pull/1).
The [actual PR CI run](https://github.com/Marci99forgrateful/prooflab/actions/runs/39404396680)
reports failure **before any job step starts** (empty runner name and empty step
list). Its GitHub check annotation states: “The job was not started because
recent account payments have failed or your spending limit needs to be
increased. Please check the 'Billing & plans' section in your settings”.

This is an account/billing infrastructure block, not evidence of a code/test
failure, and hosted CI is **not claimed passing**. No billing settings are
changed and no paid service is enabled. The exact observed check metadata is
saved in [hosted CI evidence](../artifacts/phase2-hosted-ci.json). The feature
branch remains a draft for review; `main` is still the v0.1.0 base revision.

## Remaining limitations and interpretation

- The curriculum is tiny and biased toward already solved development paths.
  It learns applicability contrasts, not optimality among valid continuations.
- Coarse goal/action interactions and text-based context features miss semantic
  or definitional matches. State-only availability features cancel within pairs.
  Predicate transport and preimage/subset cases expose real regressions.
- All ProofLab evaluation tasks are solved, so success is saturated. This is
  insufficient to establish broad or difficult theorem-proving capability.
- Native structural deduplication excludes alpha renaming, independent parameter
  permutation and reducible-definition variants; it does not decide all logical
  equivalence or exclude shared proof primitives/subgoals. Families are new at
  the whole-statement level, with primitive overlap explicitly acknowledged.
- Three repeats share 24 theorem clusters; they do not create 72 independent
  samples. Bootstrap intervals assume theorem resampling and ignore additional
  family dependence; all-success intervals are degenerate, not guarantees.
- Two workers share the host. Startup/audit dominates wall time. No portable
  timing improvement is established, and no deployment performance claim is made.
- The model learns candidate order only. Its state frontier remains handcrafted;
  no learned value function, broader generator, neural encoder or new tactic is
  claimed. Candidate ordering can still alter frontier insertion ties.
- Linux/POSIX execution is supported. The distribution requires the checkout's
  Lean project, datasets and model; it is not a standalone arbitrary-code service.
- No public v0.2.0 release, main merge, or public deployment is part of this review
  candidate. Hosted CI is reported separately from local code/test evidence.

The scientifically supported deliverable is a reproducible working learned
policy and a transparent **non-improvement finding**, with concrete local wins
and regressions. Improving the features or training curriculum requires a new
study and new unseen evaluation data, not retroactive tuning of this result.
