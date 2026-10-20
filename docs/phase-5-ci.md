# Phase 5 hosted CI investigation

The repaired GitHub Actions run [39498108456](https://github.com/Marci99forgrateful/prooflab/actions/runs/39498108456), source `55ee523065f89a349510d3e51d61110f8f44c33c`, **passed**. The actual uploaded JUnit summary reports **106 tests, zero failures/errors/skips**. Bootstrap, Lean build, Ruff, Mypy, Node tests, frontend formatting, browser installation and the full Pytest/browser suite executed successfully.

| Run | Source | Outcome | Evidence |
|---|---|---|---|
| 39495585244 | `181f69d` | Pytest step failed | Installation/build/lint/typing/Node steps passed; direct log and artifact download redirects were blocked by this cloud's egress policy |
| 39497294641 | `45233f3` | 106 tests, 13 failures | Actual JUnit failures were emitted through GitHub Checks annotations; available error annotations identify the frozen legacy CSV checksum guard |
| 39498108456 | `55ee523` | 106 tests, 0 failures | Repaired checkout, complete hosted verification passed |

This was a **repository checkout reproducibility defect**, not a rejected CI allocation or a mathematical failure. Log-download access was a separate infrastructure limitation. The previous Phase 4 account-allocation failures remain historical evidence and do not describe these jobs, which actually started.

`experiments/phase1-v1/results.csv` was originally frozen with 193 CRLF line endings. Its Phase 3 SHA-256 is:

```text
ae34ad35bf05fdc25032e3e2354ea1f76c94c7c1c1ce000dcbcc27162b6e62fe
```

The general `*.csv text eol=lf` rule caused fresh Git checkouts to produce LF bytes instead, with SHA-256 `67e2588b54f37a32e1903729e5181f20ab1831b58d4b16ea1dd74be92280fee6`. The local retained working file still had the correct historical CRLF bytes, explaining why local validation passed while clean hosted checkouts failed.

The repair adds only a path-specific checkout rule:

```gitattributes
experiments/phase1-v1/results.csv text eol=crlf
```

The committed Git data blob remains the same normalized blob. CSV values, original working bytes, all frozen manifests, model weights, candidate/search code, budgets and experimental results are unchanged. A fresh committed clone after the repair passes every frozen hash check and restores the exact original CRLF SHA-256. No checksum was relaxed and no test was disabled.

`scripts/ci_test_summary.py` preserves the underlying failed outcome and publishes bounded, escaped JUnit failure annotations through the permitted GitHub Checks API. It also rejects zero-test/all-skipped validation. This makes genuine diagnostics inspectable without bypassing the proxy or requesting new credentials/domains. GitHub limits per-step error annotations, so the 106/13 summary is retained alongside the available individual errors.

[Machine-readable hosted record](../artifacts/phase5-hosted-ci.json) · [Actual diagnostic annotations](../artifacts/phase5-hosted-ci-diagnostic-annotations.json) · [Clean-checkout reproduction](../artifacts/phase5-checkout-reproduction.json) · [Local validation](../artifacts/phase5-validation.json).

An evidence-only follow-up commit triggers another automatic verification; the PR checks identify its latest status. No merge or publication is performed.
