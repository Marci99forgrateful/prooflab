# Lean integration and trust policy

`ProofLab/Bridge.lean` is compiled against the exact `lean-toolchain` and Lake
manifest in this repository. The native `prooflab_session` tactic starts inside
an anonymous theorem. It returns a JSON initial state, then accepts bounded
`parent` snapshot IDs and generated tactic strings over two private FIFOs.

Each request:

1. Restores `Lean.Elab.Tactic.SavedState`, including term elaborator and tactic
   state, local contexts, metavariable assignments and goals.
2. Parses the tactic using the current Lean environment.
3. Executes `evalTactic` with recovery disabled, a fresh heartbeat window and
   bounded recursion. Synthetic metavariables are synthesized.
4. Returns actual unsolved goals, instantiated target text, weak-head-normalized
   head constants, binder information and local declarations.
5. Saves accepted states. On any tactic exception, restores the parent.

All accepted transitions are results of real Lean execution. Python does not
simulate introduction, rewriting, unification, elimination or proof terms.
Goal normalization and `isProp` classification are also performed by Lean.
Pretty text is used to propose some candidates; it is never proof evidence.

## Final verification

The selected path is reconstructed as a complete `prooflab_result` declaration
in a new temporary file. A fresh `lake env lean --memory=2048` invocation
elaborates and kernel checks it. `#prooflab_audit` then traverses transitive
axiom dependencies using `Lean.collectAxioms`.

Only `propext`, `Classical.choice` and `Quot.sound` are accepted. In particular,
`sorryAx`, native evaluation axioms and newly introduced arbitrary axioms are
rejected. A lexical screen additionally rejects `sorry`, `admit`, `unsafe`,
`run_tac`, `native_decide` and other obvious bypass constructs. The axiom audit,
successful process exit, and audit JSON are all required; a solved goal list is
not a certificate. The returned source SHA-256 binds verification to the exact
downloadable artifact.

The production Lean module contains no admitted theorem or new axiom. The
test suite deliberately creates an untrusted axiom in an isolated temporary
file to verify that the audit rejects its use.

## Process behavior

Lean has a 2048 MB allocation limit; heartbeats, tactic wall-time, total run
wall-time, expansions, attempts and depth are separately bounded. A timeout or
cancellation terminates the entire process group and closes private FIFOs.
A timed-out worker is never reused. Diagnostics and protocol data use separate
channels. Protocol response frames are capped at 2 MB.

Failed candidate, execution error, cancellation, exhausted search, resource
limit and verified result are distinguished in JSON. An incomplete search
does not disprove its statement. Startup and final-audit costs are recorded
separately from candidate interaction time and Python planning time.

Lean APIs are compiler-version-specific, not promised stable across releases.
Update Lean and Mathlib together, rebuild and rerun the restoration, rejection,
audit and generated-proof integration tests before claiming compatibility.
