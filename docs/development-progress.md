# Phase 1 development progress

This project was built independently in the existing `prooflab` checkout.
MathVerify was never used as a working directory or modified.

| Milestone | Delivered evidence |
|---|---|
| A — Formal foundation | Compatible pinned Lean 4.24.0 + Mathlib; 677-job dependency/project build; uv/npm locks; architecture decision |
| B — Native bridge | Persistent JSON/FIFO session; genuine goals/contexts; full saved-state restoration; invalid-step integration tests |
| C — Systematic search | Bounded BFS; structural candidates; actual branching and failures; reconstructed independently audited proofs |
| D — Heuristic/retrieval | Deterministic best-first policy; 24 named declarations; conclusion/context matching; generic order and arithmetic regressions |
| E — Interactive application | Genuine trace playback, inspector, local computation, comparison, exports, local KaTeX, responsive themes; real Chromium tests |
| F — Research | Three preserved 192-run experiments; 64 tasks, four subjects, fixed splits; raw traces, CSV/JSONL, plotted measurements |
| G — Learning foundation | Typed ranking interface; real split-labelled trajectories; off-path label policy; no trained-model claims |
| H — Portfolio | English README, real screenshots/GIF, documentation, CI/Pages workflows and checkpoint pushes; public visibility/Pages require owner-side GitHub settings |

The first experiment exposed natural-number pretty-notation detection (`ℕ`
versus `Nat`); the second exposed a conclusion/context mismatch for order
antisymmetry. Both were fixed as general structural retrieval rules, with
targeted unit and independently checked integration regressions. No task was
removed or given a hardcoded answer. The previous raw runs remain intact.

The final comparison uses the same statement dataset and computational budgets.
Its code commit, exact outcomes and limitations are in
`docs/experimental-results.md`. The reserved split is not blinded and was
visible during engineering; these are initial descriptive experiments.

Public release settings remain external blockers: the configured GitHub
integration can push source and read Actions, but receives HTTP 403 for repository
visibility changes and Pages access. The existing repository remains private.
Hosted CI received no runner because GitHub reported account billing/spending
limits; this is not an executed test failure. Local validation is independent.
