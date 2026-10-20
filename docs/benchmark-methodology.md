# Benchmark methodology

> Phase 1 foundation document. Phase 2 implementation and current evidence:
> [model](phase-2-model.md), [frozen data/protocol](phase-2-data.md),
> [measured results](phase-2-results.md), [delivery report](phase-2-final-report.md).

The frozen JSON dataset contains **64 tasks**, 16 each in logic, orders, algebra
and sets. Each subject has six easy, six moderate and four challenge tasks.
The last four form the reserved held-out split: 48 development and 16 held-out.
Difficulty is an engineering label, not independently calibrated psychometrics.

Tasks contain statements, origin, split and forbidden-lemma metadata, no answer
proofs or per-task candidate configuration. A Lean integration test elaborates
all quantified statements and all indexed lemma names. Example scripts discovered
later are outputs in traces, never candidate-generator inputs.

The reserved split is structurally separate from training, and trajectory
exports retain split labels. **This first engineering evaluation is not blinded:**
task statements were visible during development. No model was trained and no
claim of rigorous unseen-data generalization follows from this split alone.
Renamed, independently supplied implication tasks are separately tested.

## Protocol

Freeze and commit the implementation before the measured run. Record exact
code commit, Lean version, Mathlib revision, dataset SHA-256, seed, algorithm
configuration, platform, CPU count, concurrency and all limits. Run both
original policies and the separate native Aesop baseline on every selected task.
Retain all failures and invalid attempts. Do not drop challenging tasks to
improve percentages. There is no per-task timeout tuning.

Both original algorithms share generator, candidate cap and budgets. Aesop is
a separately labelled single native tactic attempt under the same per-call and
overall limits; it is not allowed a larger per-call limit. Its different
internal search is not instrumented as original ProofLab expansions.

Wall time includes Lean initialization, search, final independent checking
and cleanup. Candidate Lean interaction, initialization, verification and
Python planning time are also reported separately. Mean and median include
failures, so a fast incomplete run can appear faster than a verified one;
interpret timing with success and paired-task effort. Concurrent runs share
the host, so timing is descriptive, not a controlled speedup estimate.
Peak process memory is not measured; an explicit Lean memory limit is enforced.

## Outputs and rerun

```bash
uv run --frozen prooflab benchmark --output experiments/my-run \
  --timeout 12 --depth 7 --expansions 60 --attempts 400 --workers 2
python scripts/export_demo.py experiments/my-run
npm --prefix web run build
```

An output directory must not exist: runs are never silently overwritten.
`provenance.json`, `summary.json`, `results.csv`, per-task JSON traces and
`trajectories.jsonl` preserve metadata and outcomes. Research plots are generated
from these actual result files. Repeated experiments and confidence intervals
are future work, not fabricated precision in the first run.

Final source artifacts are freshly re-elaborated and axiom-audited. Every
claimed `verified` outcome records that audit. No proof is accepted from trace
metadata or a visually complete graph alone.
