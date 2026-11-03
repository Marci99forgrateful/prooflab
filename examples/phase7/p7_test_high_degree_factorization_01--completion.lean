import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (R : Type) [CommRing R] (x y z : R) : (x+y)^5 - (x+y)^4 * x = y * (x+y)^4 := by
  ring

#prooflab_audit prooflab_result
