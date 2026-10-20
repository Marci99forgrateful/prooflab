import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) [PartialOrder α] (a b c d e : α) (ab : a ≤ b) (bc : b < c) (cd : c ≤ d) (de : d ≤ e) : a < e := by
  apply lt_of_le_of_lt
  assumption
  apply lt_of_lt_of_le
  assumption
  apply le_trans
  assumption
  assumption

#prooflab_audit prooflab_result
