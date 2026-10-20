# ProofLab v0.4.0 — Phase 4 delivery report

ProofLab now learns which **complete proof state** to expand, separately from which tactic to try. The review candidate includes an independent CPU state-cost model, a factorial architecture experiment, bounded beam search, native repeated-structure diagnostics, a separate generator investigation, and the **Search Architecture Explorer**.

**The learned frontier did not improve overall success:** 21/32 new theorems versus handcrafted and Phase 3's 22/32. All 640 final executions are retained, including failures and regressions. Smaller all-run effort is not called an improvement when success decreases. Prior Phase 1–3 research, models, results and protected generator/verifier/bridge files remain unchanged. Work is on `feature/phase4-search-architecture`, based on `98639e1` on `feature/phase3-outcome-aware`, with a separate draft PR targeting that branch. Nothing is merged into `main` or published as a stable release.

## Completed functionality and attribution

- **Research/source study:** 29 relevant systems across Lean, HOL, Isabelle, Coq/Rocq, Metamath and general ATP/search research; 30 resolved repository snapshots including one explicitly excluded name collision, plus unsuccessful discovery attempts. The [substantive report](phase-4-related-work.md) separates source observations, author-reported evidence and proposed ideas, links exact modules/commits, records publication/access dates and individually checked license terms. Machine-readable inventory/bibliography and hash-verifying refetch command are retained. No external algorithm source, model weights or benchmark solution archive was imported. Direct arXiv access was proxy-blocked; repository sources/citations and the full repository-hosted DeepSeek V2 paper provided evidence. We do not claim every linked full paper was read.
- **Reasoned design:** [Architecture comparison](phase-4-algorithm-comparison.md) and [decision record](phase-4-design-decisions.md) rank frontier values, representations, beam/best-first, premise retrieval, repeated-state handling, AND/OR search and MCTS. Policy/value separation, best-first, beam and proof reconstruction are established ideas; ProofLab's implementation, integrations and controlled experiments are its own engineering, not new theoretical discoveries.
- **Trained state model:** 139 genuine verified nonterminal successors from 39 permitted development theorems; 81 selection-training / 58 whole-order validation states. Linear (28 coefficients) versus quadratic basis (49) and L2 grid selected the linear model. All point targets derive from independently audited complete continuations; 16 censored and 51 unselected valid alternatives receive no point labels. No held-out diagnostic/final outcome enters training. Scoring uses only observed goals/context/parent/depth and pure generated-operation features, with zero Lean lookahead. [Model details](phase-4-model.md).
- **Frozen benchmark and experiments:** 32 original tasks / eight families, six development-only difficulty pilots, native structural overlap audit over 166 statements, procedures frozen before selection. Ten arms × two repetitions × 32 tasks = 640 genuine executions, including BFS, handcrafted, Phase 2, Phase 3, learned frontier with handcrafted candidates, joint policy, beam, linear control, native Aesop and native grind. The original candidates and budgets are held fixed across controlled arms. [Data boundaries](phase-4-data.md), [actual results](phase-4-results.md).
- **Failure/generator/structure studies:** all nine Phase 3 failures investigated with actual larger-budget searches and root automation probes; all successes freshly audited. The separately identified extended generator adds general simplification, head-filtered lattice premises and rewriting alternatives, never theorem-specific scripts. All 640 primary traces have offline native expression replays with shared-prefix storage and unresolved-metavariable flags. Similar structures never justify merging, pruning or cached proof reuse. [Failure taxonomy](phase-4-failure-analysis.md).
- **Interactive laboratory:** side-by-side actual trees, both repetitions, all ten architectures, frontier selections and alternatives, state/candidate scores, weighted feature contributions, complete native contexts, proof/audit details, resource failures, beam eviction IDs, native repeated-shape relationships, actual metrics and JSON export. The labelled neighborhood projection and complete-tree modes retain genuine node identities. Zoom/pan, mobile design, static replay, earlier views and finite local computation remain available. Research cards link original sources.

## Verified evidence and negative findings

The 640 final executions produced 416 independently verified proof runs and zero execution errors. Structural outcomes repeat exactly; timing varies. Explicit outer resource limits occurred in 158 runs, with no native heartbeat/timeout-resource error messages in rejected candidates. Native reference internal search counts are not equated to ProofLab attempts/expansions.

The joint frontier loses `p4_contra_disj` (handcrafted proof: 382 attempts / 59 expansions; joint: 482 / 80, no proof within the limit). Its common-verified subset averages −13.524 attempts versus handcrafted, but theorem bootstrap 95% interval [−40.190, +3.190] and family interval [−41.091, +6.600] cross zero. That subset excludes the lost theorem and cannot establish an overall advantage. The linear control duplicates the selected model; it is a repeatability control, not independent evidence.

Local gains and regressions are inspectable: `p4_cubic_pair` drops from 386 to 146 attempts but uses a longer verified proof; `p4_partition_nested` rises from 70 to 103 attempts. The selected frontier model's development validation MSE .611837 is worse than the explanatory post-selection constant baseline .464651. This was not used to retune the final model.

The separate generator arm solves 30/32 versus original handcrafted 22/32, but changes candidates and includes strong internal simplification. This is not an ML scheduling gain or a primitive-inference comparison. It also loses the originally solved cubic-pair theorem and still lacks the function-applied witness for `p4_witness_transport`. On the older nine failures, matched current-budget original search solves 0/9 and the extended generator 6/9; those are exploratory prior-test results only.

First-repeat handcrafted traces contain 1,784 nonterminal states and 827 repeated native sequent shapes; joint contains 1,748 / 775. These are coarser structures, not certified transpositions or attainable speedups. Closing a local context as forall can erase an intro boundary; hidden assignments and constraints matter. No state merging is enabled.

## Reproducible artifacts and engineering

| Artifact | Purpose |
|---|---|
| `research/phase4/{sources,bibliography,paper-access}.json` | Pinned sources, licenses, access evidence |
| `benchmarks/phase4/{evaluation,pilot,families,protocol,frozen}.json` | Original statements, immutable procedure, overlap audit and prior hashes |
| `models/phase4/` | Selected/linear artifacts, genuine derived examples, full grid and frozen hashes |
| `experiments/phase4/evaluation-v1/` | 640 canonical lossless traces, per-run CSV, summary, theorem/family uncertainty, resource scan |
| `experiments/phase4/{pilot-v1,failures-v1,generator-v1}/` | Separately identified actual exploratory runs and audits |
| `experiments/phase4/{native-states-v1,native-failures-v1}/` | Native expression representations and trace-hash relationships |
| `examples/phase4/` | Five actual exported proofs, freshly recompiled/audited again |
| `docs/assets/phase4-*` | Real screenshots and standalone SVG/PNG/PDF measurement plots |
| `artifacts/phase4-*` | Local validation and hosted-CI evidence |

See [reproduction commands and exact provenance](phase-4-reproducibility.md). Benchmark/protocol freeze `68ee157` precedes fitting; model/execution freeze `b5ecb2e` precedes final searches. The initial reporting adapter mismatch was repaired by reconstructing summaries from the complete unchanged raw matrix, without rerunning/search-tuning. Historical generic metadata labels are documented; authoritative algorithm/tactic/queue records remain preserved. The onboarding bootstrap now routes npm's cache into the configured writable cache directory; complete bootstrap/build was actually rerun. Reusable install/start configuration was saved as a draft, not published.

## Validation and review status

Local checks and the fresh draft PR/hosted run are recorded in `artifacts/phase4-validation.json` and `artifacts/phase4-hosted-ci.json`. The detailed JUnit evidence is retained. Hosted infrastructure refusals are reported separately and never interpreted as failing code/test steps. Main and the Phase 3 review branch remain untouched.

## Remaining limitations

This is a working research laboratory and a negative learned-frontier result, not a generally superior theorem prover. Training is tiny, conditional on successful fixed-policy continuations, and biased against hard/censored states. Goal descriptions do not fully represent elaboration constraints; approximate lexical features are not type-aware unification. New statement families share elementary primitives; the split audit does not decide arbitrary logical equivalence. Eight families and two deterministic repetitions support limited uncertainty analysis, not broad neural-prover comparisons. Host sharing limits timing interpretation.

MCTS/HTPS-style online training, certified AND/OR transpositions, library-wide premise retrieval, sophisticated neural models and large-model proof synthesis remain unimplemented alternatives with explicit rationale. No Duper, hammer, HOL/Isabelle/Coq prover, or published benchmark leaderboard performance is claimed reproduced. All demonstrated proofs and metrics derive from genuine native executions; future improvements must be evaluated in a new frozen protocol rather than by revising this result.
