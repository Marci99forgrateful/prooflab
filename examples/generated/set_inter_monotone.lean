import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (A B C : Set α) (h : A ⊆ B) : A ∩ C ⊆ B ∩ C := by
  intro h0
  intro h1
  constructor
  apply h
  exact h1.1
  exact h1.2

#prooflab_audit prooflab_result
