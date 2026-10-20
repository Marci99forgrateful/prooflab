# Phase 4 — Experimental results

The learned frontier did **not** improve verified success over handcrafted or Phase 3 scheduling: it solves 21/32 theorems, compared with 22/32. Both repetitions have identical statuses, terminations, attempt/expansion counts and proof paths. Timing varies. The selected linear model also loses to a constant predictor on the held-aside development cost-regression check (MSE 0.61184 versus 0.46465); the latter is an explanatory post-selection baseline, not an additional test-tuned policy.

## Frozen controlled protocol

Commit `68ee157` fixes the 32 tasks / eight families and procedure before fitting. Commit `b5ecb2e` records the trained weights and search runner before the 640 final executions. Each algorithm uses two repetitions, interleaved and rotated by theorem/repetition on two workers. Budgets: depth 12, expansions 80, candidates per state 24, attempted candidates 600, total wall 15s and tactic wall 2s. Native Aesop and grind are separately labelled single-call references with independent complete-proof verification.

Primary traces, every attempted native action, complete verified scripts, axiom audits, queue decisions and insertion values are retained losslessly in `experiments/phase4/evaluation-v1/traces/*.json.gz`. `trace-storage.json` preserves original-byte hashes. `results.csv` contains every theorem/policy/repeat, all timing components and resource terminations. `analysis.json` adds common-verified and family-aware uncertainty. No test task or failed run was removed; no policy was retuned after evaluation.

## Aggregate actual measurements

| Policy | Verified runs / 64 | Theorems / 32 | Mean attempts | Mean expanded | Wall s | Lean interaction s | Planning s | Scores/explanations s | Resource-limited runs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BFS | 38/64 | 19/32 | 221.000 | 41.344 | 4.411 | 1.178 | 0.086 | 0.072 | 24 |
| Handcrafted | 44/64 | 22/32 | 153.594 | 25.719 | 4.204 | 0.767 | 0.052 | 0.043 | 18 |
| Phase 2 | 44/64 | 22/32 | 154.125 | 25.906 | 4.171 | 0.748 | 0.057 | 0.048 | 18 |
| Phase 3 | 44/64 | 22/32 | 152.531 | 25.844 | 4.165 | 0.725 | 0.064 | 0.055 | 18 |
| Native Aesop | 38/64 | 19/32 | 1 external call | internal work separate | 3.351 | 0.088 | 0.001 | 0.001 | 0 |
| Frontier + handcrafted | 42/64 | 21/32 | 148.844 | 26.500 | 4.132 | 0.734 | 0.084 | 0.041 | 20 |
| Frontier + Phase 3 | 42/64 | 21/32 | 147.844 | 26.500 | 4.100 | 0.748 | 0.059 | 0.050 | 20 |
| Bounded beam | 42/64 | 21/32 | 147.688 | 26.500 | 4.110 | 0.769 | 0.058 | 0.049 | 20 |
| Linear control (identical selected model) | 42/64 | 21/32 | 147.844 | 26.500 | 4.137 | 0.738 | 0.059 | 0.050 | 20 |
| Native grind | 40/64 | 20/32 | 1 external call | internal work separate | 3.255 | 0.047 | 0.001 | 0.001 | 0 |

All 640 executions completed with zero infrastructure/execution errors. The ProofLab arms record the same candidate-score comparators and state-score explanations; their costs are counted. Full elapsed time includes initialization, interaction, Python planning, verification and cleanup. Planning includes model scoring, so the timing components are nested and must not be summed. The pure score microbenchmark is a separate host-specific measurement. A short overlap with local regression work at the start and normal host sharing mean wall-clock comparisons are indicative, not isolated throughput measurements.

Aesop/grind's one external tactic call cannot be equated to one ProofLab primitive attempt or expansion. Their internal search is not instrumented; internal-work paired differences are deliberately omitted. This also applies to the extended generator's `simp_all`, which performs substantial internal work.

The linear control is byte-identical to the selected model because development selection preferred linear. It is a repeatability/implementation control, **not** independent architectural evidence or a nonlinear test-set ablation. Quadratic features were evaluated only on development validation and not promoted after their weaker scores.

## Paired uncertainty and success-conditioned effort

Differences below are joint learned frontier minus handcrafted. The 10,000 seeded bootstrap resamples repeat-averaged theorems; family sensitivity resamples whole families with their theorem multiplicities. Families are only eight small hand-authored clusters. Repetition is not treated as new independent theorem evidence.

**all theorems:**

| Metric | Estimate | Theorem 95% interval | Family 95% interval |
|---|---:|---|---|
| success | -0.03125 | [-0.09375, 0.00000] | [-0.09375, 0.00000] |
| attempted_candidates | -5.75000 | [-24.37500, 8.25000] | [-27.84375, 9.59375] |
| expanded_states | 0.78125 | [-0.93750, 2.65625] | [-1.28125, 3.06250] |
| elapsed_s | -0.10356 | [-0.27969, 0.06340] | [-0.23394, 0.01188] |
| lean_execution_s | -0.01890 | [-0.12379, 0.07211] | [-0.12844, 0.05994] |
**common verified:**

| Metric | Estimate | Theorem 95% interval | Family 95% interval |
|---|---:|---|---|
| success | 0.00000 | [0.00000, 0.00000] | [0.00000, 0.00000] |
| attempted_candidates | -13.52381 | [-40.19048, 3.19048] | [-41.09091, 6.60000] |
| expanded_states | 0.19048 | [-1.90476, 2.14286] | [-2.31818, 3.26087] |
| elapsed_s | -0.09316 | [-0.26883, 0.06563] | [-0.20904, 0.01585] |
| lean_execution_s | -0.06914 | [-0.20806, 0.03470] | [-0.19916, 0.01419] |

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
| p4_contra_choice | contrapositive_obligations | bounded failure · 61 | bounded failure · 61 | bounded failure · 61 | bounded failure · 61 | bounded failure · 61 | bounded failure · 61 | bounded failure · 61 | ✓ | ✓ |
| p4_contra_disj | contrapositive_obligations | bounded failure · 482 | ✓ · 382 | ✓ · 397 | ✓ · 382 | bounded failure · 482 | bounded failure · 482 | bounded failure · 477 | ✓ | ✓ |
| p4_contra_nested | contrapositive_obligations | ✓ · 31 | ✓ · 31 | ✓ · 31 | ✓ · 31 | ✓ · 31 | ✓ · 31 | ✓ · 31 | ✓ | ✓ |
| p4_contra_pair | contrapositive_obligations | ✓ · 44 | ✓ · 44 | ✓ · 45 | ✓ · 44 | ✓ · 44 | ✓ · 44 | ✓ · 44 | ✓ | ✓ |
| p4_cubic_context | semiring_cubic_normalization | ✓ · 26 | ✓ · 26 | ✓ · 24 | ✓ · 17 | ✓ · 39 | ✓ · 30 | ✓ · 30 | bounded failure | bounded failure |
| p4_cubic_factor | semiring_cubic_normalization | ✓ · 26 | ✓ · 26 | ✓ · 24 | ✓ · 17 | ✓ · 39 | ✓ · 30 | ✓ · 30 | bounded failure | bounded failure |
| p4_cubic_pair | semiring_cubic_normalization | ✓ · 499 | ✓ · 386 | ✓ · 384 | ✓ · 375 | ✓ · 155 | ✓ · 146 | ✓ · 146 | bounded failure | bounded failure |
| p4_cubic_two_contexts | semiring_cubic_normalization | ✓ · 146 | ✓ · 105 | ✓ · 103 | ✓ · 96 | ✓ · 49 | ✓ · 46 | ✓ · 46 | bounded failure | bounded failure |
| p4_inverse_chain | group_inverse_context | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | ✓ | bounded failure |
| p4_inverse_left | group_inverse_context | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | ✓ | bounded failure |
| p4_inverse_product | group_inverse_context | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | ✓ | bounded failure |
| p4_inverse_right | group_inverse_context | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | bounded failure · 600 | ✓ | bounded failure |
| p4_lattice_join | lattice_meet_join_bounds | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | ✓ | bounded failure |
| p4_lattice_meet | lattice_meet_join_bounds | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure | bounded failure |
| p4_lattice_nested | lattice_meet_join_bounds | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | bounded failure · 240 | ✓ | bounded failure |
| p4_lattice_product | lattice_meet_join_bounds | bounded failure · 241 | bounded failure · 241 | bounded failure · 241 | bounded failure · 241 | bounded failure · 241 | bounded failure · 241 | bounded failure · 241 | bounded failure | bounded failure |
| p4_partition_exclusion | set_partition_obligations | ✓ · 258 | ✓ · 33 | ✓ · 32 | ✓ · 32 | ✓ · 46 | ✓ · 46 | ✓ · 46 | ✓ | ✓ |
| p4_partition_inter | set_partition_obligations | ✓ · 208 | ✓ · 33 | ✓ · 38 | ✓ · 38 | ✓ · 37 | ✓ · 36 | ✓ · 36 | ✓ | ✓ |
| p4_partition_nested | set_partition_obligations | bounded failure · 380 | ✓ · 70 | ✓ · 69 | ✓ · 69 | ✓ · 103 | ✓ · 103 | ✓ · 103 | bounded failure | ✓ |
| p4_partition_pair | set_partition_obligations | bounded failure · 317 | ✓ · 53 | ✓ · 52 | ✓ · 52 | ✓ · 71 | ✓ · 70 | ✓ · 70 | bounded failure | ✓ |
| p4_preimage_chain | set_preimage_obligations | ✓ · 51 | ✓ · 16 | ✓ · 16 | ✓ · 16 | ✓ · 16 | ✓ · 16 | ✓ · 16 | bounded failure | ✓ |
| p4_preimage_diff | set_preimage_obligations | ✓ · 129 | ✓ · 40 | ✓ · 43 | ✓ · 41 | ✓ · 26 | ✓ · 26 | ✓ · 26 | bounded failure | ✓ |
| p4_preimage_inter | set_preimage_obligations | ✓ · 401 | ✓ · 39 | ✓ · 40 | ✓ · 40 | ✓ · 25 | ✓ · 25 | ✓ · 25 | bounded failure | ✓ |
| p4_preimage_union | set_preimage_obligations | ✓ · 227 | ✓ · 45 | ✓ · 45 | ✓ · 45 | ✓ · 42 | ✓ · 42 | ✓ · 42 | bounded failure | ✓ |
| p4_transport_chain | function_relational_transport | ✓ · 239 | ✓ · 26 | ✓ · 26 | ✓ · 26 | ✓ · 29 | ✓ · 29 | ✓ · 29 | ✓ | ✓ |
| p4_transport_edge | function_relational_transport | ✓ · 5 | ✓ · 5 | ✓ · 5 | ✓ · 5 | ✓ · 5 | ✓ · 5 | ✓ · 5 | ✓ | ✓ |
| p4_transport_fixed | function_relational_transport | ✓ · 17 | ✓ · 9 | ✓ · 11 | ✓ · 9 | ✓ · 9 | ✓ · 9 | ✓ · 9 | bounded failure | ✓ |
| p4_transport_symmetric | function_relational_transport | ✓ · 50 | ✓ · 20 | ✓ · 20 | ✓ · 20 | ✓ · 17 | ✓ · 17 | ✓ · 17 | ✓ | ✓ |
| p4_witness_chain | quantified_witness_obligations | ✓ · 24 | ✓ · 24 | ✓ · 24 | ✓ · 24 | ✓ · 24 | ✓ · 24 | ✓ · 24 | ✓ | ✓ |
| p4_witness_exists | quantified_witness_obligations | ✓ · 71 | ✓ · 61 | ✓ · 62 | ✓ · 61 | ✓ · 33 | ✓ · 33 | ✓ · 33 | ✓ | ✓ |
| p4_witness_pair | quantified_witness_obligations | ✓ · 13 | ✓ · 13 | ✓ · 13 | ✓ · 13 | ✓ · 13 | ✓ · 13 | ✓ · 13 | ✓ | ✓ |
| p4_witness_transport | quantified_witness_obligations | bounded failure · 6 | bounded failure · 6 | bounded failure · 6 | bounded failure · 6 | bounded failure · 6 | bounded failure · 6 | bounded failure · 6 | ✓ | ✓ |

## Family success (theorems / four)

| Family | BFS | Handcrafted | Phase 2 | Phase 3 | Frontier | Joint | Beam | Aesop | grind |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| contrapositive_obligations | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 4 | 4 |
| function_relational_transport | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 4 |
| group_inverse_context | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 |
| lattice_meet_join_bounds | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| quantified_witness_obligations | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 4 | 4 |
| semiring_cubic_normalization | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 0 | 0 |
| set_partition_obligations | 2 | 4 | 4 | 4 | 4 | 4 | 4 | 2 | 4 |
| set_preimage_obligations | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 0 | 4 |

## Native repeated-state diagnostics

Every primary trace was mapped to offline replayed native expression sequents. Shared prefixes are replayed once per theorem and referenced across policies/repetitions. All local context types, target structure, native representations and unresolved-metavariable flags are retained. Alpha/universe-erased reducible sequent shapes are **diagnostic**, not full elaboration-state identity. Any visible unresolved expression metavariables exclude a state from shared grouping. Hidden constraints, assignments and proof reconstruction still preclude sound merging.

| Policy, first repeat | Observed nonterminal states | Repeated native shapes | Unresolved-mvar states |
|---|---:|---:|---:|
| Handcrafted | 1784 | 827 | 653 |
| Phase 3 | 1770 | 824 | 645 |
| Frontier + Phase 3 | 1748 | 775 | 679 |
| Bounded beam | 1730 | 749 | 685 |

No repeated-shape counts are claimed as achievable speedups: the groups have not been shown semantically interchangeable. No transposition pruning or cached transition reuse is enabled. Native replay time is outside primary timed search and its purpose/source hashes are recorded separately.

## Separate generator investigation

The extended arm adds general local `simp_all`, head-filtered lattice premise proposals and rewriting normalization to the same 24-candidate cap; it uses unchanged handcrafted scheduling and budgets. It is a small local corpus expansion, **not** a complete type-unification retriever or a new learned model.

- On the new cohort: original handcrafted 22/32 versus extended 30/32, one separately identified run per task.
- On the previous nine Phase 3 failures: the matched current budget solves 0/9 with the original generator and 6/9 with the extended one. These older held-out outcomes are exploratory and never train/select the model.

These differences support expressiveness/retrieval as a promising next direction, but do not establish ML scheduling gains or rigorous external-system superiority. Strong simplification packs many inferences into a single candidate call; call-count savings are not primitive-inference savings. All extended traces, failures and full audits are retained separately in `experiments/phase4/generator-v1`.

## Error analysis and limits

The learned scalar is fitted only to verified nonterminal continuation successes under a specific fixed downstream collector; 16 censored continuations and 51 valid unselected alternatives remain without point targets. This introduces survivorship and policy bias. The final problem families introduce negative obligations, function transport, lattices, group inverses and larger contexts absent from the tiny curriculum. Textual/native-description features do not encode metavariable coupling, derivability or a mathematical model of progress. A constant validation cost baseline outperforming the fitted model reinforces the weak generalization signal.

The benchmark is original and structurally audited, but shared mathematical primitives and semantically related subgoals remain. Two deterministic repetitions test stability and timing variation, not independent training seeds. The host is shared. No large-model system, Duper, Sledgehammer, CoqHammer or published benchmark leaderboard was reproduced. Survey architecture comparisons are not performance measurements. No test-set retuning, dropped failures or invented proof states occurred.

Two extended-generator failures are instructive. `p4_cubic_pair` was solved by the original generator (386 handcrafted attempts) but fails in the extended arm at 600 attempts; extra locally accepted normalization branches can consume the budget and change the bounded candidate pool. Thus broader generation is not monotonically better. `p4_witness_transport` remains unresolved by both ProofLab generator variants, while native Aesop and grind audit successfully: the original existential generator proposes local terms but does not synthesize the required function-applied witness `f a`. This is a concrete structural candidate-generation limitation, not a bad learned ranking of an available witness. Both failures are retained.
