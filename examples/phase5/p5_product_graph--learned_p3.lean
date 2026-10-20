-- Actual frozen execution: p5_product_graph, learned_p3, repetition 0.
-- Source trace: experiments/phase5/evaluation-v1/traces/p5_product_graph--learned_p3--r0.json.gz
import ProofLab.Bridge

set_option maxHeartbeats 300000
theorem prooflab_result (α β : Type) (a : α) (b : β) : ∃ z : α × β, z.1 = a ∧ z.2 = b := by
  exists ((a, b))

#prooflab_audit prooflab_result
