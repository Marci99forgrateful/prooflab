-- Actual frozen execution: p5_relation_middle, learned_p3, repetition 0.
-- Source trace: experiments/phase5/evaluation-v1/traces/p5_relation_middle--learned_p3--r0.json.gz
import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (R S : α → α → Prop) (a b c : α) (h : R a b) (k : S b c) : ∃ x, R a x ∧ S x c := by
  exists b

#prooflab_audit prooflab_result
