# Phase 4 — Related work and source-code investigation

Access date: 2026-10-20. This report was written before implementing the Phase 4 algorithms. Pinned source versions, file URLs, SHA-256 digests, license locations and unsuccessful discovery attempts are in [`research/phase4/sources.json`](../research/phase4/sources.json). The machine-readable bibliography is [`bibliography.json`](../research/phase4/bibliography.json). All source comparisons concern the recorded commit, which can be newer than ProofLab's installed Lean 4.24.0 / pinned Mathlib. No external source code, benchmark solutions or model weights were copied into the implementation.

## Method and evidence boundaries

We started with the user's named systems, followed implementation references to Lean core library search, Evariste, E/Vampire, CoqHammer, LeanExplore and Kimina, and checked contemporary 2024–2026 changes. For each repository we resolved its default-branch commit, enumerated its tree, downloaded selected algorithm modules and its own license, and read the relevant scheduling/interaction/reconstruction code. This is targeted source inspection, not a full correctness audit. An initial name search found an unrelated `mcjung1/leanexplore`; it is explicitly excluded from technical evidence. Failed repository guesses remain recorded rather than invented. The actual LeanExplore repository was identified from PyPI project metadata.

**S** below means a direct source-code observation. **R** means the authors' paper/README description, not a local reproduction. **P** means a proposed independent ProofLab adaptation. Paper URLs are provided even where our network policy prevented direct arXiv access; repository citations and, for DeepSeek V2, the full repository-hosted PDF supplied evidence. We do not claim to have read every linked full paper. Publication claims are distinguished from the newer inspected implementation. No numerical cross-system leaderboard is scientifically justified here.

## Comparative research matrix

| System | Search objects / scheduling | Learned signal | Premises | Practical relation to ProofLab |
|---|---|---|---|---|
| Aesop | native AND/OR rules; safe prefix then priority queue | annotated rule probabilities | registered rules/indexes | installed external reference; independent scheduler concepts |
| grind | congruence classes, E-matching, theory propagation | none required | patterns/local facts | installed separate symbolic tactic |
| Duper | given-clause higher-order superposition | none required | explicit hints/local facts | conceptual saturation comparison |
| Lean-auto / LeanHammer | translate, select, ATP portfolio, reconstruct | optional learned premise selection | relevance / external selector | no remote selector; trust reconstruction boundary |
| ReProver / InternLM | best-first tactic states | neural tactic log probability + retrieval | learned retriever / corpus | separate actor and state scheduler |
| Lean Copilot | suggestions and Aesop-guided interactive search | pretrained tactic/premise model | neural retrieval | interface concepts only |
| DeepSeek V1.5 | prefix tree, RMaxTS/UCB exploration | RL policy and exploration rewards | language model context | study, no large model deployment |
| DeepSeek V2 / Goedel V2 | recursive decomposition / whole-proof correction | synthetic supervised data + verifier RL | large model knowledge | concept only on this CPU host |
| TacticToe | tactics and AND subgoals, policy/value search | proof traces / learned value and policy | learned tactic arguments | CPU-scale precedent, no code port |
| DeepHOL | HOL Light goal graph, bounded BFS | tactic and premise scores | theorem database, accessibility | proof-log and split methodology |
| HTPS / Evariste | hyperedges, simulations and backups | online policy/critic | neural tactic model | coupling/cycle caution; CC-BY-NC source |
| Sledgehammer / CoqHammer | relevance + ATP + reconstruction | optional premise learning | MePo/MaSh / learned predictions | local relevance and certified reconstruction |
| E / Vampire | saturation active/passive clauses | separate learned-clause research | clause indexes/redundancy | no naive state deduplication |
| Pantograph / REPL / LeanDojo | native snapshot/interaction interfaces | supplied by client | client-dependent | preserve metavariable context |
| LeanExplore | declaration retrieval | embeddings / reranker optional | indexed Lean declarations | no hosted runtime service |

## Detailed dossiers

### Aesop

**Objective, authors and publication:** Limperg and From, Aesop: White-Box Best-First Proof Search for Lean, CPP 2023. Lean symbolic backward automation.

**R — architecture, states and scheduling:** AND/OR rule applications, native goals and saved metavariable state; normalization and safe rules precede unsafe alternatives. Goal probabilities guide best-first scheduling.

**S — inspected implementation:** Queue.lean ActiveGoal.le orders by priority then expansion/insertion iteration; Main.lean expandNextGoal/searchLoop enforce goal and rule-application limits and reconstruct a proof. ExpandSafePrefix.lean extracts safe progress. Source pin [`29c64c56cc38`](https://github.com/leanprover-community/aesop/tree/29c64c56cc38211d39b306db2df11701e3d3de11); checked commit date 2026-10-19T13:37:15Z.

**Candidates, learning and supervision:** Registered rule sets and discrimination indexing; rule success percentages are user/default annotations, not a trained state-value network. No ML training corpus.

**Evidence and limits:** Published Mathlib automation experiments motivate structured rule search; they do not measure our finite candidate generator. Our installed pinned Aesop differs from the current inspected commit.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Independent state scheduling and explicit queue decisions; retain our fresh proof audit. Integrate only already-installed Aesop as an external reference.

### Lean core: grind and library search

**Objective, authors and publication:** Lean FRO and Lean contributors; evolving reference implementation, inspected 2026 revision. Native symbolic congruence reasoning.

**R — architecture, states and scheduling:** Congruence classes of terms, equality explanations, E-matching instantiations and theory propagation, with controlled case splitting; this is not tactic-sequence BFS.

**S — inspected implementation:** Grind/Core.lean removeParents/reinsertParents and addEqCore maintain congruence information; EMatch.lean handles matching infrastructure. LibrarySearch.lean provides discharge/search infrastructure, including a try? discharger in this current revision. Source pin [`6172398c3a0a`](https://github.com/leanprover/lean4/tree/6172398c3a0a2b1506252f4df4eb68c29e5b2695); checked commit date 2026-10-20T11:39:59Z.

**Candidates, learning and supervision:** Theorem patterns and local facts; symbolic search has no learned parameters. Congruence closure is not a neural heuristic.

**Evidence and limits:** Implementation and documented capabilities, not an independently reproduced aggregate score. Current core is newer than our Lean 4.24.0.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Run the installed grind locally as a separately labelled secondary external tactic, if available; adopt resource and explanation design concepts without changing Lean.

### Mathlib tactics and retrieval

**Objective, authors and publication:** Mathlib community; evolving library and tactic infrastructure. Library-scale certified mathematical automation.

**R — architecture, states and scheduling:** Declaration types, namespace/import accessibility and tactic-specific indexes; specialized normalizers such as ring solve a richer internal problem than one ProofLab candidate count expresses.

**S — inspected implementation:** ApplyFun.lean is meta-level function application infrastructure; ApplyWith.lean elaborates application options. Current library-search core has moved to Lean: do not attribute unrelated Algebra/Exact modules to retrieval. Source pin [`bbe3db288201`](https://github.com/leanprover-community/mathlib4/tree/bbe3db288201b39ef92689278906d3bf6d45c291); checked commit date 2026-10-20T08:03:43Z.

**Candidates, learning and supervision:** Public declarations selected by types/discrimination indexes; ring is symbolic normalization. Our 24-lemma token index is dramatically smaller and not type unification.

**Evidence and limits:** Library tests establish behavior, not a general learned-prover benchmark. Dependency version and imports change candidate availability.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Preserve pinned Mathlib. Independently study type/head relevance and local rewrite normalization in a separate generator arm.

### Duper

**Objective, authors and publication:** Joshua Clune, Yicheng Qian and Alex Bentkamp; open-source higher-order superposition prover. Native proof-producing saturation.

**R — architecture, states and scheduling:** Active/passive clause sets, literal selection, simplification and given-clause saturation. Forward demodulation/subsumption and superposition operate over clauses, not restored tactic prefixes.

**S — inspected implementation:** ProverM.lean exposes active/passive sets and inference indexes; Selection.lean selects negative/maximal/ground literals. Saturate.lean inferenceRules lists superposition, equality factoring, clausification and higher-order fluid rules; termination checks include time, iterations and heartbeats. Source pin [`5940907b9581`](https://github.com/leanprover-community/duper/tree/5940907b9581beb2fd08b9d0b0682c2b0c9c15b8); checked commit date 2026-09-28T04:58:10Z.

**Candidates, learning and supervision:** Explicit supplied facts, local facts with [*], symbolic portfolios; no trained frontier network in inspected files.

**Evidence and limits:** README explicitly warns premise relevance matters and needs minimal hints; portfolio instances divide resources. Not locally installed or benchmarked here.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Conceptual comparison and independent queue engineering only. Adding a new toolchain/dependency would confound this experiment.

### Lean-auto

**Objective, authors and publication:** Yicheng Qian; Lean-auto, arXiv:2505.14929, 2025. Translation and external/native ATP interface.

**R — architecture, states and scheduling:** Monomorphization from dependent types into higher-order logic and deep embedding; native Duper can reconstruct, while some external SMT/TPTP modes do not reconstruct.

**S — inspected implementation:** Tactic.lean collectLctxLemmas/collectUserLemmas collect inputs; Translation/LamReif.lean contains reification tables and checker statistics. Source pin [`6544cf60e89e`](https://github.com/leanprover-community/lean-auto/tree/6544cf60e89e363a9e889f6bc88762709ac18b52); checked commit date 2026-09-28T04:58:39Z.

**Candidates, learning and supervision:** User hints and preprocessing rather than a tactic policy; no learned training data required by the translation layer.

**Evidence and limits:** Reported nontrivial examples do not establish equivalence to bounded ProofLab. Unreconstructed external success is incompatible with our audit boundary.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Study premise visibility and certified reconstruction. Do not enable untrusted external answers or install external binaries.

### LeanHammer

**Objective, authors and publication:** Joshua Clune and collaborators; evolving 2025–2026 hammer implementation. Premise selection plus portfolios of automation and reconstruction.

**R — architecture, states and scheduling:** Combines premise selection, translation, external ATPs and native reconstructors. Current README lists cloud premise selection and local Sine Qua Non, Aesop, Duper, grind and Lean-SMT.

**S — inspected implementation:** DuperCore.lean getDuperCoreLemmas selects facts from solver unsat cores and runDuperPortfolioMode reconstructs; AutoExtension.lean querySMTForHints exports/query hints. Source pin [`93734d62412e`](https://github.com/JOSHCLUNE/LeanHammer/tree/93734d62412e5af695439eab116efcece30e80a9); checked commit date 2026-10-13T00:00:25Z.

**Candidates, learning and supervision:** Symbol/relevance filtering or externally hosted premise selection; distinct from standalone native symbolic search. Hosted inference is not used here.

**Evidence and limits:** Current README supports Lean 4.20–4.34; pinning source is essential. No reproduction of its performance.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Local symbol relevance is feasible, cloud premise selection excluded; compare ideas, do not silently label hammer a native fixed-candidate baseline.

### LeanDojo / ReProver

**Objective, authors and publication:** Kaiyu Yang and coauthors, LeanDojo: Theorem Proving with Retrieval-Augmented Language Models, NeurIPS 2023. Retrieval-augmented tactic generation and best-first search.

**R — architecture, states and scheduling:** Lean tactic states and directed search edges; best-first priority uses cumulative tactic log probability. Retrieval restricts to accessible premises.

**S — inspected implementation:** prover/search_tree.py InternalNode.priority returns cumulative_logprob; out_edges recomputes status/distance. proof_search.py manages the best-first expansion and LeanDojo interaction. Source pin [`fd6d99c01e8b`](https://github.com/lean-dojo/ReProver/tree/fd6d99c01e8bd8fd8f3fd1de4cd0bc4a7f158eaa); checked commit date 2025-01-30T13:34:20Z.

**Candidates, learning and supervision:** Supervised Mathlib proof-state/tactic examples, dense premise retrieval and a language-model generator. Random and novel-premises splits test different generalization.

**Evidence and limits:** Reported benchmark performance depends on models, training library and search time. README evaluation requests GPU resources; no such model is run here.

**Availability and license:** Public source; API classification `MIT`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Separate candidate policy from frontier value, preserve theorem/family split and record accessible candidates. Independently implement a tiny state model, not ReProver weights.

### Lean Copilot

**Objective, authors and publication:** Peiyang Song, Kaiyu Yang, Anima Anandkumar, arXiv:2404.12534, 2024. Interactive neural suggestions and automation.

**R — architecture, states and scheduling:** Models consume pretty-printed tactic goals; suggestion generation, premise selection and Aesop-assisted proof search combine interaction and native verification.

**S — inspected implementation:** Tactics.lean getPpTacticState formats unsolved goals; suggestTactics calls generate and filters self-reference and aesop suggestions; annotatePremise attaches declaration metadata. Models/Builtin and ByT5 provide inference adapters. Source pin [`078135523a51`](https://github.com/lean-dojo/LeanCopilot/tree/078135523a51e34b6a095bb2e4088ab4ee0161f0); checked commit date 2026-10-13T00:50:57Z.

**Candidates, learning and supervision:** Pretrained tactic models/premise embeddings; neural scores differ from a trained scalar progress estimator.

**Evidence and limits:** Useful interactive workflow and published results; inference/compiler dependencies and model licenses are separate from source. README documents generated-proof caveats.

**Availability and license:** Public source; API classification `MIT`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Adopt inspectable score/context presentation; do not install CTranslate2/OpenBLAS models or claim their experiments reproduced.

### Pantograph

**Objective, authors and publication:** Pantograph project contributors; native Lean interaction infrastructure. Fine-grained persistent proof interaction.

**R — architecture, states and scheduling:** Saved tactic state, root/parent metavariables and tactic fragments; focus/prefer/unfocus explicitly manage multiple goals.

**S — inspected implementation:** Goal.lean GoalState stores SavedState, root, parentMVars and fragments; Site.runTacticM tracks affected goals. Tactic.lean/Assign.lean implement operations. Source pin [`0ee70917fb93`](https://github.com/leanprover/Pantograph/tree/0ee70917fb93a5421157119362ecde806a4d881b); checked commit date 2026-10-20T01:32:08Z.

**Candidates, learning and supervision:** Interface for a caller-provided policy, not by itself a learned prover or benchmark result. No intrinsic training set.

**Evidence and limits:** Interface capabilities are source-confirmed; claims of proving performance require a specified client and workload.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Critical warning against treating equal printed goals as interchangeable. Our whole-state scheduling keeps coupled goals together.

### PyPantograph

**Objective, authors and publication:** Stanford Centaur / Pantograph Python contributors; evolving client. Python interaction/search abstraction.

**R — architecture, states and scheduling:** Goal-state handles and multi-goal interaction; search.py abstracts tactic generation/search callbacks and uses automatic mode.

**S — inspected implementation:** SearchAgent and search machinery in pantograph/search.py check automatic mode and track root goal count/time; server.py wraps native server calls. Source pin [`c9b8648233a8`](https://github.com/stanford-centaur/PyPantograph/tree/c9b8648233a88996d559966c974944d5879329da); checked commit date 2026-10-20T01:40:59Z.

**Candidates, learning and supervision:** No fixed pretrained policy required; a host may provide generators.

**Evidence and limits:** No intrinsic benchmark win from an interface; compatibility depends on the server/toolchain.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Conceptual comparison to our persistent FIFO interface; no replacement during controlled evaluation.

### InternLM2.5-StepProver

**Objective, authors and publication:** Zijian Wu, Suozhi Huang, Zhejian Zhou, Huaiyuan Ying, Jiayu Wang, Dahua Lin, Kai Chen; arXiv:2410.15700, 2024. Expert iteration over Lean problems.

**R — architecture, states and scheduling:** Neural tactic generation and LeanDojo best-first expansion; solved trajectories feed iterative training; premise/search configuration matters.

**S — inspected implementation:** minif2f/proofsearch_internLM2-StepProver.py best_first_search pops a heap and pushes scored states, with real Lean interaction. README distinguishes Math, Workbook and LEAN-GitHub data. Source pin [`eaead17b7b95`](https://github.com/InternLM/InternLM-Math/tree/eaead17b7b95670f0592f5b818080fb6762f3fdf); checked commit date 2024-10-22T16:18:00Z.

**Candidates, learning and supervision:** Large-scale supervised/expert iteration on formal Lean corpora, not a small locally fitted classifier.

**Evidence and limits:** Published MiniF2F results use trained language models and sampling; scripts include operational workarounds. No fair numerical comparison to our original tasks.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENCE, minif2f/LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Reuse only the expert-iteration concept at bounded CPU scale; retain unresolved trajectories without calling them false.

### DeepSeek-Prover V1.5

**Objective, authors and publication:** Huajian Xin and DeepSeek collaborators; arXiv:2408.08152, 2024. RL and RMaxTS exploration.

**R — architecture, states and scheduling:** Generates partial/whole proof continuations; tree nodes represent goal-conditioned prefixes. UCB-style exploration of under-visited states encourages novelty.

**S — inspected implementation:** rmax_tree_search.py _select_node compares node/subtree values plus sqrt(2 log visits / visits), with asynchronous generation and subtree visitation; _tree_update segments real proof goals. Source pin [`2c4ba9119eef`](https://github.com/deepseek-ai/DeepSeek-Prover-V1.5/tree/2c4ba9119eef74d0d611f494261b2c5bae98c69a); checked commit date 2024-08-16T03:33:21Z.

**Candidates, learning and supervision:** Large pretrained models, verifier rewards and search-based data; archive can contain sorry placeholders for partial tasks, which cannot count as complete proofs.

**Evidence and limits:** Reported MiniF2F performance uses model/sample budgets; not a ready tiny CPU algorithm.

**Availability and license:** Public source; API classification `MIT`; individually read `LICENSE-CODE, LICENSE-MODEL`. LICENSE-CODE is MIT; LICENSE-MODEL imposes distinct model terms. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Use exploration/fairness as motivation, but implement a simpler identifiable beam arm first. No external weights or placeholder admissions enter our verifier.

### DeepSeek-Prover V2

**Objective, authors and publication:** Z. Z. Ren, Zhihong Shao, Junxiao Song, Huajian Xin and coauthors; arXiv:2504.21801, 2025. Subgoal decomposition and verifier-based RL.

**R — architecture, states and scheduling:** DeepSeek-V3 decomposes statements, a smaller 7B model solves subgoals, composed successful proofs seed reasoning data, followed by RL. This is different from UCT on a fixed tactic list.

**S — inspected implementation:** Inspected README and repository-hosted full paper PDF; no released complete search/training implementation observed in selected source. Do not infer an implementation from the model announcement. Source pin [`e598a57ea328`](https://github.com/deepseek-ai/DeepSeek-Prover-V2/tree/e598a57ea3284997d4a2a168a069fdd5064afbc8); checked commit date 2025-07-18T08:11:28Z.

**Candidates, learning and supervision:** Synthetic cold starts, informal/formal reasoning and binary verifier feedback; 671B flagship is outside our CPU budget.

**Evidence and limits:** Paper abstract: 88.9% MiniF2F and 47/658 PutnamBench; README at inspected revision instead says 49 in one place. Preserve this version discrepancy; no local reproduction.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `no license file found`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Subgoal provenance and complete-proof audits are transferable. Large-model decomposition is conceptual only.

### Goedel-Prover V2

**Objective, authors and publication:** Goedel-LM research team, Goedel-Prover-V2, arXiv:2508.03613, 2025. Scaffolded synthesis, verifier self-correction and model averaging.

**R — architecture, states and scheduling:** Whole-proof generation followed by compiler-feedback revisions; does not imply an independent fixed-candidate state-value search.

**S — inspected implementation:** src/inference.py uses vLLM, SamplingParams, correction_round and prior output data to generate correction prompts. Source pin [`2e9036e11846`](https://github.com/Goedel-LM/Goedel-Prover-V2/tree/2e9036e118464aa96a8bebaf9f5b9d091aa3585c); checked commit date 2025-08-27T18:13:25Z.

**Candidates, learning and supervision:** Expert iteration/RL, increasing difficulty and averaged checkpoints; large pretrained 8B/32B models.

**Evidence and limits:** README reports 90.4% MiniF2F pass@32 in correction mode, with leaderboard updates using different sample counts. Treat as author-reported and version-bound.

**Availability and license:** Public source; API classification `no root license classification`; individually read `no license file found`. README claims Apache 2.0, but LICENSE retrieval returned 404. Reuse permission is unresolved; no code or model reused. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Self-correction loop is useful future data design; no installation or throughput equivalence claim. README Apache badge is not a substitute for a missing license file.

### TacticToe

**Objective, authors and publication:** Thibault Gauthier, Cezary Kaliszyk and Josef Urban, TacticToe: Learning to Prove with Tactics, arXiv:1804.00596, 2018. HOL4 learned tactic search.

**R — architecture, states and scheduling:** Recorded tactic applications and HOL goals; learned policy/value guidance and tree backups over subgoals. Current source has evolved beyond the original paper.

**S — inspected implementation:** tttLearn.sml records learning machinery; tttSearch.sml reward_of_goal, reorder_stacl, backstatus_stactree and backstatus_root separate OR choices and AND subgoals; visits/rewards are maintained. Source pin [`e05a5e00ca85`](https://github.com/HOL-Theorem-Prover/HOL/tree/e05a5e00ca85782d304d4f71e550640d44e51e05); checked commit date 2026-10-20T09:57:52Z.

**Candidates, learning and supervision:** HOL4 proof library tactic traces, feature-based learning and later neural components. Do not assume the 2026 snapshot is exactly the 2018 experiment.

**Evidence and limits:** Paper evaluates HOL4 library reproving with substantial tactic coverage. Logic/library/time differ from Lean.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `examples/lambda/cbpv-reasonable/LICENSE, examples/muddy/LICENSE, COPYRIGHT`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Strong CPU-scale precedent for trajectory learning and tactic attribution. Independently implement state-value regression; do not port SML or compare absolute success percentages.

### HOList / DeepHOL

**Objective, authors and publication:** Kshitij Bansal, Sarah Loos, Markus Rabe, Christian Szegedy, Stewart Wilcox; HOList, ICML 2019. HOL Light benchmark and neural-guided proving.

**R — architecture, states and scheduling:** Theorem database plus tactic arguments, premise ranking and logged proof search; proof-assistant server independently checks tactics.

**S — inspected implementation:** deephol/action_generator.py ActionGenerator combines tactic/premise scores and restricts preceding theorem indexes; prover.py BFSProver handles bounded search and failure/timeout logs. Source pin [`b5b721f54de1`](https://github.com/tensorflow/deepmath/tree/b5b721f54de1d5d6a02d78f5da5995237f9995f9); checked commit date 2020-03-16T17:46:30Z.

**Candidates, learning and supervision:** HOL Light theorem proofs, supervised learning and iterative proof-log training.

**Evidence and limits:** Reported theorem split/reproving results require their server and trained networks; historical TensorFlow dependency. No local reproduction.

**Availability and license:** Public source; API classification `Apache-2.0`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Import proof-log and dependency-order discipline, not benchmark proofs; record search effort and split restrictions.

### HyperTree Proof Search / Evariste

**Objective, authors and publication:** Guillaume Lample, Timothee Lacroix, Marie-Anne Lachaux, Aurelien Rodriguez, Amaury Hayat, Thibaut Lavril, Gabriel Ebner, Xavier Martinet; NeurIPS 2022, arXiv:2205.11491. Online neural hypergraph proof search.

**R — architecture, states and scheduling:** Tactics are hyperedges to jointly necessary subgoals; value estimates, visitation and backups drive simulations; cycle/reachability handling is nontrivial.

**S — inspected implementation:** mcts.py find_leaves_to_expand follows policy arrays across many leaves, stores priors/counts/logW for visualization, and comments that loop killing may prevent proofs. mcts_samples.py defines critic/tactic samples. Source pin [`ef43511f2d23`](https://github.com/facebookresearch/Evariste/tree/ef43511f2d234bcb28e380388b8fe0d06a4d93a7); checked commit date 2024-08-01T13:22:26Z.

**Candidates, learning and supervision:** Online successful subproofs and critic/policy updates across Lean, Metamath and equations.

**Evidence and limits:** README explicitly states archive does not run out of the box after removal of internal systems. Reported results are not a deployable CPU recipe.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `LICENSE, lean_fork/LICENSE`. Main code is CC-BY-NC 4.0; Apache applies only to selected Lean subtrees, not the MCTS code. No third-party implementation is integrated.

**P — lesson and compatibility decision:** AND/OR correctness and recorded decisions inform our design. Main license is CC-BY-NC 4.0, distinct from Apache Lean subtrees: no code copied.

### Isabelle Sledgehammer

**Objective, authors and publication:** Jasmin Blanchette, Lawrence Paulson and Sledgehammer contributors; system papers and Isabelle documentation, current 2026 source. Premise selection, ATP portfolios and trusted reconstruction.

**R — architecture, states and scheduling:** HOL facts translated for external ATPs; relevant used facts are reconstructed by Metis/other methods inside Isabelle.

**S — inspected implementation:** sledgehammer_mepo.ML typed-constant relevance; mash.ML supports learned premise selection; prover.ML slice_timeout, bunches_of_metis_methods and used-fact handling separate solving/reconstruction. Source pin [`a82828aba6e7`](https://github.com/isabelle-prover/mirror-isabelle/tree/a82828aba6e796dfe82aa3fb44d49bf1e725dc5a); checked commit date 2026-10-14T18:53:35Z.

**Candidates, learning and supervision:** MePo symbolic relevance and MaSh learned selections from existing proof dependencies; not an LLM-only tool.

**Evidence and limits:** Strong library automation history; external ATP success and successful certified reconstruction are different outcomes.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `COPYRIGHT`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Local relevance filtering and independent reconstruction are appropriate concepts; do not run Isabelle or equate HOL and Lean candidate units.

### CoqHammer

**Objective, authors and publication:** Łukasz Czajka and Cezary Kaliszyk; CoqHammer, IJCAR 2018 and project. Coq/Rocq hammer with internal reconstruction.

**R — architecture, states and scheduling:** Premise prediction, higher-order/dependent translation to ATP tasks and proof reconstruction tactics.

**S — inspected implementation:** hammer_main.ml Features.predict, reconstruction batches, time limits and process forks coordinate ATP/reconstruction. Source pin [`27b80e8f2aa1`](https://github.com/lukaszcz/coqhammer/tree/27b80e8f2aa1a53d8d2a0642302736bad14c20ed); checked commit date 2026-08-31T15:29:18Z.

**Candidates, learning and supervision:** Proof-dependency premise learning; search is fundamentally different from fixed Lean tactic ranking.

**Evidence and limits:** Published Coq library reproving, not comparable to Lean percentages; external tools and reconstruction coverage limit transfer.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `LICENSE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Conceptual premise-selection comparison only; LGPL-2.1 text requires distinct handling from our Apache project, no source reuse.

### E prover / ENIGMA context

**Objective, authors and publication:** Stephan Schulz and E contributors; E, established saturation prover; ENIGMA research by Jakubův and collaborators. First-order saturation and learned clause guidance.

**R — architecture, states and scheduling:** Given-clause active/passive sets with term indexes, simplification/subsumption, weighted selection and scheduling. ENIGMA is a related learned-clause framework, not claimed present in inspected file.

**S — inspected implementation:** CONTROL/cco_proofproc.c inspected as main proof process; source-confirmed control loop is separate from paper-based ENIGMA inference. Source pin [`3b7afc70fe77`](https://github.com/eprover/eprover/tree/3b7afc70fe77d3118bb95144c4735ca45f5f31cf); checked commit date 2026-09-02T20:08:04Z.

**Candidates, learning and supervision:** Classical E strategies need no training; ENIGMA learns useful clauses from proof-search traces.

**Evidence and limits:** TPTP-style workloads and first-order proof certificates differ from Lean elaboration states.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `CONTRIB/picosat-965/LICENSE, COPYING`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Age/weight scheduling motivates a fair bounded alternative; no C implementation imported. COPYING lists GPL/LGPL version-dependent provisions.

### Vampire

**Objective, authors and publication:** Andrei Voronkov and Vampire contributors; established automated first-order theorem prover. Saturation and strategy portfolios.

**R — architecture, states and scheduling:** Discount/Otter variants balance forward/backward simplification and active/passive clauses; term redundancy has formal ordering conditions.

**S — inspected implementation:** Saturation/Discount.cpp, Otter.cpp and SaturationAlgorithm.cpp implement these distinct saturation control arrangements. Source pin [`b75190a4b794`](https://github.com/vprover/vampire/tree/b75190a4b7946c325263b079ac8a67d2ea1c3e01); checked commit date 2026-10-20T08:48:18Z.

**Candidates, learning and supervision:** Symbolic strategy portfolios; learned variants are separate research claims.

**Evidence and limits:** Strong first-order competition results do not imply local Lean proof reconstruction or identical mathematical coverage.

**Availability and license:** Public source; API classification `NOASSERTION`; individually read `LICENCE`. No third-party implementation is integrated.

**P — lesson and compatibility decision:** Redundancy requires a proof-theoretic criterion, not similar text. BSD-3-Clause inspected, conceptual comparison only.

## Interfaces and benchmark methodology

### LeanDojo interaction/data

Yang and coauthors, 2023. TracedTheorem/TracedTactic include source/proof accessibility; dojo.py TacticState, run interaction and check_proof distinguish process errors from Lean rejection. Supervision is proof-state/action data, with random/novel-premise splits. MIT source inspected. Adopt provenance and strict split guards; no dataset proofs imported. Checked [7a9f600b250a](https://github.com/lean-dojo/LeanDojo/tree/7a9f600b250a89a62e991c05ffe81ba033018e6e) (2026-01-18T21:33:30Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### Lean REPL

Lean community, evolving interface. REPL/Main.lean records command/proof snapshots, reports proof status and serializes goal information. Saved-state handles support branching, but equal prints are not equality of elaboration state. Apache source; no learned model or intrinsic benchmark score. Compare interface design only. Checked [a85a1d2f4bde](https://github.com/leanprover-community/repl/tree/a85a1d2f4bdeab19c3d34be979ea336c9ee9b3ed) (2026-10-16T20:02:26Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### LeanExplore

Justin Casher and contributors, current 2026 repository. Declaration search, local embedding/reranking backend and optional hosted API. Inspected models/search_db.py stores SQLite declaration/embedding schema; README explicitly separates base remote API from local extras. Apache source license. No proof-search performance claim; no remote runtime dependency introduced. Local type/symbol indexes are a future alternative. Checked [17b9d6c87a2b](https://github.com/justincasher/lean-explore/tree/17b9d6c87a2bf0dc4ea27de05da8a1c9965391b7) (2026-09-29T00:57:44Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### ProofNet

Zhangir Azerbayev, Bartosz Piotrowski, Hailey Schoelkopf, Edward W. Ayers, Dragomir Radev, Jeremy Avigad; arXiv:2302.12433, 2023. 371 undergraduate examples with informal statements/proofs and formal Lean 3 statements; current README recommends Lean 4 ports. Autoformalization differs from proving a trusted statement. MIT license inspected; only documentation read, not proof corpus. Adopt breadth and explicit versioning, not theorem imports. Checked [509ad79710ed](https://github.com/zhangir-azerbayev/ProofNet/tree/509ad79710ed4f46ff5c282ed5640c1aa9ac3f30) (2024-10-14T00:46:43Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### MiniF2F

Kunhao Zheng, Jesse Michael Han, Stanislas Polu; ICLR 2022. Competition problems across formal systems, validation/test design and multiple proof samples. Version/port, imports, pass@k, time and contamination matter. Root license was unavailable; per-system licenses differ, including Apache Isabelle and BSD HOL Light. No benchmark proofs read. Compare design only. Checked [4e433ff5cadf](https://github.com/openai/miniF2F/tree/4e433ff5cadff23f9911a2bb5bbab2d351ce5554) (2022-06-02T16:35:50Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### MiniF2F Lean 4 port

Kaiyu Yang and community contributors; evolving port. Pinned Lean 4 environment matters: a port is not automatically identical to historical Lean 3 evaluation. MIT file inspected individually. No data imported. Our held-out original statements are not a miniature reproduction of MiniF2F scores. Checked [5746b7d6c478](https://github.com/yangky11/miniF2F-lean4/tree/5746b7d6c47855ce1294bed87329618ff7f1bc31) (2026-03-25T16:02:13Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### PutnamBench

George Tsoukalas, Jasper Lee, John Jennings, Jimmy Xin, Michelle Ding, Michael Jennings, Amitayush Thakur, Swarat Chaudhuri; arXiv:2407.11214, 2024, updated through 2026. Multilingual competition formalizations, category metadata and answer-factored tasks. Current README has 672 Lean, 640 Isabelle, 412 Coq formalizations; historical papers have smaller snapshots. Lean/Isabelle Apache, Coq MIT; informal statements have separate permission. README requests avoiding public solution contamination. Only documentation/license read; no task solutions imported. Checked [a635813f5edf](https://github.com/trishullab/PutnamBench/tree/a635813f5edf297d928f9bd5ef8324a26bdde09c) (2026-10-06T21:57:24Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

### Kimina Lean server

Project Numina / Kimina contributors, 2025–2026 infrastructure. Lean process/server infrastructure supports batch verification for neural proof pipelines; source inventory records inspected modules. A verifier service does not itself imply a proving policy. No server/model installed. Compare timeout/process accounting and version pinning; no hosted inference. Checked [fb2393de3461](https://github.com/project-numina/kimina-lean-server/tree/fb2393de3461db35eda4c714e3fd21187e92ec90) (2026-01-11T14:24:06Z). These infrastructure/data systems do not themselves specify a learned policy, training objective, candidate set or state scheduler; those fields are not applicable unless a particular prover is added. Their experimental methodology cannot supply a missing ProofLab result.

## Search theory, attribution and limits

Hart, Nilsson and Raphael (1968) define A*: f=g+h with admissibility/consistency conditions for optimality; Pohl (1970) studies heuristic weighting. Our fitted regression has no admissibility guarantee, so we must call it learned best-first, not optimal A*. Beam search retains a bounded number of promising frontier entries and may discard the only proof. We implement a deterministic bounded best-first beam, explicitly distinct from synchronous layer beam search.

Kocsis and Szepesvári (2006), UCT, balances estimated return and exploration using visit counts. AlphaZero (Silver and coauthors, 2017/2018) combines policy/value learning, simulation and self-play; a proof state is not a two-player board game. Metamath proof search (including Polu and Sutskever, 2020, arXiv:2009.03393) and HTPS provide more relevant AND/OR adaptations: all subgoals under a tactic must succeed, alternatives are OR choices, and sound proof assembly must respect shared constraints. A state whose displayed first goal is easy can still hide expensive other obligations.

Saturation redundancy is justified through clause subsumption and ordering conditions, not hashing pretty-printed states. Aesop/Pantograph maintain native metavariable/elaboration state. Two tactic snapshots may show identical goals but contain different assignments or synthetic constraints. ProofLab will inspect native expression structures offline and group similar states without merging, reusing results or pruning. Only exact tactic prefixes within a native session retain their existing identity. No claimed graph-level speedup is earned by diagnostic grouping.

ENIGMA-style clause usefulness and TacticToe/HTPS value learning suggest a small trained state scorer can be meaningful even when neural tactic generation is infeasible. However, learning continuation cost only on verified successes is biased toward solvable/easier trajectories. A censored rollout means the configured search did not finish; it is not evidence that the mathematical state has no proof, nor a lower bound on the shortest possible proof.

## Prior evidence and choice

Phase 2 and 3 both achieved 23/32 Phase 3 theorems under the fixed generator, with no established Phase 3 advantage over the handcrafted policy. Candidate ordering is only one lever. We select a separately trained scalar frontier-cost estimator with interpretable features, compare linear and fixed quadratic feature models on permitted development theorems, and perform a factorial scheduling/candidate comparison. A bounded beam arm tests a different memory/search-space policy. The primary generator and verification bridge remain unchanged. A separate local normalization/retrieval diagnostic investigates expressiveness; its results cannot be attributed to ML scheduling.

This is original ProofLab implementation and original controlled experiments using established ideas, not a new proof-search theory. MCTS, certified AND/OR transpositions, large-model self-improvement and library-wide neural retrieval remain untested alternatives. Current 2026 LeanHammer, LeanExplore and Lean core changes are included as checked source developments; we do not invent a comprehensive list of every 2026 paper.
