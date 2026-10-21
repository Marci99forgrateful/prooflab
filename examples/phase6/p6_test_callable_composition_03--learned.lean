import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α β γ δ : Type) (f : α → β → γ) (g : γ → δ) (a : α) (b : β) (P : γ → Prop) (h : ∀ x y, P (f x y)) : ∃ t : γ × β, P t.1 ∧ t.2 = b := by
  exists ((f a b, b))
  simp_all

#prooflab_audit prooflab_result
