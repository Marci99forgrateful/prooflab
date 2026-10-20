# Phase 4 — Phase 3 failure analysis

This is exploratory research over all nine Phase 3 theorems unsolved by handcrafted and learned scheduling. Their outcomes were already known; none is new unseen-test evidence, and no diagnostic data enters frontier training/selection. Raw records and original-source hashes: `experiments/phase4/failures-v1`; actual native structural replays: `native-failures-v1`; separate generator arm: `generator-v1`.

Original budget: depth 10 / 70 expansions / 500 attempts / 12s. Diagnostic extension: depth 14 / 160 expansions / 1200 attempts / 25s, same generator/handcrafted policy. The latter changes limits, so success is evidence of a reachable generated path under more work, not of an improved algorithm. Root `simp_all`, `grind` and `aesop` were each actually executed; a claimed success requires a fresh complete-proof and transitive axiom audit.

| Phase 3 theorem | Original stop | Larger original search | Root simp_all | Root grind | Root Aesop | Native repeats / nonterminal states in extension |
|---|---|---|---|---|---|---|
| p3_monoid_reverse | resource_limit:attempts | not_found_within_budget | ✓ | no audited closure | ✓ | 262/366 |
| p3_monoid_three | resource_limit:attempts | not_found_within_budget | ✓ | no audited closure | ✓ | 274/374 |
| p3_order_cycle_product | resource_limit:expansions | verified | no audited closure | no audited closure | no audited closure | 133/287 |
| p3_order_routes | resource_limit:expansions | not_found_within_budget | no audited closure | no audited closure | no audited closure | 130/296 |
| p3_order_square | resource_limit:expansions | not_found_within_budget | no audited closure | no audited closure | no audited closure | 173/350 |
| p3_set_complement_product | resource_limit:expansions | verified | no audited closure | ✓ | no audited closure | 236/297 |
| p3_set_diff_nested | resource_limit:expansions | verified | no audited closure | ✓ | no audited closure | 92/256 |
| p3_set_excluded_join | resource_limit:expansions | verified | no audited closure | ✓ | no audited closure | 59/131 |
| p3_set_join_product | resource_limit:expansions | verified | ✓ | ✓ | ✓ | 16/102 |

## Failure taxonomy and supported conclusions

1. **Resource-bounded reachable paths:** Five of nine are solved by the larger original search: `order_cycle_product`, `set_complement_product`, `set_diff_nested`, `set_excluded_join`, `set_join_product`. This establishes candidate-path reachability for those cases. It does not show that a better frontier would find them within the old budget.
2. **Missing normalization / weak candidate coverage:** `monoid_reverse` and `monoid_three` remain unresolved even at 1200 attempts, while root `simp_all` and Aesop independently close them. The original generator has raw equality rewrites and a few identity/associativity lemmas, but no general normalization candidate. This is strong evidence of a generator/normalization gap; bounded original failure alone would not prove a useful sequence absent. The separately extended generator solves both.
3. **Combined search and generation difficulty:** `set_join_product` is solved by larger original search and by all three general root tactics. Both path search effort and richer internal automation matter. Set exclusion/complement proofs benefit from grind's internal propositional/congruence machinery, whereas Aesop fails these root calls.
4. **Poor candidate applications / metavariable branching:** Accepted set/order lemma applications can introduce underconstrained type/object obligations and many siblings. Native structural output records unresolved metavariables and repeated full-context shapes. Lean acceptance is not a proof-progress guarantee. Existing features see target text/head and partial overlaps, not full semantic relevance.
5. **Frontier and candidate ordering:** Phase 3 controls provide no established global advantage. New Phase 4 controlled scheduling gives actual local benefits/regressions on a new cohort, including a lost contraposition theorem. We do not attribute an old unsolved theorem to frontier ordering solely from a resource-limited trace. Root ranking cannot create missing normalization or globally useful premises.
6. **Repeated structures:** Native diagnostics record substantial repeated reduced sequent shapes, including many monoid rewrite cycles. Visible unresolved-mvar states are deliberately excluded from shared grouping. Other hidden assignments/context constraints still prevent claiming these groups are safely mergeable. No states are merged, pruned or treated as mathematically equivalent.
7. **Unresolved order products:** `order_routes` and `order_square` remain unsolved by larger original search and all three root reference calls. Separate general generator probes do not automatically solve them either. The relation/antisymmetry/dependent-context branching combination remains a limitation, not evidence that the theorem is unprovable.

The three cases solved by native Aesop but not original Phase 3 are exactly `monoid_reverse`, `monoid_three` and `set_join_product`; all three root successes are re-executed and audited here. No Aesop benchmark solution was copied into candidate generation. Broader local automation belongs in its own experiment because it changes both candidate availability and the amount of internal work per call.
