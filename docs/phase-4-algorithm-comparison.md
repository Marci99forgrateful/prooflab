# Search architecture comparison

The pinned [survey](phase-4-related-work.md) separates implementation evidence from reported results. All ProofLab states contain the complete remaining goal list in one saved Lean elaboration state. Alternatives are OR branches; the obligations inside a state are jointly necessary. Treating each goal as independent would lose shared metavariable constraints.

| Architecture | Expansion priority | Candidates | Retention / correctness |
|---|---|---|---|
| BFS | insertion order by depth | original generator order | complete only within finite tactic/depth limits |
| Handcrafted best-first | 12×goals + target characters/12 + .8×depth | handcrafted prior | no admissibility guarantee |
| Phase 2 | same handcrafted frontier | learned applicability preferences | state scheduling unchanged |
| Phase 3 | same handcrafted frontier | learned applicability and successful continuation cost preferences | unresolved actions unlabeled |
| Frontier + handcrafted | fitted state log-cost + .15×depth | handcrafted | all native branches retained |
| Frontier + outcome | same fitted state value | frozen Phase 3 | factorial test of candidate versus state scheduling |
| Beam | same fitted state value | frozen Phase 3 | bounded best-first frontier; worst queue entry discarded; may remove unique proof |
| Linear frontier ablation | transparent linear fit | frozen Phase 3 | separates nonlinear feature basis from search architecture |
| Native Aesop | internal safe/unsafe AND/OR scheduling | Aesop rule database | one external call, internal effort incomparable |
| Native grind | internal congruence/E-matching/theory propagation | installed symbolic rules | separate reference, independent fresh audit |

Learned best-first is not A*: predicted cost is not admissible, and observed continuation attempts are not minimal path length. Beam is a global bounded priority queue, not a per-layer synchronous beam. Its retention width is frozen from development-only design, not chosen using final-test success. MCTS would require visit statistics, an exploration rule and justified AND backups; HTPS adds hypergraph/cycle handling and online training. None of those names describe our beam implementation.

For each expansion the execution trace will retain the actual popped state, all eligible frontier entries and their insertion priorities, learned values, heuristic values, and counted attempts. Candidate rankings and actual native transitions remain available. This makes a scheduling divergence independently inspectable. Any excluded beam entry is recorded separately from Lean rejection. Diagnostic state grouping never influences scheduling.
