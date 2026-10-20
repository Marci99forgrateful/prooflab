import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (P Q R S : Prop) (f : P → R) (g : Q → S) : ¬ R ∧ ¬ S → ¬ (P ∨ Q) := by
  intro h0
  intro h1
  rcases h1 with h2 | h3
  apply h0.1
  apply f
  assumption
  apply h0.2
  apply g
  assumption

#prooflab_audit prooflab_result
