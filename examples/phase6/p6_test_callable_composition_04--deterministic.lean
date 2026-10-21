import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α β γ δ : Type) (f : α → β → γ) (g : γ → δ) (a : α) (b : β) (k : α → β) (P : δ → Prop) (h : ∀ x, P (g (f x (k x)))) : ∃ t, P t := by
  exists (g (f a (k a)))
  apply h

#prooflab_audit prooflab_result
