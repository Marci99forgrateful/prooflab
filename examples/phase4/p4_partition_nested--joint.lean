import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (A B C D : Set α) (h : A ⊆ D) : ((A ∩ B) \ C) ∪ ((A \ B) ∩ C) ⊆ D := by
  intro h0
  intro h1
  rcases h1 with h2 | h3
  rcases h2 with ⟨h1, h3⟩
  rcases h1 with ⟨h2, h4⟩
  apply h
  assumption
  rcases h3 with ⟨h1, h2⟩
  rcases h1 with ⟨h3, h4⟩
  apply h
  assumption

#prooflab_audit prooflab_result
