import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (K : Type) [CommSemiring K] (a b x : K) (h : a = b) : ((a+x)^3 = b^3+3*b^2*x+3*b*x^2+x^3) ∧ (a*(x+1)^2 = b*x^2+2*b*x+b) := by
  rw [h]
  constructor
  ring
  ring

#prooflab_audit prooflab_result
