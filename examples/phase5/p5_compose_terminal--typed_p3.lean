-- Actual frozen execution: p5_compose_terminal, typed_p3, repetition 0.
-- Source trace: experiments/phase5/evaluation-v1/traces/p5_compose_terminal--typed_p3--r0.json.gz
import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α β γ : Type) (f : α → β) (g : β → γ) (P : γ → Prop) (a : α) (h : P (g (f a))) : ∃ z, P z ∧ z = g (f a) := by
  exists (g (f a))

#prooflab_audit prooflab_result
