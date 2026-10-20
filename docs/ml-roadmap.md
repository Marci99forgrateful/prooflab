# From heuristic to locally learned guidance

> Phase 1 foundation document. Phase 2 implementation and current evidence:
> [model](phase-2-model.md), [frozen data/protocol](phase-2-data.md),
> [measured results](phase-2-results.md), [delivery report](phase-2-final-report.md).

Phase 1 contains no trained model. Its deterministic ranking interface is
designed for extension without changing the trusted execution/verification
boundary. No hosted inference or paid API is needed.

`trajectories.jsonl` contains genuine goal states and contexts, candidate text,
category, lemma provenance, validity, successor state, depth, actual interaction
time, task split and verified-solution-path membership. Off-path steps are
**unexplored or unsuccessful under this search**, not mathematically useless.
Successful-path labels are assigned only after independent final verification.

The next experiment should train a small CPU model on development trajectories
to rank a fixed candidate pool, then freeze weights and evaluate on a new,
unseen held-out dataset. Split by theorem families as well as IDs to reduce
near-duplicate leakage. Keep baseline candidate availability and budgets fixed.
Record seeds, model parameters, training provenance and raw evaluation results.

Potential later directions are declaration retrieval, learned state value
functions and reinforcement learning. Do not describe a handwritten score as
AI training or a syntactically new tactic script as a novel theorem. Compare
success at fixed budgets, paired explored-state effort and held-out outcomes
before claiming better mathematical search.
