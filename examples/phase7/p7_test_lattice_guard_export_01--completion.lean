import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) [Lattice α] (a b c d : α) (h : a ⊓ b ≤ c) : (a ⊓ b ≤ c) ∧ (a ⊓ b ≤ a ⊔ c) := by
  simp_all

#prooflab_audit prooflab_result
