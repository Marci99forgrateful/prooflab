# ProofLab

### Learning to Search for Formal Mathematical Proofs

An interactive neuro-symbolic theorem proving laboratory built on Lean 4 and
Mathlib. ProofLab **constructs proof paths** using breadth-first and heuristic
best-first search, visualizes actual failed and successful tactic attempts, and
rechecks every successful proof in a separate Lean process.

No paid model, API key, external inference service, or GPU is required.

```lean
example (P Q R : Prop) (hpq : P → Q) (hqr : Q → R) (hp : P) : R := by
  apply hqr
  apply hpq
  assumption
```

This is a genuine search output, independently checked by Lean. The candidate
generator does not contain per-task answer scripts.

## Quick start

Prerequisites: Linux, Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js
20.19+ (or 22.12+), npm, Git, curl. Allow several GB for Lean and Mathlib.

```bash
git clone https://github.com/Marci99forgrateful/prooflab.git
cd prooflab
bash scripts/bootstrap.sh
uv run --frozen prooflab serve
```

Open the local address printed by the server. The app defaults to clearly
labelled **recorded replay**; choose **Use live search** to compute a new proof.
The backend binds only to the loopback interface and accepts repository-owned
task IDs, never visitor-supplied Lean code.

```bash
uv run --frozen prooflab search imp_chain --algorithm best_first --output proof.json
uv run --frozen pytest
uv run --frozen ruff check src scripts tests
uv run --frozen mypy src/prooflab
npm --prefix web test
```

## What is original?

The structural candidate generator, bounded lemma selection, search scheduling,
trace and trajectory formats, experiment runner, and interactive visualization
are project code applying established methods. Lean supplies elaboration and
kernel verification; Mathlib supplies mathematics, `ring`, and other tactics.
Native Aesop is evaluated only as a separately identified automation baseline.
Hand-designed heuristics are not described as a trained AI model or novel research.

## Status

Phase 1 is under active implementation. Verified capability and benchmark
evidence are recorded in the project documentation; no unexecuted measurement
is presented as a result. Windows compatibility has not been tested.

Apache-2.0 for original code. See LICENSE and the forthcoming dependency notices.
