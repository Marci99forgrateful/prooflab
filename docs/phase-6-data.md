# Phase 6 data and generalization boundary

Phase 6 introduces **160 development statements in sixteen named families** and **48 final statements in twelve new combination families**. No Phase 1–5 held-out trajectory or completion label trains either new model. Historical failures motivate engineering; they do not become new test evidence.

| Development family | Mathematical content | Role |
|---|---|---|
| continuation_logic | Higher-order implications, case analysis, equivalences, refutation | Whole-family validation |
| quantifier_transport | Quantified implications, existential transport, predicates | Training |
| relation_closure | Transitivity, symmetry, chains, relational witnesses | Training |
| ordered_bounds | Partial-order bounds, strict/non-strict composition, antisymmetry | Training |
| lattice_maps | Meets, joins, absorption and mixed bounds | Whole-family validation |
| monoid_words | Noncommutative associativity, identities, contextual products | Training |
| group_equations | Inverses, cancellation and contextual equations | Training |
| ring_expansion | Polynomial identities and substitutions | Training |
| set_images | Images, unions/intersections, membership and monotonicity | Training |
| preimage_algebra | Preimages, complements, differences and membership | Training |
| set_difference | Exclusion, partitions, distributivity and complements | Whole-family validation |
| function_retractions | Inverses, injectivity, surjectivity and transport | Training |
| curried_construction | Curried applications, returned functions and witnesses | Training |
| product_graphs | Heterogeneous/nested products and function graphs | Whole-family validation |
| dependent_contexts | Fibred types and dependent applications | Training |
| heterogeneous_transport | Composition, equality transport and injectivity | Training |

Each family has ten different statements. The candidate learner fits only **120 training tasks**; the other forty supply selection validation. The selected expert retains that training-only fit when collecting mode costs. After selecting the cost architecture on the same whole-family boundary, the cost selector refits the permitted development outcomes, including the validation tasks. Development validation is reused for two selection stages; its losses are selection diagnostics, not independent estimates of final generalization.

The new test families are ternary witness pipelines, callable compositions, conjugation/commutator words, noncommutative context systems, polynomial constraint systems, mixed lattice intervals, image/preimage composition, nested set partitions, quantified case witnesses, dependent function graphs, relation diamonds and inverse chains. Each contains four statements. Statements were specified before solver calibration on them, all unsolved tasks remain, and algorithms/models are frozen before final proof search.

## Structural audit and limits

The native audit elaborates all 208 new statements and compares their reducible typed expression graphs with all **212 earlier statements**. It erases binder names/universe levels and permits forall-binder permutation, then uses graph hashing followed by exact isomorphism. The final registry has zero duplicate pairs. Six initially overlapping development statements were replaced before the dataset freeze; no task was dropped after final search.

This does not prove arbitrary logical independence, proof-schema disjointness or absence of shared mathematical primitives. In particular, longer curried/composed witnesses deliberately test compositional generalization from simpler development constructions. Group, ring, order and set structures recur across splits. Named families are curated research groups, not random independent samples of all mathematics. Reported intervals describe this finite task population and family sensitivity; they do not establish general superiority on arbitrary Mathlib problems. The relevance expert does not fit lattice-map/product-graph validation labels, but the final cost controller refit can see their development outcomes. Strong whole-system out-of-domain generalization is not established by that fact.

## Actual development evidence

The original source/action collector at commit `339b8f1` runs three equal-budget teacher searches per development task, then probes actual candidates at at most two states of a verified path (or the root if no path is found). All branches restore genuine saved Lean states. A source-positive action can be recorded outside the selected pool, explicitly marked. Sixteen alternatives per state and up to four short continuations give:

- 480 real source searches and 160 retained action bundles;
- 212 source states and **3169 actual candidate applications**;
- 538 verified continuations and twelve additional source-path positives;
- 579 actually rejected applications;
- 1742 accepted unknown alternatives, 295 accepted censored alternatives and three tool-error unknown continuations.

The three tool errors involve `apply Or.elim` in quantified-transport tasks: native goals appear closed while unresolved metavariables remain. Fresh complete-proof checking rejects those apparent closures, including recovered `sorryAx` cases. They are **not** positive examples or mathematical-negative labels. This is concrete evidence of the independent verification boundary doing necessary work.

There are 1964 pair preferences: 1480 verified-over-actual-rejection and 484 strictly lower costs between two independently verified continuations. Selection training uses 1473 pairs; validation uses 491. Accepted unknown/censored alternatives never become usefulness negatives. The applicability-only control instead treats actual acceptance as its positive event, with no claim that acceptance implies completion.

A separate **480-run matched selector collection** at commit `689ea1d` fixes the trained relevance component and forces each of symbolic/hybrid/typed modes on every development task. All use the same canonical P3 ordering, new native environment and eight-second/160-attempt budget. Symbolic verifies 135, hybrid 126 and typed 86, yielding **347 verified conditional-cost targets** (262 training and 85 validation). Other outcomes remain in the archive and do not become mathematical-impossibility labels.

## Versioned provenance

The initial naming-error smoke collection, unused all-development relevance refit and initial shared-controller linear-control artifact are retained as labelled diagnostics. They were never evaluated on final tasks. The selection criterion and primary winning coefficients were unchanged by those engineering corrections. The final fully linear control is a distinct ridge-controller baseline on the same data. Exact saved-data refitting reproduced the selected candidate/controller parameters before final testing.

Frozen statements/protocols live in [benchmarks/phase6](../benchmarks/phase6), actual source/action data in [development-v1](../experiments/phase6/development-v1), exact-mode data in [selector-v1](../experiments/phase6/selector-v1), and executable/model hashes in [the final freeze](../models/phase6/frozen.json). Raw/compressed hashes and lossless storage indices retain trace-level evidence. No historical measurement or old model was rewritten.
