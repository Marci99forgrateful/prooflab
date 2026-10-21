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

This selects the linear/boosted relevance architecture using four whole-family validation groups, retains the fitted relevance weights from the 120 training tasks. The forty validation families never train that expert before selector validation. It produces **provisional relevance artifacts**: an unfitted adaptive selector cannot execute normal search. Relevance fingerprints are frozen before the separate matched strategy collection. The recorded experiment already includes the actual equal-budget forced-mode traces, so a saved-data selector refit needs no new Lean searches:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 uv run --frozen python - <<'PY'
from pathlib import Path
from prooflab.adaptive_fit import fit_selector
fit_selector(output=Path('/tmp/prooflab-phase6-refit'))
PY
```

Compare final relevance/selector parameter JSONs with the committed artifacts; wall-time fields in reports are observations and are not expected to match. The selector's target is log attempt cost **conditional on independently verified fixed-mode completion**. Accepted/censored/unexplored actions are never labelled mathematically incorrect. Missing outcome selection bias and root-to-intermediate-state distribution shift remain limitations.

To collect a **new** matched strategy experiment, use `phase6_counterfactuals.collect(destination=<new-dir>)` with the documented relevance model source. The collector refuses existing output; it hashes the exact relevance component and all procedures. Linear/applicability relevance controls share the selected selector, explicitly isolating relevance changes rather than claiming independently trained portfolios.

## Frozen final execution

The committed `models/phase6/frozen.json` hashes all executable Phase 6 source, models and the selector registration. `check_execution` also verifies all prior frozen evidence. It is forbidden to tune code/models against final results.

```bash
uv run --frozen python -c 'from prooflab.phase6_evaluation import check_execution; check_execution()'
uv run --frozen python scripts/evaluate_phase6.py run --output /tmp/prooflab-phase6-new-evaluation
uv run --frozen python scripts/evaluate_phase6.py finalize --output /tmp/prooflab-phase6-new-evaluation
```

The full preregistered matrix is 1344 genuine searches with two workers. Comparable primary arms share 18 seconds, 600 attempts, eighty expansions, depth twelve and cap 24. The smaller controls share 10 seconds, 240 attempts and forty expansions. Every query/inference/verification consumes the outer wall budget. Aesop/grind use a separate opaque external call capped at two seconds; attempts are not internal inference counts. Use an otherwise idle host for cleaner timing; report any concurrent activity. New execution can legitimately differ under resource limits and does not replace the recorded result.

## Inspecting data and replay

```bash
gzip -dc experiments/phase6/evaluation-v1/traces/<task>--<arm>--r0.json.gz
uv run --frozen python scripts/analyze_phase6.py
uv run --frozen python scripts/report_phase6.py
uv run --frozen python scripts/export_phase6.py
npm --prefix web run build
uv run --frozen prooflab serve
```

All canonical archives retain exact original JSON bytes. `trace-storage.json` indexes raw and compressed SHA-256 values; the browser decompresses the same gzip files. Analysis/reporting reads recorded evidence and cannot retune frozen execution. `results.csv` contains all per-run measurements; summary files include per-theorem proofs, paired intervals, per-family results and exact-prefix witnessed availability. Native compatibility, actual acceptance and verified complete paths remain distinct.

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
