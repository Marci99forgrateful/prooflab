import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) [Lattice α] (a b c d e : α) (h : a ≤ b) (k : b ≤ c) (l : c ≤ d) : a ⊔ b ≤ d ⊓ (c ⊔ e) := by
  apply le_trans
  simp_all
  assumption
  simp_all

#prooflab_audit prooflab_result
