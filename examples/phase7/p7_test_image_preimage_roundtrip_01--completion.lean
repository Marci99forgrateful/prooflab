import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α β : Type) (f : α → β) (A B C D : Set α) : (A ∩ B) ∪ (C ∩ D) ⊆ f ⁻¹' (f '' ((A ∩ B) ∪ (C ∩ D))) := by
  intro h0
  intro h1
  exists (h0)

#prooflab_audit prooflab_result
