import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (M : Type) [Monoid M] (a b : M) (h : a = b) : a * 1 = b := by
  rw [h]
  apply mul_one

#prooflab_audit prooflab_result
