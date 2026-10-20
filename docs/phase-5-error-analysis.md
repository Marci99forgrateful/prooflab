# Phase 5 failure and intervention analysis

The new typed generator solves fifteen theorems versus fourteen for original generation under Phase 3 scheduling. This small net change hides **twelve gained and eleven lost theorems**. The broader Phase 4 generator solves twenty-nine. Candidate expressiveness improves in real cases, but added compatible branches frequently overwhelm the bounded search. These are the frozen outcomes; no candidate, score, quota or statement was changed to rescue failures.

## What the learned intervention actually changes

There are 2738 actually matched exact theorem/repetition/tactic-prefix states between learned and deterministic retrieval with Phase 3 scheduling. Capped candidate membership is identical at 2736; it differs at only two, the same group-context prefix in both repetitions. Generated input order differs at all matched states. At the 2736 equal-membership states, actual downstream order also differs, with **zero shared-action score disagreements**. The existing stable Phase 3 sorter preserves retrieval order among equal scores.

Consequently this is primarily a retrieval-order/tie intervention, with a rare membership intervention. It must not be advertised as a pure availability-only or purely independent downstream-scheduling experiment. The frozen factorial still separates named generator and scheduler choices, but their stable-order interaction is real and recorded. The handcrafted comparison similarly matches 2734 prefixes, with two membership changes and 2732 equal-pool order changes. Unmatched prefixes have no counterfactual observations.

## A verified useful normalizer is displaced

At `p5_conjugate_context`, after the actual prefix `rw [← h]`, the deterministic and learned sessions reach the same proof-prefix obligation. The bounded noncommutative group normalizer is in the potential universe in both:

```lean
simp only [mul_assoc, mul_one, one_mul, mul_inv_cancel,
  inv_mul_cancel, mul_inv_cancel_left, mul_inv_cancel_right] at *
```

| Proposal | Deterministic score | Learned score | Deterministic selection | Learned selection |
|---|---:|---:|---|---|
| Group normalizer | 12.000000 | 0.110500 | retained | displaced |
| `apply Or.elim` | 4.300000 | 1.364287 | outside cap | retained |

The typed search completes in **157 attempts**, with `rw [← h]` followed by normalization. The learned search completes in **485 attempts**, requiring an extra `rw [← mul_assoc]` before normalization becomes available along its successful path. Both repetitions reproduce these counts and both complete proofs pass fresh kernel/axiom auditing. The extra 328 attempts are an observed regression, not a claim that `Or.elim` is mathematically invalid. At the matched prefix, the deterministic run directly demonstrates that the displaced action is useful.

The learned normalizer score includes +0.792430 for compatibility, −0.338055 for `op:other`, −0.338055 for the normalizer family, and −0.005820 for the action/goals cross-feature. `Or.elim` receives positive compatibility, premise-overlap, premise-count and implicit-parameter contributions. These are recorded weighted feature contributions, not post-hoc model refitting.

Development evidence explains a limitation of the representation/data boundary: the 99 source states contain PartialOrder (30 observations), Monoid (4), CommMonoid (1) and CommRing (1), but **no Group or Lattice context**. The sixteen observed new normalizers in training are set normalizers: twelve rejected applications and four verified continuations. The model has no directly learned Group-specific normalizer preference; the shared normalizer-family penalty transfers poorly here. Class information gates symbolic generation but is not a separate class-indicator feature in the linear scorer. Adding Group development supervision or changing quotas after seeing this test would be retuning, so neither is done.

## Component evidence and unresolved failures

With handcrafted scheduling, broad unfiltered generation verifies 4/40, type filtering 15/40 and deterministic relevance 15/40. Removing the new witness family gives 7/40; removing the new normalization family gives 13/40. Each ablation has one recorded run. These results support expressiveness and filtering effects in this finite benchmark; they do not establish a learned gain or complete mathematical recall.

Typed indexing alone does not solve the new lattice sandwich family. Generic rules can unify with many goals while leaving unknown data or extra logical premises. Set/quantified contexts also regress despite original useful actions often remaining available. The finite index omits unavailable image/preimage declarations; the fixed witness-function bank does not promote generated partial applications to callable functions, so `f a b` can remain missing even when unary composition and pair construction work. Native Aesop and broader `simp_all` exploit stronger infrastructure; their gains remain separately identified.

Eight task/arm pairs differ across repetitions in termination, attempts, expansions or proof details; all preserve their success/failure classification. Nine searches terminate with a Lean interaction timeout. These are resource-censored failures, not mathematical counterexamples. All unsolved tasks and error details remain in the canonical archives.

The primary ML success difference is zero on this sample. Common-success mean attempts are 21.867 higher for learned retrieval, driven by the single group-context regression; the paired theorem interval is [0, 65.6]. This does not establish a population-wide efficiency improvement or equivalence. Wider development coverage and a newly frozen evaluation would be needed before changing the selector.

[Structured exact-prefix selection analysis](../experiments/phase5/evaluation-v1/analysis.json) · [Full results](phase-5-results.md) · [Model and labels](phase-5-model.md)
