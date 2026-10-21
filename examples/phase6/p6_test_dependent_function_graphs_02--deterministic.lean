import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (β : α → Type) (f : ∀ x, β x → β x) (g : ∀ x, β x) (a : α) (P Q : β a → Prop) (h : P (g a)) (k : ∀ z, P z → Q (f a z)) : ∃ z, Q z := by
  exists (f a (g a))
  simp_all

#prooflab_audit prooflab_result
