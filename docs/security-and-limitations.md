# Security and limitations

The public artifact is static replay only. New Lean computation belongs on a
local machine: the API binds to `127.0.0.1`, validates hosts, rejects cross-origin
and cross-site computation requests, and accepts **only repository-owned task
IDs**. Unknown fields, arbitrary Lean strings, tactic input and paths are rejected.
There is no public custom-code execution endpoint.

The Lean bridge and local Python library are trusted development tools, not a
general hostile-code sandbox. Do not expose them to the Internet, bypass the
loopback binding, or run unreviewed Lean plugins. Existing Mathlib and Lean
dependencies are trusted under their documented licenses and pinned revisions.

Search has explicit depth, state expansion, candidate count, attempt count,
per-tactic time and overall wall-time bounds. Lean has a 2048 MB allocation
limit. Local computation concurrency is two; stored jobs are capped. Cancellation
kills only the spawned process group and removes private temporary files/FIFOs.
These safeguards do not constitute container isolation for arbitrary code.

The independent verifier permits only standard Lean axioms `propext`,
`Classical.choice`, `Quot.sound` and rejects admitted or untrusted-axiom proofs.
Kernel checking is conditional on trusted Lean binaries and imported dependencies;
no formal proof of the implementation itself is claimed.

## Scope

- The mathematical fragment is elementary logic, generic partial orders,
  monoid/ring identities and basic sets. Arbitrary advanced Mathlib theorems
  are outside the demonstrated scope.
- Lemma retrieval uses a bounded curated index and simple type features.
- Conservative path identity retains semantic duplicate states. Pretty-text
  matching proposes some tactics but is never accepted as mathematical evidence.
- Phase 1 held-out data was reserved but not blind. Phase 2 uses a new frozen family split and a genuinely fitted model; see [its data limitations](phase-2-data.md).
- Live search finishes before animated playback; streaming is future work.
- Graph rendering has a node cap. Raw traces preserve all recorded attempts.
- The supported distribution requires the project checkout. A standalone wheel
  without the Lean project/data/web files is not supported.
- Linux is tested. The FIFO transport requires POSIX; Windows is **not tested
  and not supported by the current transport**. macOS is also untested.
- Hosted CI and public deployment status must be reported separately from local
  test success. A workflow file alone is not evidence that a hosted run passed.

An exhausted search never asserts a theorem false. Mathematical novelty,
learned guidance and statistically significant performance improvements are
not claimed in Phase 1.
