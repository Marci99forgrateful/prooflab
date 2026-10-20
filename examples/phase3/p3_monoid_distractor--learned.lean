import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (M : Type) [Monoid M] (a b c d : M) (h : a = b) (k : b = c) (decoy : d = a) : (a * c) * 1 = b * c := by
  rw [h]
  apply mul_one

#prooflab_audit prooflab_result
