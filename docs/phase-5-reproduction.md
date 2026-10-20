# Reproducing Phase 5

Use the Phase 5 feature branch with Python 3.12, CPU, Lean 4.24.0 and the committed Mathlib revision. No GPU, API key, pretrained weights or hosted inference is involved. Cache use is supported. The setup script uses `XDG_CACHE_HOME`, `UV_CACHE_DIR` and `npm_config_cache`; cloud installations should point these into a writable workspace.

```bash
export XDG_CACHE_HOME=/workspace/.cache
export UV_CACHE_DIR="$XDG_CACHE_HOME/uv"
export npm_config_cache="$XDG_CACHE_HOME/npm"
export ELAN_HOME=/workspace/.toolchains/elan
export PATH="$ELAN_HOME/bin:$PATH"
bash scripts/bootstrap.sh
```

All commands below run from the repository root. Canonical outputs refuse accidental overwrite. To inspect rather than recompute, gzip files contain the byte-exact original JSON and `trace-storage.json` provides hashes.

```bash
.venv/bin/python -c 'from prooflab.phase5_data import check_freeze; check_freeze()'
.venv/bin/python -c 'from prooflab.phase5_evaluation import check_execution; check_execution()'
.venv/bin/python scripts/train_phase5.py fit --output /tmp/prooflab-retrained
cmp models/phase5/retrieval.json /tmp/prooflab-retrained/retrieval.json
.venv/bin/python scripts/train_phase5.py collect --data /tmp/prooflab-development
.venv/bin/python scripts/train_phase5.py fit --data /tmp/prooflab-development --output /tmp/prooflab-new-fit
.venv/bin/python scripts/evaluate_phase5.py run --output /tmp/prooflab-evaluation
.venv/bin/python scripts/evaluate_phase5.py finalize --output /tmp/prooflab-evaluation
.venv/bin/python scripts/canonicalize_phase5_statistics.py --experiment /tmp/prooflab-evaluation
PYTHONHASHSEED=0 .venv/bin/python scripts/canonicalize_phase5_statistics.py --verify
PYTHONHASHSEED=1 .venv/bin/python scripts/canonicalize_phase5_statistics.py --verify
.venv/bin/python scripts/export_phase5.py
.venv/bin/prooflab search p5_product_graph --generator typed --algorithm best_first --depth 12 --attempts 600 --timeout 18
.venv/bin/prooflab search p5_product_graph --generator learned --algorithm outcome --depth 12 --attempts 600 --timeout 18
.venv/bin/prooflab serve
```

Retraining on saved evidence is deterministic. Recollecting evidence can change wall-time censoring and therefore training observations; retain the new raw corpus and do not compare its weights as if the source data were identical. A full repeated evaluation uses the frozen reference model and source hashes; model replacement is a new study, not an overwrite of this evaluation. Source/benchmark regeneration scripts intentionally refuse once frozen. To reconstruct those historical preparation steps, inspect the pre-freeze commits in a separate checkout.

The controlled matrix has four generators × handcrafted/Phase 3 action schedulers, two additional frozen Phase 4 joint-frontier arms, separate Aesop/grind references (all repeated twice), and four single-run ablations: broad, type-filter-only, no new witnesses, no new normalization. Forty tasks yield 1120 actual runs. Every arm has depth twelve, eighty expansions, candidate cap 24, 600 attempts, eighteen seconds overall and two seconds per tactic/query. Retrieval is part of that overall deadline. Repeated primary runs and rotated arm ordering reduce, but cannot eliminate, shared-host timing variability.

Wall time includes initialization and fresh proof auditing. `lean_execution_s` includes step IPC and native retrieval; retrieval is also reported separately. Planning includes Python scoring and model inference is its measured subset, not another disjoint wall-time category. Native allocation-heartbeat deltas are available for successful/rejected tactics and retrieval queries, including external references; they are allocation counters, not proof-inference counts. Live session-tree CPU and summed process high-water RSS bounds exclude independent audit subprocess resources and are not total-machine CPU or simultaneous peak memory. Missing measurements remain null.

The initial regression log completed 0.350 seconds before campaign start, so that suite did not overlap the experiment. An earlier draft incorrectly conflated its 18.86-second duration with overlap; the filesystem timestamps correct this in artifacts/phase5-timing-note.json. Frontend builds and light report editing occurred on the shared cloud host. Do not infer a controlled hardware speedup from wall time alone. The second primary repetition is separate evidence; structural counts and success repeat stability must be reported. No frozen-test outcome was used to alter the search or model. Retrieval variants can change both capped membership and generated input order; the existing action rankers are stable, so equal downstream scores preserve retrieval order. The analysis separates membership changes from order-only changes at actually matched exact prefixes.

Validation commands:

```bash
lake build ProofLab
.venv/bin/ruff check src scripts tests
.venv/bin/ruff format --check src scripts tests
.venv/bin/mypy src/prooflab
.venv/bin/pytest -q
npm --prefix web run format:check
npm --prefix web test
npm --prefix web run build
```

Browser tests use installed Chromium (`PROOFLAB_CHROMIUM` may override its path). Static replay needs exported canonical assets but no Lean process. Phase 5 exports copy canonical gzip archives byte for byte; the browser decodes them with DecompressionStream, avoiding several GB of redundant uncompressed static assets. Use a current browser. Local search is served only on loopback and accepts repository task IDs and finite generator/policy choices, never arbitrary source/tactic input. Exports preserve actual traces and verification status.

The frozen runner's intermediate family set gives its finite bootstrap a hash-order dependency. Its raw `summary.json` is retained. `summary-canonical.json` sorts family IDs, preserves all actual outcomes and theorem-bootstrap values, and explicitly records the family-balanced point for the common-success sensitivity analysis. `statistics-correction.json` links both reports by hash. This fixes derived reporting determinism without changing a model, experiment budget, realized trace or selection decision.

The current cloud review server is available at `http://127.0.0.1:8003`; a fresh installation can use the CLI default port 8000.

The historical `experiments/phase1-v1/results.csv` has a path-specific CRLF checkout rule matching the original frozen hash. Preserve `.gitattributes` when copying/reconstructing a clean checkout; do not normalize that old file or update its frozen checksum. See [hosted CI investigation](phase-5-ci.md).
