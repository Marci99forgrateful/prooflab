import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (A B C : Set α) (ha : A ⊆ C) (hb : B ⊆ C) : A ∪ B ⊆ C := by
  intro h0
  intro h1
  rcases h1 with h2 | h3
  apply ha
  assumption
  apply hb
  assumption

#prooflab_audit prooflab_result
