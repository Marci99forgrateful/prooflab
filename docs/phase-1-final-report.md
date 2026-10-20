# ProofLab — Phase 1 delivery report

Date: 2026-10-20. Package version: **0.1.0**. The delivered source is on the
repository's default branch **main**, with a version tag identifying the final
delivery commit. Resolve the exact checkout SHA with `git rev-parse HEAD`.
The frozen measured implementation is
`45322e084527600b9706510fe421c26f3da7e5eb`; later commits package the evidence,
interface refinements and documentation.

## Delivery status

**A functioning, independently tested local proof-search laboratory is
delivered. Public portfolio publication is still blocked by GitHub integration
permissions.** The existing repository is private; it was inspected and its
initial work preserved. Source checkpoint pushes to
[Marci99forgrateful/prooflab](https://github.com/Marci99forgrateful/prooflab)
succeeded. No public demo URL is claimed. MathVerify was never modified or used
as a working directory.

## Implemented and verified

- Lean 4.24.0 and pinned Mathlib `f897ebcf72cd16f89ab4577d0c826cd14afaafc7`,
  committed Lake/uv/npm locks, reproducible bootstrap and architecture record.
- Persistent native Lean tactic sessions over private JSON/FIFOs, genuine
  goals/local hypotheses, normalized expression structure, full elaboration
  snapshot restoration and invalid-candidate isolation.
- Original deterministic bounded breadth-first and heuristic best-first search,
  a shared structural candidate generator, 24-declaration curated Mathlib index,
  resource bounds, cancellation, actual attempt trees and proof reconstruction.
- A fresh Lean invocation for every accepted proof, followed by transitive
  axiom auditing. Only `propext`, `Classical.choice`, `Quot.sound` are accepted.
  Admitted and arbitrary-axiom proofs are rejected in explicit tests.
- A local computation API accepting only finite repository-owned task IDs;
  a polished browser application with real trace replay, node inspection,
  exact goals, proof download, complete JSON and SVG export, themes, responsive
  layouts, and same-task algorithm comparison.
- 64 statement-only benchmark tasks across logic, orders, algebra and sets;
  48 development and 16 reserved held-out. Three complete 192-run experiments
  are preserved, including pilot failures and generic fixes.
- Real screenshots/GIF, research figures in SVG/PNG/PDF, raw JSON/CSV/JSONL,
  typed ranking-policy extension points and split-labelled training trajectories.

## Genuine mathematical examples

All eight [exported source artifacts](../examples/generated) were independently
compiled and axiom-audited again after export. They are outputs, never search
inputs or per-task templates.

| Example | Actual discovered path |
|---|---|
| Implication composition | `apply hqr; apply hpq; assumption` |
| Universal consequence | introduction, hypothesis application, universal premise |
| Generic order antisymmetry | `apply le_antisymm; assumption; assumption` |
| Three-step inequality chain | two transitivity applications and assumptions |
| Algebraic rewriting | rewrite a supplied equality, then use the monoid identity |
| Binomial expansion | specialized Mathlib `ring`, explicitly categorized |
| Intersection monotonicity | two introductions, constructor, implication, projections |
| Union elimination | introductions, genuine disjunction elimination and branch applications |

The binomial example is native polynomial automation, not attributed to a
novel original proof-search method. Standard mathematics is not claimed novel.

## Actual benchmark results

Final run: [`experiments/phase1-v3`](../experiments/phase1-v3).
Each policy attempts all 64 tasks under the same 12-second total, 3-second
per-tactic, depth-7, 60-expansion, 400-attempt and 24-candidate caps.

| Strategy | Independently verified | Median wall time | Mean expanded states |
|---|---:|---:|---:|
| Breadth-first | 59/64 (92.19%) | 3.337 s | 9.23 |
| Heuristic best-first | 59/64 (92.19%) | 3.301 s | 7.33 |
| Native Aesop reference | 41/64 (64.06%) | 3.230 s | 1.00 external invocation |

The two original policies each produce 40 constructed derivations, 12 one-step
lemma solutions and seven specialized one-step proofs. Their successful task
sets differ. On the 57 tasks both solve, BFS expands 214 states versus 161 for
best-first. Each original policy solves 13/16 reserved tasks. There are zero
execution errors in the final experiment; incomplete searches remain in the
raw data. Native Aesop's internal expansion count is not instrumented.

These are initial descriptive results. The reserved split was visible during
engineering and is not a blind generalization test. No model was trained.
Concurrent timings include Lean startup and fresh proof checking. No claim of
statistical significance, universal heuristic superiority or mathematical
novelty follows. See the full [benchmark report](experimental-results.md).

## Validation and visual evidence

The local acceptance run contains **41 Pytest tests**, including **11 actual
Chromium browser tests**, plus **four Node frontend tests**. Exact final run
outcome is recorded alongside this report in `experiments/validation.json`.
Lean compilation, Ruff checks/format, strict Mypy, frontend production build
and Prettier checks are also required. All eight exported Lean examples were
recompiled separately with the independent axiom audit.

The tests cover actual generated proof checking, unseen renamed statements,
restoration after failed tactics, forbidden/admitted and transitive-axiom
rejection, candidate generation/retrieval, budgets, timeouts/cancellation,
dataset and raw-report consistency, API execution boundaries, new computation
in the browser, replay and inspection, exports, responsive layouts, and a
static deployment under a subdirectory with no backend or external assets.

Real evidence: [workspace](assets/proof-explorer.png),
[active recorded replay](assets/active-search.png),
[animation](assets/proof-search.gif),
[comparison](assets/algorithm-comparison.png),
[benchmarks](assets/benchmarks.png),
[mobile](assets/mobile.png), [dark theme](assets/dark-theme.png).

## Publication and exact remaining actions

The GitHub API confirmed a private repository and `main` as its default branch.
A request to make it public returned **HTTP 403, "Resource not accessible by
integration"**. Pages access returned the same permission error. The integration
can push source and workflows but cannot apply these repository settings.

The owner must:

1. Open repository **Settings → General → Danger Zone → Change repository
   visibility → Public**. This implements the explicitly requested public
   portfolio visibility; no source overwrite or new repository is necessary.
2. Open **Settings → Pages → Build and deployment → Source: GitHub Actions**,
   then run **Publish authentic trace demo** from Actions. Its built artifact
   is already tested for static subdirectory hosting and needs no paid backend.
3. Rerun **Verify ProofLab** when account Actions access is available. The
   hosted job did **not start** because GitHub reported failed account payments
   or a spending limit. No test step ran, so its red status is infrastructure
   failure, not executed test failure. Evidence:
   [recorded hosted run](https://github.com/Marci99forgrateful/prooflab/actions/runs/39347789314).
4. Optionally set the repository homepage to the URL returned by the successful
   Pages deployment and add topics: `lean4`, `theorem-proving`,
   `automated-reasoning`, `formal-verification`, `proof-search`, `mathlib`.

No public website, successful hosted CI or changed visibility is claimed before
those actions actually succeed. Local operation does not require paid AI or
paid hosting. The prepared cloud environment has tested `install_script` and
`start_skill` saved as configuration drafts; review/save and publish it in
environment settings to activate the reusable snapshot. Draft saving is not
publication or proof of a fresh-task restore.

## Local startup

```bash
cd prooflab
bash scripts/bootstrap.sh
uv run --frozen prooflab serve
```

Open the server's printed local address. Default recorded playback is clearly
labelled; choose **Use live search** for a new actual Lean computation. The
bootstrap was run repeatedly without changing tracked files. Startup readiness
requires both the health response and an independently verified new search,
not merely a process or listening port.

## Tested limits and remaining research

The current transport is POSIX-only. Linux is tested; Windows is not supported
by this transport and has **not** been tested. macOS is also untested. The app
requires its checkout, including the Lean project, dataset and static assets.

This is an elementary, bounded fragment, not arbitrary advanced theorem
proving. Retrieval is curated and feature based, not a complete type-indexed
Mathlib search. Semantic state canonicalization is deliberately incomplete:
exact-prefix identity avoids unsafe merging but retains duplicate work.
Subtle equivalent-theorem leakage is not automatically eliminated.

Live computation completes before animated trace playback; candidate-level
streaming is future work. Tree rendering is capped, while JSON preserves the
complete trace. No formal verification of the search implementation itself,
trained model, blinded benchmark, Windows support or public deployment has
been claimed.

The recommended next research milestone is a **small locally trained ranking
policy**, trained only on development trajectories and evaluated on a new,
unseen theorem-family split under the same candidate pool and budgets. This
should follow the [ML roadmap](ml-roadmap.md), with no changes to Lean's trusted
checking boundary.
