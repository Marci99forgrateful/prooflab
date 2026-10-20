# ProofLab v0.5.0 — Phase 5 final report

Phase 5 implements bounded native type-directed retrieval, structured witness generation and development-trained local retrieval ranking. It separates candidate expressiveness, pool selection, action order, frontier scheduling and external automation. The numerical findings below are the actual frozen experiment, not a required improvement target.

**Main finding:** the learned retriever does not improve verified success over deterministic typed retrieval (15/40 each in both repeats), and its common-success effort is worse on one group-context theorem. The stronger Phase 4 expanded generator solves 29/40, while native Aesop solves 31/40. The new typed component improves expressiveness in real witness cases but fails to control branching well enough to establish broad search improvement.

## Delivered functionality

- A focused extension of the 29-system Phase 4 survey, including individually pinned Lean/Aesop/Mathlib modules and seven additional/revisited ReProver, LeanHammer, Duper and TacticToe source checks. No external implementation, pretrained model or solution archive is copied.
- A native index of 116 declarations beyond the original 24-lemma corpus, with exact types, implicit/instance/premise information, source modules, compatibility probes, rewrite direction checks and bounded cost accounting.
- Typed local-function witnesses including `f a` and unary compositions, bounded product constructors and Nat literals. Explicit noncommutative group/set normalizers; original logic, local hypotheses, order/set/algebra rules and old specialized tactics remain available.
- Fixed-cap protected original lanes, novelty selection, backfill and actual entered/displaced candidate records; broad, type-filtered, deterministic, learned, witness and normalization controls.
- A real 130-coefficient CPU pairwise model: 555 observed preferences, 80 verified continuation-cost preferences, 47 contributing development theorems. Accepted unknown/censored alternatives are never mathematical negatives. Development validation selects L2=0.01 before final testing; saved-data refitting is byte-identical.
- Forty original frozen tests in ten families; 212 native typed structural audit trees, no duplicate pairs, explicit semantic-audit limits and immutable earlier evidence.
- 1120 actual searches: four generators crossed with handcrafted/Phase 3 scheduling, a frozen Phase 4 joint-frontier subset, separate Aesop/grind references and four single-run ablations.
- Premise & Candidate Explorer integrated into the existing Architecture Explorer: native states/types, lemma provenance, witnesses, compatibility, retrieval/scheduler ranks and contributions, actual outcomes, pool displacement, costs, real trees/proofs, static replay, mobile layout, local computation and JSON exports.

## Verified quantitative evidence

- `original_p3`: **28/80** independently verified runs; mean 151.875 calls/attempts, 3.372s wall. External references have incomparable internal work units.
- `phase4_p3`: **58/80** independently verified runs; mean 70.975 calls/attempts, 3.717s wall. External references have incomparable internal work units.
- `typed_p3`: **30/80** independently verified runs; mean 399.950 calls/attempts, 5.438s wall. External references have incomparable internal work units.
- `learned_p3`: **30/80** independently verified runs; mean 421.775 calls/attempts, 5.464s wall. External references have incomparable internal work units.
- `typed_joint`: **36/80** independently verified runs; mean 365.137 calls/attempts, 5.692s wall. External references have incomparable internal work units.
- `learned_joint`: **36/80** independently verified runs; mean 364.375 calls/attempts, 5.637s wall. External references have incomparable internal work units.
- `automation`: **62/80** independently verified runs; mean 1.000 calls/attempts, 3.627s wall. External references have incomparable internal work units.
- `grind`: **52/80** independently verified runs; mean 1.000 calls/attempts, 3.127s wall. External references have incomparable internal work units.

The primary ML success difference is **+0.000 percentage points**, theorem interval [+0.000, +0.000], family sensitivity [+0.000, +0.000]. On 15 common-verified theorems, the observed mean attempt difference is +21.867 with theorem interval [+0.000, +65.600]. This conditional comparison is not an unconditional efficiency claim.

The [complete results](phase-5-results.md) include every arm, per-family/per-theorem outcomes, repeated-run stability, actual applicability, partial witnessed availability, uncertainty and raw trace links. The following descriptive gains/regressions were selected after evaluation for explanation; they never changed training or search.

- `typed_p3 minus original_p3`: success gains p5_compose_conditional, p5_compose_pair, p5_compose_terminal, p5_conjugate_cancel, p5_conjugate_context, p5_conjugate_identity, p5_image_witness, p5_product_function, p5_product_graph, p5_product_predicate, p5_product_two_properties, p5_right_inverse_witness; regressions p5_choice_exists, p5_choice_refutation, p5_choice_shared, p5_complement_contradiction, p5_congruence_chain, p5_exclusion_choice, p5_exclusion_transport, p5_image_preimage_element, p5_left_inverse_injective, p5_relation_diagonal, p5_relation_reverse_middle. Complete actual proofs, failed traces and effort differences are in the case-study artifact.
- `learned_p3 minus typed_p3`: success gains none; regressions none. Complete actual proofs, failed traces and effort differences are in the case-study artifact.
- `phase4_p3 minus typed_p3`: success gains p5_binary_congruence, p5_binary_graph_exists, p5_binary_predicate, p5_choice_exists, p5_choice_refutation, p5_choice_shared, p5_complement_contradiction, p5_congruence_chain, p5_exclusion_choice, p5_exclusion_transport, p5_image_preimage_element, p5_join_upper, p5_left_inverse_injective, p5_meet_lower, p5_relation_diagonal, p5_relation_reverse_middle, p5_two_sided_lattice; regressions p5_compose_conditional, p5_compose_pair, p5_right_inverse_witness. Complete actual proofs, failed traces and effort differences are in the case-study artifact.
- `typed_joint minus typed_p3`: success gains p5_binary_predicate, p5_choice_refutation, p5_complement_contradiction, p5_congruence_chain, p5_exclusion_transport, p5_relation_composed, p5_relation_reverse_middle; regressions p5_conjugate_cancel, p5_exclusion_disjoint, p5_image_witness, p5_right_inverse_witness. Complete actual proofs, failed traces and effort differences are in the case-study artifact.
- `automation minus learned_p3`: success gains p5_binary_congruence, p5_binary_graph_exists, p5_binary_predicate, p5_choice_exists, p5_choice_refutation, p5_choice_shared, p5_complement_contradiction, p5_compose_disjunction, p5_congruence_chain, p5_exclusion_choice, p5_exclusion_transport, p5_image_preimage_element, p5_inverse_equality, p5_join_upper, p5_meet_lower, p5_relation_composed, p5_relation_diagonal, p5_relation_reverse_middle; regressions p5_conjugate_cancel, p5_right_inverse_witness. Complete actual proofs, failed traces and effort differences are in the case-study artifact.
- `grind minus learned_p3`: success gains p5_binary_congruence, p5_binary_graph_exists, p5_binary_predicate, p5_choice_all, p5_choice_exists, p5_choice_refutation, p5_choice_shared, p5_complement_contradiction, p5_compose_disjunction, p5_congruence_chain, p5_exclusion_choice, p5_exclusion_transport, p5_image_preimage_element, p5_inverse_unique, p5_left_inverse_injective, p5_relation_composed, p5_relation_diagonal, p5_relation_reverse_middle; regressions p5_conjugate_cancel, p5_conjugate_context, p5_conjugate_identity, p5_product_graph, p5_product_predicate, p5_product_two_properties, p5_right_inverse_witness. Complete actual proofs, failed traces and effort differences are in the case-study artifact.

[Detailed error/intervention analysis](phase-5-error-analysis.md) identifies the exact Group normalizer displaced by `Or.elim`: 157 versus 485 attempts. At 2736/2738 matched P3 prefixes the candidate set is identical and only stable downstream ties change; the two membership changes are this same regression in the two repeats. The development corpus contains no Group/Lattice states. These facts limit any pure-availability attribution.

## Mechanisms and limits

The reused Phase 4 witness failure is repaired by native `f a` construction and an audited three-step proof. The cubic regression persists; typed root original actions are retained, while extra generic/rewrite branches consume the finite search budget. Lattice indexing alone does not guarantee an efficient transitivity/projection sequence. Group normalization supplies symbolic mathematical power and is explicitly ablated. These diagnostic observations are excluded from fresh test scores and training.

A type-compatible rule can create irrelevant or underconstrained subgoals. An accepted step may remain unproductive or unknown. The small development corpus mostly follows old source paths, and only eighty preferences compare completed continuation costs. The model learns finite-policy evidence, not optimal mathematical relevance. The index is bounded, some image/preimage declarations are unavailable in the unchanged imports, witness functions/terms/depth are capped, and constructed partial applications are not promoted to a callable bank. No arbitrary-equivalence pruning, complete Mathlib retrieval, GPU/pretrained embedding model or new foundational prover is claimed.

All timing is shared-host evidence with documented initial test overlap. External references have a two-second per-call cap and opaque internal work. CPU/RSS coverage is partial. Family-balanced sensitivity and theorem-weighted common-success effort are distinct estimands. The ten small families do not establish broad real-world theorem-proving generalization.

The frozen raw family-bootstrap iteration was hash-order dependent. A separate canonical derived report sorts family IDs; original results are retained, theorem metrics are unchanged, and the correction never feeds model/search selection. This reporting correction and the distinct family-balanced point estimand are documented explicitly.

## Reproduction, validation and review

[Model/features/labels](phase-5-model.md) · [Data/protocol boundary](phase-5-data.md) · [Source comparison](phase-5-related-work.md) · [Phase 4 coverage diagnosis](phase-5-coverage.md) · [Exact commands and scopes](phase-5-reproduction.md).

Local and hosted validation evidence is recorded separately in `artifacts/phase5-validation.json` and `artifacts/phase5-hosted-ci.json`. Hosted infrastructure rejection is not a passing test or a code failure. The delivery branch is `feature/phase5-type-directed-retrieval`, with a draft pull request targeting `feature/phase4-search-architecture`. Main, MathVerify and the Phase 4 branch are not merged or modified.

Actual interface captures: [tree comparison](assets/phase5-tree-comparison.png), [native witness and types](assets/phase5-native-witness.png), [regression](assets/phase5-regression.png), [mobile](assets/phase5-mobile.png).
