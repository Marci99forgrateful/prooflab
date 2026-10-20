# Search policies and candidate generation

Breadth-first search uses a FIFO frontier. Accepted states are expanded in
nondecreasing depth and stable generation order. Best-first search uses a heap
and a deterministic insertion-ID tie-break. Its state score is:

```
12 * remaining_goal_count + total_target_text_length / 12 + 0.8 * depth
```

Candidate ranking uses transparent category priors: matching assumptions,
introductions and projections precede lower-priority lemma and automation
attempts. This is a hand-designed heuristic, not an admissible A* estimate or
trained model. There is no claim of optimality or universal improvement.

The **same bounded candidate list is selected before ranking** for both
policies. The policy changes order, not available mathematics or tactic power.
Specialized `ring` and `omega` attempts are visibly categorized. The Aesop
baseline makes one independent native automation attempt and is never counted
as an original ProofLab search algorithm.

## Candidates

- Goal structure: introduction, constructor, disjunction branches, assumption,
  reflexivity and bounded existing witness terms.
- Hypothesis structure: implication application, conjunction projections,
  fresh-name structured elimination, contradiction and both equality rewrites.
- Curated Mathlib retrieval: goal type features, relevant operators and local
  type context select a small bounded set of actual imported declarations.
- Scoped specialized arithmetic and polynomial normalization.

Lean computes weak-head-normalized structure, so definitions such as set
membership can expose underlying conjunctions and implications. Only proof
hypotheses are proposed as implications or equality proofs. Every proposal
still goes through Lean; a heuristic match is not an applicability guarantee.

## Identity and termination

Visited keys are **exact tactic prefixes inside one session**. Lean snapshots
are never merged merely because printed goals look similar. Local contexts and
hidden metavariable constraints can distinguish states with identical displays.
This conservative choice avoids unsound pruning but retains many semantic
duplicates. Depth, expansion, candidate, attempt and wall-time budgets prevent
cycles from running indefinitely.

`not_found_within_budget` carries a `termination` reason (`search_exhausted` or
`resource_limit:*`). It is never interpreted as falsity. The trace includes
accepted, rejected, solved and interrupted attempt nodes; the solution path is
marked only after independent verification.

## Adding a learned policy

Implement `RankingPolicy.rank_candidates(proof_state, candidate_steps)` and
`state_priority(state, depth)`. A future model changes scheduling and cannot
replace the final Lean verifier. Preserve candidate availability and comparable
budgets when measuring guidance quality.
