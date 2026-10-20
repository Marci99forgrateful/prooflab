import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (R : Type) [CommRing R] (a b : R) : (a + b)^2 = a^2 + 2*a*b + b^2 := by
  ring

#prooflab_audit prooflab_result
