import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (P Q R : α → Prop) (h : ∃ x, P x ∧ Q x) (f : ∀ x, Q x → R x) : ∃ x, P x ∧ R x := by
  rcases h with ⟨h0, h1⟩
  exists h0
  rcases h1 with ⟨h2, h3⟩
  constructor
  assumption
  apply f
  assumption

#prooflab_audit prooflab_result
