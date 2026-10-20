# Phase 2: frozen data and leakage audit

The new evaluation set contains **24 statements in six theorem families**:
existential elimination, witness construction, function congruence, predicate
transport, set preimages and set differences (four statements each). The
statement-only JSON contains no hand-supplied solution paths. These are different
whole-theorem families from the Phase 1 development curriculum; they necessarily
reuse elementary logical and mathematical primitives.

| Artifact | Role |
|---|---|
| `benchmarks/tasks.json`, split `development` | Only permitted training/validation source (48 tasks) |
| Phase 1 split `held_out` | Never read by the collector or optimizer |
| `benchmarks/phase2/evaluation.json` | New held-out statements, 24 tasks |
| `benchmarks/phase2/protocol.json` | Families, budgets, model-selection grid, repeats, uncertainty |
| `benchmarks/phase2/frozen.json` | Native expression trees, structural audit, hashes, permitted IDs |
| `experiments/phase2-training/` | Real replay outcomes, collection ledger, optimization report |
| `models/phase2/ranker.json` | Selected and refitted CPU model with provenance |

Evaluation SHA-256:
`bc1f9f4a7627f41aded20befb333a04faa3139a36c7bb892e9a9f5c00fe0d8e3`.
The freeze precedes training/model selection in Git. `check_freeze()` verifies
both statement/protocol hashes and the protected candidate-generator/native
bridge/checker hashes before training and evaluation. The runner also checks
that model training IDs are permitted development IDs and that the model cites
the same frozen evaluation. Runtime output and reports retain source/model/data
hashes so a reviewer can check chronology and provenance.

## Structural exclusion, beyond string matching

`ProofLab/Structure.lean` actually elaborates all 88 statements in Lean and
reduces reducible definitions. It exports typed expression trees using de Bruijn
bound-variable references, with binder names and universe-level annotations
erased. The audit builds typed expression graphs, including edges from bound
variable occurrences to their binding nodes. A forall block is unordered while
its dependency edges remain explicit, so independent parameter reordering and
alpha renaming cannot conceal duplicates. Hashes only prefilter comparisons;
final exclusion uses **exact labeled graph isomorphism**. App argument roles
and constants remain distinguished. The pinned NetworkX version is recorded.

No structural duplicate was found between the 24 evaluation statements and
**any** of the 64 Phase 1 statements, or within evaluation. Automated tests use
actual Lean elaboration to exercise renamed/reordered equivalents, freeze
checks and tamper rejection. The complete native trees and pair audit are
exported rather than relying on statement titles or author assertions.

This is not a decision procedure for arbitrary logical equivalence. Different
statements can use the same proof primitive, and some new statements can be
viewed as pointwise applications of elementary implications or conjunctions.
The split excludes exact native structural equivalence after the documented
normalization, not all semantic, curriculum or subgoal similarity. Erasing
universe levels is conservative and could exclude extra pairs. Family authorship
and a tiny hand-designed sample further limit external validity. No large-scale
out-of-distribution theorem-proving result is claimed.

## Evaluation rules

All BFS, heuristic and learned runs use the exact same bounded generator,
24-candidate cap, depth 8, 60 expansions, 400 candidate attempts, 12-second wall
budget and 3-second per-tactic timeout. BFS keeps FIFO and generator order;
heuristic uses the Phase 1 policy; learned uses learned candidate order with
the same handcrafted state-frontier score. Different visited states naturally
produce different pools; at the **same** state the available pool is invariant.
The first successful empty-goal path must pass fresh elaboration and transitive
axiom auditing to count as verified. A timeout is not a proof or a negative
mathematical label.

Native Aesop is explicitly a separate Mathlib reference: one native `aesop`
call under the external time budget, with its own internal search and candidate
space. Its one external attempt and expansion cannot be interpreted as the
same unit of internal work as one ProofLab tactic. No Aesop success is attributed
to the learned policy.

There are three repetitions per task and policy, with two workers. The initial
policy order rotates by theorem and repetition; repeats are collected
sequentially. Source/model remain fixed. Wall time includes process startup and
fresh audit, and shares host resources; it is not a dedicated-hardware speed
measurement. Structural effort is deterministic when no wall limit intervenes;
repeats mainly reveal timing/resource variability, not independent mathematical
samples.

The report exports every run, including failures, and per-theorem averages.
Success and paired effort differences have seeded 10,000-sample 95% percentile
bootstrap intervals using theorem clusters, retaining all three repeats together.
The intervals describe this hand-designed sample under a theorem-resampling
assumption; they do not correct family dependence, selection bias or multiple
comparisons. Effort on all tasks includes censored failures; common-verified
subsets are reported separately to avoid equating early failure with efficiency.
No model retuning is allowed after these outcomes are seen.
