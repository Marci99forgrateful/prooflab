# Experimental results — Phase 1

These numbers are generated from actual completed runs. No unexecuted result is included.

## Frozen final experiment

- Code commit: `45322e084527600b9706510fe421c26f3da7e5eb`.
- Lean: `leanprover/lean4:v4.24.0`; Mathlib: `f897ebcf72cd16f89ab4577d0c826cd14afaafc7`.
- Dataset SHA-256: `64db27492b0396ad2a418d4f3c097a7343a52f20128a4f1768a1a73fd747ebe2`.
- Started: `2026-10-20T00:28:00.148850+00:00` (UTC).
- Host: `Linux-6.18.55-x86_64-with-glibc2.41`, `x86_64`, 5 visible CPUs; peak memory not measured; Lean allocation limit 2048 MB.
- Python: `3.12.14`; seed: `0 (deterministic)`; workers: 2.
- Budget: `{"max_attempts": 400, "max_candidates": 24, "max_depth": 7, "max_expansions": 60, "tactic_timeout_s": 3, "timeout_s": 12.0}`.
- 64 tasks: 48 development and 16 reserved held-out; four mathematical subjects.

## Overall results

| Strategy | Verified | Success | Mean wall s | Median wall s | Mean expansions | Mean candidates | Resource limits | Execution errors |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Breadth-first | 59/64 | 92.19% | 3.315 | 3.337 | 9.23 | 38.47 | 5 | 0 |
| Heuristic best-first | 59/64 | 92.19% | 3.288 | 3.301 | 7.33 | 30.66 | 5 | 0 |
| Native Aesop | 41/64 | 64.06% | 2.822 | 3.230 | 1.00 | 1.00 | 0 | 0 |

Aesop is one separately identified native automation attempt, not a ProofLab algorithm. All strategies share the overall and per-call caps; Aesop uses one call.

## By mathematical subject

| Subject | BFS | Best-first | Native Aesop |
|---|---:|---:|---:|
| Logic | 15/16 | 15/16 | 16/16 |
| Order | 16/16 | 15/16 | 4/16 |
| Algebra | 16/16 | 15/16 | 10/16 |
| Sets | 12/16 | 14/16 | 11/16 |

## Reserved held-out split

| Strategy | Development | Held-out |
|---|---:|---:|
| Breadth-first | 46/48 | 13/16 |
| Heuristic best-first | 46/48 | 13/16 |
| Native Aesop | 34/48 | 7/16 |

The reserved split is not a blinded evaluation. Statements were visible during engineering, including pilot failure analysis. No model was trained. These numbers do not establish strong out-of-distribution generalization.

## Where the successful proofs came from

| Strategy | Constructed derivation | One-step lemma | Specialized tactic | Native automation |
|---|---:|---:|---:|---:|
| Breadth-first | 40 | 12 | 7 | 0 |
| Heuristic best-first | 40 | 12 | 7 | 0 |
| Native Aesop | 0 | 0 | 0 | 41 |

A multi-step proof can still include a specialized tactic; the exact script and per-attempt category are retained. This table does not claim new mathematics.

## Paired effort and interpretation

On the **57 tasks verified by both original strategies**, BFS expanded 214 states in total and best-first expanded 161. This is a descriptive search-effort comparison, not a statistically established wall-clock speedup.

Best-first solves some tasks that BFS misses, and misses some that BFS solves. In particular, inspect `set_inter_monotone`, `set_union_elim`, `eq_pair` and `symmetric_chain`. A smaller heuristic score is not proof evidence or a guarantee of better scheduling.

Lean startup and independent rechecking dominate short runs. Wall times include failures; fast failed searches must not be interpreted as better proof discovery. Concurrent workloads share the host. No confidence intervals or novelty claims are made from one run.

## Preserved original-search failures

| Task | Strategy | Actual termination |
|---|---|---|
| `distribute` | Heuristic best-first | `resource_limit:expansions` |
| `distribute` | Breadth-first | `resource_limit:expansions` |
| `eq_pair` | Heuristic best-first | `resource_limit:attempts` |
| `set_distribute` | Heuristic best-first | `resource_limit:expansions` |
| `set_distribute` | Breadth-first | `resource_limit:expansions` |
| `set_inter_comm` | Heuristic best-first | `resource_limit:expansions` |
| `set_inter_comm` | Breadth-first | `resource_limit:expansions` |
| `set_inter_monotone` | Breadth-first | `resource_limit:expansions` |
| `set_union_elim` | Breadth-first | `resource_limit:expansions` |
| `symmetric_chain` | Heuristic best-first | `resource_limit:expansions` |

These are incomplete bounded searches, never mathematical counterexamples. All native automation failures are also retained in the raw results.

## Preserved pilot history

| Run | Code commit | BFS | Best-first | Native Aesop |
|---|---|---:|---:|---:|
| phase1-v1 | `f91bb03a141d` | 53/64 | 54/64 | 41/64 |
| phase1-v2 | `a16b54fe84b7` | 57/64 | 58/64 | 41/64 |
| phase1-v3 | `45322e084527` | 59/64 | 59/64 | 41/64 |

The first pilot exposed `ℕ`/`Nat` detection; the second exposed a general conclusion/context feature mismatch for antisymmetry retrieval. Both received generic fixes and regressions. Dataset and limits stayed fixed. No failed task was removed, no complete answer was inserted into candidate generation, and the prior raw evidence remains available.

## Reproduce and inspect

Raw run: [`experiments/phase1-v3`](../experiments/phase1-v3). See [methodology](benchmark-methodology.md) for the command and scope.

![Actual measured results](assets/benchmark-results.svg)

Exportable figures: [SVG](assets/benchmark-results.svg), [PNG](assets/benchmark-results.png), [PDF](assets/benchmark-results.pdf).
