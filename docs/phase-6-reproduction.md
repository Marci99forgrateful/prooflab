# Reproducing Phase 6

Use the review branch `feature/phase6-adaptive-hybrid`, based on Phase 5 commit `4cc061e`. No merge is required. The pinned toolchain remains Lean 4.24.0 and Mathlib `f897ebcf72cd16f89ab4577d0c826cd14afaafc7`. `uv.lock` and `web/package-lock.json` pin Python/Node dependencies; NumPy is an explicit development/training dependency. Model inference is standard-library CPU arithmetic. No GPU, pretrained weights, API key or hosted inference is involved.

```bash
bash scripts/bootstrap.sh
uv run --frozen python -c 'from prooflab.phase6_data import check_freeze; check_freeze()'
```

Bootstrap compiles the new `ProofLab.Adaptive` module and preserves old trusted code. If a managed workspace requires writable caches, set `XDG_CACHE_HOME`, `UV_CACHE_DIR`, `npm_config_cache` and `MPLCONFIGDIR` to directories below `/workspace/.cache`. Existing `ELAN_HOME` or the retained `/workspace/.toolchains/elan` is honored. The existing network proxy/CA policy remains unchanged.

## Training stages and exact source provenance

Final statements, development boundaries, budgets and model-selection rules are frozen before selection. The matched-selector supplement is separately hash-registered before relevance fitting. Phase 1–5 evaluation material is diagnosis only. Do not regenerate frozen JSON files or substitute previous test traces as development labels.

The actual first complete development action/source collection runs the implementation at **`339b8f1`**. Its provenance stores that commit and exact source hashes; later cancellation, annotation and forced-mode changes do not rewrite those traces. A clean checkout at that commit reproduces the collection procedure; use a new output directory and expect real wall/resource variation. The naming-error smoke archive is retained separately and is excluded from training. The six prototype pilots likewise remain separate.

```bash
# From the documented collection source commit, or to run a new versioned collection:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --frozen python scripts/train_phase6.py collect \
  --data /tmp/prooflab-phase6-new-development
```

A same-source interrupted collection supports `--resume`; mismatched source hashes are refused. Never overwrite committed evidence. After collection, use the current Phase 6 training implementation and the recorded canonical development data:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --frozen python scripts/train_phase6.py fit \
  --data experiments/phase6/development-v1 --output /tmp/prooflab-phase6-refit
```

This selects the linear/boosted relevance architecture using four whole-family validation groups and retains its 120-task training fit. The forty tasks in the four validation families never train that expert before selector validation. It produces **provisional relevance artifacts**: an unfitted adaptive selector cannot execute normal search. Relevance fingerprints are frozen before the separate matched strategy collection. The recorded experiment already includes the actual equal-budget forced-mode traces, so a saved-data selector refit needs no new Lean searches:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --frozen python - <<'PY'
from pathlib import Path
from prooflab.adaptive_fit import fit_selector
fit_selector(output=Path('/tmp/prooflab-phase6-refit'))
PY
```

Compare final relevance/selector parameter JSONs with the committed artifacts; wall-time fields in reports are observations and are not expected to match. The selector's target is log attempt cost **conditional on independently verified fixed-mode completion**. Accepted/censored/unexplored actions are never labelled mathematically incorrect. Missing outcome selection bias and root-to-intermediate-state distribution shift remain limitations.

To collect a **new** matched strategy experiment, use `phase6_counterfactuals.collect(destination=<new-dir>)` with the documented relevance model source. The collector refuses existing output; it hashes the exact relevance component and all procedures. The fully linear control uses a ridge controller on identical costs; the applicability relevance control holds the selected boosted controller fixed. Controller seeds one/two keep relevance identical and change only the registered stochastic cost model.

## Frozen final execution

The committed `models/phase6/frozen.json` hashes nineteen executable/protocol/archive entries and eight model/report artifacts. Source commit `f239b2b` and freeze commit `6c204c2` precede the first final search. The effective protocols include the selector validation guard, precise work-conserving allocation semantics, the fully linear control and the conditional seed supplement. `check_execution` also verifies all prior frozen evidence. It is forbidden to tune code/models against final results.

This is a locally committed research freeze, not external blinded preregistration. The final freeze was pushed to the review branch during the campaign; its public publication did not precede the first run. Statements were visible to the developers for design and native structural auditing. The archived commit/source/model hashes and run provenance make the implemented boundary inspectable.

```bash
uv run --frozen python -c 'from prooflab.phase6_evaluation import check_execution; check_execution()'
uv run --frozen python scripts/evaluate_phase6.py run --output /tmp/prooflab-phase6-new-evaluation
uv run --frozen python scripts/evaluate_phase6.py finalize --output /tmp/prooflab-phase6-new-evaluation
```

The full effective preregistered matrix is **1440 genuine searches with two workers**: 1344 main/ablation runs plus 96 controller-seed robustness runs. The conditional seed supplement was registered before controller selection; seed zero remains primary. Comparable primary arms share 18 seconds, 600 attempts, eighty expansions, depth twelve and cap 24. The smaller controls share 10 seconds, 240 attempts and forty expansions. Every query/inference/verification consumes the engine wall budget. Full-call `runner_wall_s` additionally includes separately measured fixed artifact setup and metadata construction; archive I/O/interpreter startup are outside the call. Failed retrieval round trips are metered, with unavailable interrupted native counters left unknown. Aesop/grind use a separate opaque external call capped at two seconds; attempts are not internal inference counts. Use an otherwise idle host for cleaner timing; report any concurrent activity. New execution can legitimately differ under resource limits and does not replace the recorded result.

## Inspecting data and replay

```bash
gzip -dc experiments/phase6/evaluation-v1/traces/<task>--<arm>--r0.json.gz
uv run --frozen python scripts/analyze_phase6.py
uv run --frozen python scripts/sensitivity_phase6.py
uv run --frozen python scripts/report_phase6.py
uv run --frozen python scripts/export_phase6.py
uv run --frozen python scripts/plot_phase6.py
uv run --frozen python scripts/export_phase6_examples.py
npm --prefix web run build
uv run --frozen prooflab serve
```

All canonical archives retain exact original JSON bytes. `trace-storage.json` indexes raw and compressed SHA-256 values; the browser decompresses the same gzip files. Analysis/reporting reads recorded evidence and cannot retune frozen execution. `results.csv` contains all per-run measurements; summary files include per-theorem proofs, paired intervals, per-family results and exact-prefix witnessed availability. Native compatibility, actual acceptance and verified complete paths remain distinct.

The inherited generic `metadata.seed` describes deterministic search scheduling. The controller training seed is recorded in its model's `selector.seed`, the effective arm's `model_variant`, and `adaptive_model_file`/`adaptive_model_sha256`; seeded sensitivity arms must be identified from those fields rather than the legacy generic label.

Select **Phase 6 · Adaptive Proof Search** in the existing Search Architecture Explorer. Compare Phase 4, Phase 5 typed, deterministic and learned policies side by side. A small-budget arm has its own recorded budget; do not interpret it as an equal-budget primary comparison. The finite local API accepts only repository-owned evaluation IDs and registered modes; it preserves cancellation, origin restrictions, proof checking and exports.

## Validation

```bash
uv run --frozen ruff check src scripts tests
uv run --frozen ruff format --check src scripts tests
uv run --frozen mypy src/prooflab
npm --prefix web test
npm --prefix web run format:check
uv run --frozen pytest -q --junitxml=artifacts/local/pytest.xml
```

Hosted CI runs the same bootstrap, lint/typing, Node and actual Python/browser tests. JUnit outcomes are emitted as GitHub annotations, preserving failures. The Phase 5 CRLF checkout rule for the old frozen CSV remains; do not change old hashes to accommodate checkout normalization. Infrastructure denials and code/test failures must be distinguished from actual GitHub job evidence.
