# Reproducing ProofLab v0.7.0

Use `feature/phase7-budget-aware-learning`, based on Phase 6 commit `a8af9eb8698819d07bb10f7f1bacd855f9b1213a`. Its draft PR targets `feature/phase6-adaptive-hybrid`; no automatic merge is authorized. MathVerify is unrelated and unchanged.

Linux, Python 3.12+, uv 0.12.23, Node.js 24/npm, Lean 4.24.0 and the committed Mathlib revision are retained. Python and npm lockfiles keep the same dependency versions as Phase 6; only the local package version changes. Development/training uses NumPy on CPU and two native data-collection workers. No API key, paid inference or GPU is required.

Each cloud task already has an isolated checkout. Use it directly rather than creating a Git worktree. With the retained cloud toolchain:

```bash
cd /workspace/prooflab
export ELAN_HOME=/workspace/.toolchains/elan
export PATH="$ELAN_HOME/bin:$PATH"
export XDG_CACHE_HOME=/workspace/.cache
export UV_CACHE_DIR=/workspace/.cache/uv
export UV_SYSTEM_CERTS=true
export npm_config_cache=/workspace/.cache/npm
export MPLCONFIGDIR=/workspace/.cache/matplotlib
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
uv sync --frozen --extra dev
lake build ProofLab
```

The standard `bash scripts/bootstrap.sh` restores caches and exports all replay datasets. If the current network excludes `lakecache.blob.core.windows.net`, compile the pinned imports with `lake build ProofLab` instead of disabling trust checks. A retained manual Lean installation uses official GitHub release artifacts with published SHA-256 verification. Preserve inherited proxy and CA settings. `.gitattributes` requires CRLF for the historical `experiments/phase1-v1/results.csv`; its exact frozen research bytes must not be normalized.

## Immutable scientific boundaries

`benchmarks/phase7/frozen.json` hashes the 64 development/48 evaluation statements, families, reused-development registry and protocol after every statement passes native typed-graph auditing. Structural isomorphism catches alpha/binder-permutation duplicates; it does not establish arbitrary logical inequivalence or external blindness.

The dataset generator refuses existing inputs. Do not rerun it over frozen files. The complete collection and model artifacts are committed, so reproducing training does not require rerunning hundreds of Lean searches. New collections must use a new output directory and preserve their own source hashes:

```bash
uv run --frozen python -m prooflab.phase7 collect --output /tmp/prooflab-phase7-new-development
# Resume only with identical registered source and input hashes:
uv run --frozen python -m prooflab.phase7 collect --output /tmp/prooflab-phase7-new-development --resume
```

The recorded collection uses the committed source hash map in `experiments/phase7/development-v1/provenance.json`. It restores original proof prefixes and runs all three fixed experts at both budgets. `rows.json.gz`, `manifest.json`, all source searches and all continuation traces remain available, including bounded failures and errors. A new runtime can differ near resource limits; it must not replace the published experiment.

```bash
uv run --frozen python -m prooflab.phase7 fit --output /tmp/prooflab-phase7-refit
```

Compare `selected.json`, `root-trained.json`, `linear.json` and `boosted.json` with `models/phase7`. Parameter JSONs reproduce on the pinned environment; wall/CPU/RSS observations in reports need not match. Validation selects architectures and the conservative margin exactly once; it never trains coefficients. Do not choose a new threshold or model after viewing final results.

`models/phase7/frozen.json` pins selected artifacts, training sources, cost semantics, runtime engine and evaluator before the first final search. Historical Phase 6 hashes are verified too. `check_execution()` refuses changed frozen execution sources. A new research iteration requires a new versioned experiment rather than modifying these records.

```bash
uv run --frozen python -c 'from prooflab.phase7_evaluation import check_execution; check_execution()'
uv run --frozen python -m prooflab.phase7 evaluate --output /tmp/prooflab-phase7-new-evaluation
```

The registered final matrix is **48 statements × 11 arms = 528 actual searches**, one repeat per arm, two workers. All arms receive the same 600-attempt, eighty-expansion, depth-twelve, cap-24, eighteen-second engine budget and two-second tactic cap. Aesop/grind are external opaque references. Initialization, queries, prediction and independent verification consume the engine wall budget; archive serialization lies outside the measured call. The preserved Phase 6 wrapper performs small fixed artifact setup before starting its engine clock, while the new engine includes its model setup. Per-run `runner_wall_s` includes both and is retained alongside engine time; nominal clock scopes are not claimed identical at the setup boundary. Session CPU/RSS counters are partial native-process observations, not a complete aggregate machine resource bill.

The final summary includes every outcome, attempt/expansion/state/wall/query/model/verification cost, native heartbeat counter, strategy switch, family result and regression. Paired theorem bootstrap intervals and separate equal-family sensitivity are descriptive at this sample size. Common-success effort is reported separately from all-run effort.

## Web application and checks

```bash
uv run --frozen python scripts/export_phase3.py
uv run --frozen python scripts/export_phase4.py
uv run --frozen python scripts/export_phase5.py
uv run --frozen python scripts/export_phase6.py
uv run --frozen python scripts/export_phase7.py
npm --prefix web ci --no-audit --no-fund
npm --prefix web run build
uv run --frozen prooflab serve
```

For a single registered theorem, retain a new complete trace with a fresh output
filename (existing research output is never overwritten):

```bash
uv run --frozen python -m prooflab.phase7 search \
  --task p7_test_high_degree_factorization_01 --policy conservative \
  --output /tmp/prooflab-p7-proof.json
```

The Policy Learning Explorer supports frozen evaluation, matched root/intermediate development continuations, native state and full-tree inspection, actual prediction/decision records, observed success/failure, full JSON export and cancellable local computation. Recorded development is explicitly separated from new evaluation. All previous explorers and interactions remain available. Static subdirectory replay requires no backend or CDN. The backend continues to bind only to loopback and accepts finite registered theorem IDs, never arbitrary Lean text.

```bash
uv run --frozen ruff check src scripts tests
uv run --frozen ruff format --check src scripts tests
uv run --frozen mypy src/prooflab
npm --prefix web test
npm --prefix web run format:check
PROOFLAB_CHROMIUM=/usr/bin/chromium uv run --frozen pytest -q --junitxml=artifacts/local/phase7-pytest.xml
```

GitHub HTTPS Git access and GitHub API access are separate. In the managed environment, API operations need `api.github.com` allowed in environment settings. Native Git uses the existing platform proxy authentication; no token value belongs in chat, scripts, reports or a credential file. A saved configuration draft does not itself apply network changes or establish a passing hosted CI run.
