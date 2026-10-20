import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (P Q : α → Prop) (h : ∀ x, P x → Q x) (hp : ∀ x, P x) : ∀ x, Q x := by
  intro h0
  apply h
  apply hp

#prooflab_audit prooflab_result
