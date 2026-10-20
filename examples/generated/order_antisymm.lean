import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) [PartialOrder α] (a b : α) (hab : a ≤ b) (hba : b ≤ a) : a = b := by
  apply le_antisymm
  assumption
  assumption

#prooflab_audit prooflab_result
