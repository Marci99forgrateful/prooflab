import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (G : Type) [Group G] (a b c d : G)  : (a*b*a⁻¹)*(a*c*a⁻¹)*(a*d*a⁻¹) = a*(b*c*d)*a⁻¹ := by
  simp only [mul_assoc, mul_one, one_mul] at *
  simp_all

#prooflab_audit prooflab_result
