import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α β : Type) (f : α → β) (g : β → β) (P Q : β → Prop) (a : α) (h : ∀ y, P (g y) ∧ Q (g y)) : ∃ z, P z ∧ Q z ∧ z = g (f a) := by
  simp_all

#prooflab_audit prooflab_result
