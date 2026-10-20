# Phase 4 candidate-coverage diagnosis

These are exploratory reused Phase 4 tasks, never fresh Phase 5 tests or training data. `experiments/phase5/coverage-v1` preserves twelve genuine matched searches under the Phase 5 limits (24 candidates, 600 attempts, eighty expansions, depth twelve, eighteen seconds). Historical Phase 4 original/expanded/Aesop/grind evidence is linked by canonical path and SHA-256 rather than copied. `analysis.json` records exact-prefix reference-path coverage and separates observations from explanations.

| Task | Original | Phase 4 expanded | Deterministic typed |
|---|---|---|---|
| `p4_witness_transport` | exhausts, 6 attempts | exhausts, 7 | verified, 37 attempts / 4 expansions |
| `p4_cubic_pair` | verified, 386 / 26 | bounded failure, 600 / 36 | bounded failure, 600 / 49 |
| `p4_inverse_right` | bounded failure, 600 / 67 | verified, 2 / 1 | verified, 22 / 2 |
| `p4_lattice_meet` | bounded failure, 240 / 80 | verified, 13 / 3 | bounded failure, 600 / 56 |

The witness case is a directly observed expressiveness gap: original and expanded generators offer no function-applied witness. Native typed construction emits `f a : β`; the actual proof `exists (f a); apply h; assumption` is independently checked and axiom audited. The native Aesop/grind successes remain external engine references. Neither the demonstration nor these reused outcomes constitute held-out ML evidence.

The cubic regression persists in the new typed generator. The successful original path is `rw [h]; constructor; ring; ring`. At the typed root no original candidate is displaced; new associativity/commutativity rewrite and generic logical applications enter. This rules out root truncation as the whole explanation. Their accepted branches and new priorities consume the finite budget; exact-prefix coverage in the structured analysis distinguishes reached states, expanded states, pool membership and actual action outcomes. Inferring a particular optimal new ordering would require another development-only study. The frozen final evaluation is not changed to rescue this theorem.

For the inverse task, bounded group `simp only` normalization plus `assumption` supplies a useful symbolic action. The normalizer respects noncommutativity and is separately ablated. Expanded `simp_all` is faster in this example but invokes a broader engine. These successes do not support a learned-policy attribution.

For the lattice task, having an indexed declaration is insufficient: the expanded arm constructs `le_trans; inf_le_left; assumption`, while typed selection/search still spends its budget elsewhere. Native compatibility of `inf_le_left` depends on the actual current target, including the intermediate metavariables introduced by transitivity. Generic rules can also unify while producing unproductive obligations. The trace exposes that distinction; mere acceptance is not labelled usefulness.

The examples show both missing expressiveness and candidate-explosion failures. Candidate caps, protected original lanes and type filtering do not guarantee monotone success. Further changes would require a separately frozen experiment rather than tuning against this diagnostic/final evidence.
