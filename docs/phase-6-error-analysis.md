# Phase 6 observed mechanisms and regressions

These are post-evaluation inspections of actual recorded executions. They do not change a generator, model, threshold or budget. The [historical diagnosis](phase-6-diagnosis.md) is separate from this new benchmark evidence. Complete contrast cases, exact-prefix pool changes, scores/order checks and positive-path availability are exported in [analysis.json](../experiments/phase6/evaluation-v1/analysis.json).

## A constructed term adds mathematical expressiveness

In `p6_test_ternary_witness_pipeline_02`, a local function has type `α → β → γ → δ`, with local arguments `a`, `b`, `c` and hypotheses proving predicates of its output. Deterministic hybrid repeat zero independently verifies:

```lean
exists (f a b c)
simp_all
```

It takes sixteen attempted candidates. The native witness record infers type `δ`, matches expected carrier `δ`, reports depth three and retains the derivation `application(f a b, c)` through `application(f a, b)` and `application(f, a)`. The root uses eight baseline and two novelty slots. This is actual bounded callable closure, not a theorem-specific answer. The final simplifier is strong symbolic automation; this proof is not attributed to ML. [Actual trace](../experiments/phase6/evaluation-v1/traces/p6_test_ternary_witness_pipeline_02--deterministic--r0.json.gz).

API tests also construct set-image/preimage witnesses and independently audit complete examples. Those feature tests establish capability, not additional held-out benchmark success.

## A quantified witness helps without establishing a learning gain

For `p6_test_quantified_case_witness_03`, learned repeat one verifies the goal `∃ x, R x ∧ P x` with:

```lean
rcases h with ⟨h0, h1⟩
exists (h0)
simp_all
```

The run takes 58 attempts and seven queries; expanded P4 repeat one exhausts its available search after 35 attempts. The learned root costs are symbolic 2.30203, hybrid 2.24993, typed 2.97556, so hybrid is chosen. The useful witness is a new local after destructuring, not a root answer fetched from a script. Staged repeat zero also verifies the same proof in fifty attempts. Candidate availability and symbolic simplification therefore explain a capability gain; a learned-versus-baseline success alone does not isolate learning. [Learned trace](../experiments/phase6/evaluation-v1/traces/p6_test_quantified_case_witness_03--learned--r1.json.gz), [baseline trace](../experiments/phase6/evaluation-v1/traces/p6_test_quantified_case_witness_03--phase4--r1.json.gz).

## A protected proof branch can still starve

On `p6_test_set_nested_partition_02`, expanded P4 repeat zero verifies `(A \ (B \ C)) ∩ B = A ∩ B ∩ C` in 101 attempts and eighteen expansions:

```lean
apply Set.Subset.antisymm
intro h0
simp_all
intro h0
simp_all
```

The learned root predicts symbolic 1.94751, hybrid 1.87952, typed 2.13484 and chooses hybrid. It retains and accepts `apply Set.Subset.antisymm` at node six; that successor is never expanded before eighty expansions are consumed. There is no observed displacement of this first useful action, and later path availability is unknown because those prefixes are unvisited. The run ends at 393 attempts with an expansion-limit failure. Extra rewriting/order branches change what the fixed frontier explores.

The canonical-tie P4 control also verifies at 101 attempts/eighteen expansions, so this particular loss is not explained by the explicit tie rule alone. Staged repeat zero verifies an alternative audited proof in 205 attempts/33 expansions, while fixed-quota and old-synthesis controls each exhaust eighty expansions at 524 attempts. These are descriptive actual interventions on this task, not a universal causal guarantee. [Failed learned tree](../experiments/phase6/evaluation-v1/traces/p6_test_set_nested_partition_02--learned--r0.json.gz), [verified baseline](../experiments/phase6/evaluation-v1/traces/p6_test_set_nested_partition_02--phase4--r0.json.gz), [staged alternative](../experiments/phase6/evaluation-v1/traces/p6_test_set_nested_partition_02--staged--r0.json.gz).

## The trained controller can suppress the new capability

The positive ternary construction above is also a learned-policy failure. On `p6_test_ternary_witness_pipeline_02`, the primary learned root predicts symbolic 2.50682 versus hybrid 2.51850 and chooses symbolic. It exhausts search after eight attempts without retrieving the available `f a b c` witness. `callable_composition_04`, `dependent_function_graphs_02` and `ternary_witness_pipeline_01` all receive the identical cost vector (symbolic 2.95667, hybrid 2.96835, typed 3.49626), choose symbolic and fail after seven attempts. The deterministic hybrid verifies all four. A small predicted conditional-cost difference can therefore remove the decisive capability entirely. This is observed controller behavior, not proof that any unsearched action is invalid.

The learned policy gains one theorem over deterministic allocation and loses six; its net success difference is −10.417 percentage points. Seeds one/two solve twenty/twenty-one of 48, versus primary seed zero's twenty-two. The transparent linear controller solves twenty-three. Neither a more expressive controller nor a different registered seed establishes an ML gain.

## Which ablations actually change search?

New deterministic synthesis solves six additional statements over the old-construction control, with no losses: two callable-composition, two dependent-graph and two ternary-witness tasks. This supports a concrete expressiveness gain across three related construction families. It does not establish broad mathematical-domain generalization.

The context-dependent eight/four novelty reserve and fixed-four reserve have identical selected pools and schedules at all 1611 matched prefixes. Unused baseline capacity can be borrowed, so the nominal reserve difference is not binding on this benchmark. A distinct source-code option is not evidence of an effective allocation improvement.

Usefulness and applicability-only relevance likewise yield identical pools and execution order at all 1434 matched prefixes, with identical theorem outcomes and attempts. Their fitted weights/objectives differ, but this experiment does not demonstrate a downstream usefulness-objective benefit. Between learned and deterministic modes, all 1586 matched prefixes have identical scores and relative order for shared actions; 1270 have identical membership, with no same-pool execution-order disagreements. Thus Phase 5's accidental retrieval/score-tie coupling has been removed across new policies. The historical P4 comparison deliberately retains its original tie behavior; its separate canonical control changes order but not success.

## What remains unknown

An accepted step can add obligations or branches without producing a complete proof. Candidate compatibility, actual application and audited usefulness remain distinct. Unexplored/censored candidates are not mathematical negatives. Exact tactic prefixes identify observed comparable states; this analysis does not equate arbitrary logically equivalent states or know every valid proof action. Displacement recall uses only witnessed audited paths, so it is partial and selection-biased.

The controller minimizes success-conditioned fixed-mode attempt cost. It has no target for modes that fail within the collection budget, learns only development-root outcomes and then switches greedily at intermediate states under different budgets. Small cost differences can therefore select an unsuccessful or branching-heavy expert. Candidate relevance can only choose within its available and eligible novelty universe; it cannot repair absent terms, insufficient search depth or a starved frontier.

The quantitative report separately assesses whether the new architecture beats expanded P4, whether learning beats deterministic allocation, and whether benefits survive family/seed/budget sensitivity. Local examples are not substitutes for those comparisons. No final-test-driven correction is made to these frozen algorithms.
