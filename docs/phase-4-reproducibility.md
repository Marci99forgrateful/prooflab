# Phase 4 reproduction and provenance

Use Linux, Python 3.12, uv, Node 20.19+ / 22.12+ and the pinned Lean 4.24.0 toolchain. No GPU, inference key, model service or new ML package is needed. The cloud cache can be reused; never alter MathVerify or replace the pinned Mathlib version.

```bash
bash scripts/bootstrap.sh
uv run --frozen prooflab train-frontier --output /tmp/prooflab-frontier-repro
uv run --frozen prooflab evaluate-phase4 --output /tmp/prooflab-phase4-repro
uv run --frozen prooflab inspect-states --experiment /tmp/prooflab-phase4-repro --output /tmp/prooflab-native-repro
```

Training/evaluation destinations must be new. Training checks the frozen input whitelist; evaluation uses the committed selected/linear artifacts and protocol, rather than silently accepting a different fitted model. Numerical weights and normalization reproduce exactly; report wall/CPU timestamps and platform provenance naturally differ. Final evaluation is deterministic in structural decisions under sufficient wall time; host contention can change wall-limit outcomes.

Canonical experiment maintenance commands, without rerunning Lean:

```bash
uv run --frozen python scripts/finalize_phase4.py
uv run --frozen python scripts/analyze_phase4.py
uv run --frozen python scripts/report_phase4.py
uv run --frozen python scripts/plot_phase4.py
uv run --frozen python scripts/export_phase4.py
npm --prefix web run build
uv run --frozen prooflab serve --port 8000
```

The Search Architecture Explorer is available through its navigation item. It replays the 640 actual executions and offline native diagnostic relationships, supports both recorded repetitions, ten policy selections, queue inspection, candidate scores, feature contributions, complete audited proofs and full JSON export. The neighborhood view is explicitly labelled: actual path, all accepted children and up to four rejected attempts. Complete-tree mode retains every actual node. Earlier Phase 1–3 replay, live search, continuation inspection and exports remain available.

For a finite live local computation: `uv run --frozen prooflab search p4_witness_exists --algorithm joint --depth 12 --expansions 80 --attempts 600 --timeout 20`. `--frontier-model` selects a local state model only for an explicit custom search; it does not change the primary evaluator. The API accepts repository task IDs and enumerated policies only, never Lean/tactic source or arbitrary model uploads.

The development pilot and generator-study scripts write fixed new experiment directories and refuse overwrite. For reruns use an isolated checkout or edit only the destination argument locally; do not overwrite committed scientific evidence. The original statement generator refuses to rewrite frozen data. `inspect_phase4_sources.py --output NEW_DIRECTORY` fetches and verifies exactly the pinned source subset from the bibliography; it downloads no models or benchmark solution archives.

## Execution provenance and reporting repairs

`68ee157` freezes the new theorem families and protocol before fitting. `b5ecb2e` freezes trained models and primary execution source before final searches. Every raw trace records its actual commit/toolchain/model hashes; `provenance.json` records exact source-file SHA-256 values. Later interface, documentation and reporter work is not misrepresented as the source that generated the primary measurements.

The initial report adapter expected the older uncertainty-object shape while Phase 4's frozen protocol describes uncertainty in text with separate numeric fields. All 640 native executions were already recorded before reporting encountered this mismatch. `finalize_phase4.py` validates the complete expected matrix and regenerates summary/CSV from unchanged raw traces using the corrected adapter; no searches or model selections are repeated. This reporting repair changes no measured execution, proof, success or cost.

Historical raw `metadata.frontier_policy` strings for BFS/native references inherited a generic comparator annotation from Phase 3. Actual algorithm IDs, FIFO decisions and native tactic records are authoritative. The Explorer labels these architectures explicitly, and future trace metadata has been corrected; raw historical bytes remain preserved. Frontier decisions record queue **selection**, including states later skipped at the depth bound. Expanded-state metrics count only actual candidate-pool expansions, not every pop.

All primary traces are deterministic gzip archives of exact original JSON bytes with raw/compressed hashes. The pilot, extended-generator and failure traces use the same reversible format. Native expression diagnostics retain one shared-prefix replay per theorem, with source-hash references to every trace. Generated static assets are ignored and rebuilt, avoiding a second large checked-in trace copy. Old Phase 1–3 research artifacts, models and protected generator/verifier/bridge hashes remain unchanged.

## Validation commands

```bash
uv run --frozen ruff check src scripts tests
uv run --frozen ruff format --check src scripts tests
uv run --frozen mypy src/prooflab
lake build ProofLab
npm --prefix web test
npm --prefix web run format:check
uv run --frozen pytest -q --junitxml=artifacts/local/phase4-pytest.xml
```

Hosted CI results must be checked separately. A provider refusal before job startup does not execute any code/test step and cannot be reported as a failing code check. Do not change account billing or merge a draft to bypass it.

A normalized closed sequent can also erase the boundary between an implication goal and the same premise introduced into local context. The original native representations retain binder names; the structural grouping erases them. The native inspector regression deliberately checks that target binders remain unintroduced until the actual recorded tactic is replayed. This illustrates why sequent-shape repeats are exploratory observations, never certified transpositions. CSV metrics distinguish unique native saved-state handles from these coarser structures.
