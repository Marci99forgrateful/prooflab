import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (P Q R : Prop) (hpq : P → Q) (hqr : Q → R) (hp : P) : R := by
  apply hqr
  apply hpq
  assumption

#prooflab_audit prooflab_result
