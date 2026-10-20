import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) [PartialOrder α] (a b c d : α) (hab : a ≤ b) (hbc : b ≤ c) (hcd : c ≤ d) : a ≤ d := by
  apply le_trans
  assumption
  apply le_trans
  assumption
  assumption

#prooflab_audit prooflab_result
