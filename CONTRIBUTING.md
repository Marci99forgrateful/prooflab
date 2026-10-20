# Contributing

Run `bash scripts/bootstrap.sh`, then `uv run --frozen pytest`,
`uv run --frozen ruff check src scripts tests`, `uv run --frozen mypy src/prooflab`,
and `npm --prefix web test` before proposing a change.

Browser tests require Chromium. Use an installed `chromium`, set
`PROOFLAB_CHROMIUM`, or run `uv run --frozen playwright install --with-deps chromium`.
Do not skip Lean integration tests when changing proof generation or validation.

Preserve the distinction between candidate validity, solved search state, and
independent kernel verification. Never introduce admitted proofs, target answer
tables, test-only proof replacements, or fabricated traces. A new tactic must
remain behind the same independent verifier.

Do not tune on the reserved held-out split or silently change the dataset after
reporting results. Freeze code, record the exact commit and dataset hash, and
retain failures. Describe specialized Mathlib tactics and native Aesop separately
from project search algorithms. Follow `docs/benchmark-methodology.md`.

This repository is independent of MathVerify. Original code and documentation
are Apache-2.0; preserve third-party license notices. AI-assisted engineering
was used for Phase 1, with executable formal verification and recorded testing.
