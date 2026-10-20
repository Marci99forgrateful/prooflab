import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α : Type) (R : α → α → Prop) (a b c : α) (ab : R a b) (bc : R b c) (sym : ∀ x y, R x y → R y x) (tr : ∀ x y z, R x y → R y z → R x z) : R c a := by
  apply tr
  apply sym
  assumption
  apply sym
  assumption

#prooflab_audit prooflab_result
