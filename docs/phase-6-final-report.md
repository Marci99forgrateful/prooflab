# ProofLab v0.6.0 — Adaptive Hybrid Proof Search

Phase 6 implements a working adaptive hybrid over genuine Lean states, with broader development-only training, bounded callable expression synthesis, explicit candidate allocation and an integrated research explorer. **The primary learned policy does not outperform the strongest prior ProofLab algorithm in this experiment.** Deterministic synthesis and staged generation give useful observed capability gains; these are not attributed to machine learning.

The review branch is `feature/phase6-adaptive-hybrid`, based on Phase 5 commit `4cc061e`. [Draft PR #5](https://github.com/Marci99forgrateful/prooflab/pull/5) targets `feature/phase5-type-directed-retrieval`. No merge, site deployment, MathVerify change, paid AI API, pretrained model, hosted inference or GPU is part of this delivery.

## Completed algorithms and interface

The new provider combines expanded P4 symbolic generation, the existing 116-declaration native index, typed context subterms and bounded expression closure. Generated partial applications become callable; nested heterogeneous products and explicit image/preimage constructions retain actual inferred types and derivations. Bounds cover depth, local seeds, term/function banks, branching, expression/type size and query time. Independent native integration tests verify curried/dependent/product/set constructions. Set-constructor feature tests are not counted as benchmark gains.

Hybrid selection protects expanded-baseline structural/specialized capabilities, reserves eligible novelty places and permits borrowing unused baseline capacity within the same cap of 24. Symbolic, hybrid and typed modes have explicit deterministic or trained context decisions. Staging delays retrieval for the first two non-existential expansions and retrieves immediately on existential goals. All strategies use one continuous search budget. Every actual tactic, native query, score and branch is charged to the engine; there is no extra-budget restart or hidden Aesop fallback.

Selection and execution are distinct: new policies use canonical Candidate metadata, unchanged P3 action scores and explicit tactic-string ties. Historical methods retain their original behavior. The [architecture](phase-6-architecture.md) describes controls, bounds and measurement scope; the [historical failure diagnosis](phase-6-diagnosis.md) links actual old failures to pinned source locations.

The Adaptive Proof Search Explorer adds all 1440 real recordings to the existing application. It shows native goals/context, structures, proposals/witnesses, mode costs, model components, selected/displaced actions, learned/deterministic relevance, actual scheduler ranks, native acceptance, trees, full-call/Lean/retrieval costs and complete proof audits. Real gains, regressions and universally unsolved tasks are inspectable side by side. One/two recorded repetitions, controller seeds, smaller budgets, full JSON export and finite loopback local computation work alongside the Phase 1–5 views. Unequal selected budgets are explicitly labelled.

Actual captures: [trees](assets/phase6-tree-comparison.png), [native witness](assets/phase6-native-witness.png), [learned decision](assets/phase6-learned-decision.png), [regression](assets/phase6-regression.png), [mobile](assets/phase6-mobile.png). These screenshots come from browser replay of canonical executions.

## Data, models and evidence boundary

There are 160 development statements in sixteen families and 48 new final statements in twelve combination families. A native reducible expression-graph audit compares all 208 new statements with 212 earlier statements, allowing alpha renaming and forall-binder permutation; it finds no duplicate pairs. Shared proof primitives and related mathematical structures remain. This is compositional evaluation on curated families, not proof-schema independence or broad out-of-domain generalization.

Actual development collection supplies 480 source searches, 212 source states and 3169 executed candidate alternatives. The 1964 preference pairs use verified actions over actual rejected applications, or lower cost among two audited completions. Valid unknown/censored actions are not usefulness negatives. Three apparent closures rejected by fresh Lean checking remain tool-error unknowns. Candidate relevance trains on 120 tasks; forty whole-family tasks supply selection validation. A separate 480-run, equal-budget fixed-mode collection provides 347 verified conditional-cost targets. Failed/censored modes are retained but excluded from cost regression.

Linear relevance wins development validation (loss 0.460912 versus best boosted mean 0.527345). The selected cost controller is 48 depth-two boosted trees (validation MSE 1.202460 versus ridge 1.229892). Its final fit uses permitted 160-task outcomes, while relevance retains its 120-task fit to avoid contaminating controller validation. The exported fully linear control uses the same relevance and a ridge controller; applicability-only relevance holds the primary controller fixed. Primary seed zero and two sensitivity seeds are fixed before testing. See [data](phase-6-data.md), [models](phase-6-model.md), [protocol](phase-6-protocol.md) and [saved parameters](../models/phase6).

The final executable/model state is committed at `f239b2b`, with freeze `6c204c2` before any final proof search. All 1440 run records identify that freeze commit. The boundary is a locally committed freeze; it was pushed during the campaign and is not external blinded preregistration. Initial source collection (`339b8f1`), matched selector collection (`689ea1d`), later pre-test guards and unused diagnostic fits retain their own provenance. No final result changes the model, generator, threshold, seed or test membership.

## Verified experimental findings

The 1440-run matrix includes two repeats of ten main arms, allocation/synthesis/objective/tie controls, four smaller-budget arms and two preregistered controller-seed arms. Primary ProofLab arms share eighteen seconds, 600 attempts, eighty expansions, depth twelve and cap 24. Small arms share ten seconds, 240 attempts and forty expansions. Aesop/grind are separately identified two-second opaque calls; their internal effort is not equated to one ProofLab primitive inference.

| Policy | Verified theorems in each repeat | Verified runs | Mean attempts/calls | Full-call wall s |
|---|---:|---:|---:|---:|
| Strongest prior expanded P4/P3 | 23/48 | 46/96 | 165.60 | 5.328 |
| Phase 5 deterministic typed | 9/48 | 18/96 | 536.33 | 7.510 |
| Phase 5 learned retrieval | 9/48 | 18/96 | 537.15 | 7.471 |
| Naive combined pool | 18/48 | 36/96 | 398.85 | 7.696 |
| Deterministic context hybrid | 27/48 | 54/96 | 238.75 | 6.884 |
| Primary learned adaptive hybrid | 22/48 | 44/96 | 198.35 | 6.325 |
| Fully linear adaptive control | 23/48 | 46/96 | 256.83 | 7.260 |
| Deterministic staged hybrid | 30/48 | 60/96 | 205.33 | 6.483 |
| Native Aesop reference | 23/48 | 46/96 | 1 external call | 3.848 |
| Native grind reference | 26/48 | 52/96 | 1 external call | 3.634 |

All repeated arms have identical status, proof, attempt and expansion results across the two runs; timings vary. There are **647 independently audited successful runs**, no execution-error results and no failed retrieval round trips in this final matrix. Finite attempt/expansion/depth/time failures and seven statements unsolved by every registered arm remain. [Complete measured results](phase-6-results.md) include every arm, per-theorem/per-family results, proof lengths, Lean/verification/retrieval/inference times, resource terminations and uncertainty; [raw evidence](../experiments/phase6/evaluation-v1) preserves every tree.

The three predeclared primary success contrasts use theorem repeat averages and 10,000 paired bootstrap draws, seed 2718:

| Left minus right | Success difference pp | Theorem 95% interval | Equal-family 95% interval |
|---|---:|---:|---:|
| Learned minus expanded P4 | −2.083 | [−14.583, +10.417] | [−18.750, +12.500] |
| Deterministic minus expanded P4 | +8.333 | [−6.250, +22.917] | [−12.500, +29.167] |
| Learned minus deterministic | −10.417 | [−20.833, 0.000] | [−20.833, 0.000] |

No primary interval establishes a positive learning gain. On eighteen common-verified learned/P4 tasks, learning uses **37.611 extra attempts** on average (theorem interval +2.333 to +91.611). Lower all-run means can reflect early failure and are not proof-efficiency gains. The learned controller gains four theorems and loses five against P4; against deterministic allocation it gains one and loses six. Seeds one/two solve twenty/twenty-one, so changing the registered seed does not recover a win.

The staged policy's observed 30/48 is promising algorithmic evidence. A separately labelled **post-hoc** comparison against P4 gives +14.583 pp, theorem interval [0.000, +29.167] and family interval [−4.167, +33.333]; these do not establish a general positive difference. It gains ten statements and loses three; on twenty common-verified tasks it uses 11.850 extra attempts and about 0.469 additional full-call seconds. Leaving out any one family keeps its descriptive point positive (+11.364 to +20.455 pp), but related task construction and small family count still limit inference. The original preregistered summary is preserved; [sensitivity.json](../experiments/phase6/evaluation-v1/sensitivity.json) labels this additional analysis.

## What the controls explain

Improved synthesis adds **six verified statements** over deterministic allocation with the old constructor (27/48 versus 21/48), across callable-composition, dependent-graph and ternary-witness families, with no observed losses. It creates actual previously unavailable typed witnesses. Deterministic allocation also beats naive union descriptively (27/48 versus 18/48); merely exposing more compatible actions is insufficient.

Context-dependent and fixed-four novelty reserves produce identical pools/schedules at all 1611 matched prefixes. The quota difference is not binding once unused baseline capacity can be borrowed. Usefulness versus applicability-only relevance likewise produces identical pools/schedules at 1434 matched prefixes and identical outcomes/attempts. Neither ablation demonstrates an effective gain here. Candidate-score training improvements are not silently promoted to search improvements.

Between new learned/deterministic policies, 1586 exact prefixes show no shared-action score or relative-order disagreements; 1270 have identical selected membership and no identical-pool order disagreements. Canonical ties remove the old accidental retriever/scheduler coupling. Historical P4 tie changes alone do not change success.

The [error analysis](phase-6-error-analysis.md) follows real witnesses and failed trees. A learned selector can choose symbolic mode by a tiny conditional-cost margin and never retrieve a decisive curried witness. In a set-identity regression it accepts the first baseline proof action but never expands that successor before its global state budget expires. Preserving candidates is not preserving completed proofs. New symbolic capabilities and staging explain observed gains more defensibly than learning does.

## Resources, validation and limitations

Final CPU fitting takes 18.755 seconds wall and 18.950 seconds user+system CPU, with trainer high-water RSS 510156 KiB, using one BLAS/OpenMP thread. The actual two-worker evaluation campaign takes 4494.723 seconds including archive processing. Recorded coordinator CPU sums to 824.826 seconds and partial live-session CPU to 5730.810 seconds; neither includes complete independent-audit process CPU. The largest summed session-process RSS high-water bound is 2227664 KiB, not a simultaneous physical-memory peak. Shared-host configuration is in [hardware evidence](../artifacts/phase6-hardware.json). Whole development-collection campaign CPU/wall is not fully instrumented and is not claimed.

The canonical final trace archive compresses 4,414,981,360 original JSON bytes to 213,099,647 bytes, with per-file raw/compressed SHA-256 indices. Static export copies these exact gzip archives into ignored build assets. Five [exported actual proofs](../examples/phase6) are freshly rechecked again, with [new audit records](../artifacts/phase6-example-audits.json). Previous frozen inventories and all 3493 existing tracked research artifacts are unchanged from Phase 5; [preservation evidence](../artifacts/phase6-preservation.json) records the check.

Final local validation passes **131 Python tests** (including 24 browser tests), **17 Node tests**, the **681-target Lean build**, Ruff lint/formatting, Prettier, Vite build and strict Mypy on 44 source files. There are no test failures/errors/skips; two existing dependency warnings remain. These checks cover old and new functionality. Exact outcomes and scopes are recorded in [local validation](../artifacts/phase6-validation.json) and [hosted CI](../artifacts/phase6-hosted-ci.json). The frozen-source hosted run passed 122 tests with no failures/errors/skips before final delivery assets; the complete delivery commit `d544934` then passes **131 tests with no failures/errors/skips** in [hosted run 39634100413](https://github.com/Marci99forgrateful/prooflab/actions/runs/39634100413). The final evidence-only follow-up retains that code. [Reproduction commands](phase-6-reproduction.md) rebuild, refit from permitted saved data, rerun a new versioned evaluation and regenerate reports/plots/replay.

Remaining scientific limitations include success-conditioned missing costs, root-only fixed-mode targets applied to greedy switching, source/budget shifts, reused development validation, coarse context partitions, curated related families, bounded synthesis/index/search, partial CPU/RSS and shared-host timing. Bootstrap intervals are descriptive finite-sample uncertainty, not general theorem-proving guarantees or multiplicity-adjusted discovery claims. No final result is used to retune.

The most defensible next learning study would collect matched intermediate-state mode trajectories and model **bounded completion under a specified policy/budget** separately from conditional completion cost, retaining censored mathematical outcomes as unknown. It should encode construction demand more directly and test any allocation/staging change on another frozen benchmark. This is future work; Phase 6 preserves the present negative ML finding and the implemented algorithmic gains.
