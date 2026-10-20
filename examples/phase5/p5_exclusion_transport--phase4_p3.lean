-- Actual frozen execution: p5_exclusion_transport, phase4_p3, repetition 0.
-- Source trace: experiments/phase5/evaluation-v1/traces/p5_exclusion_transport--phase4_p3--r0.json.gz
import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (A B C : Set α) (a : α) (h : A ⊆ B) (k : a ∈ A \ C) : a ∈ B ∧ a ∉ C := by
  simp_all
  apply h
  exact k.1

#prooflab_audit prooflab_result
