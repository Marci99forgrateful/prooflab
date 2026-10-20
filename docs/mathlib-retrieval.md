# Mathlib retrieval

The first index is intentionally small: 24 imported declarations grouped into
order, equality, set and algebraic operations. `LEMMAS` in
`src/prooflab/candidates.py` records the exact declaration name and defining
module. Integration tests elaborate every indexed name against pinned Mathlib.

Retrieval matches target operators and relevant type-context features, then
asks Lean to `apply` the selected declaration. Lean performs typeclass
resolution, unification and applicability checking. This is conservative
feature retrieval, **not full type-indexed Mathlib search**. Feature matching
can propose inapplicable candidates and can miss useful declarations. All
actual attempts, failures and lemma provenance are recorded in the trace.

The index does not read benchmark IDs or contain theorem-to-solution mappings.
The benchmark target is introduced only after imports in a fresh anonymous
session; it is not an imported usable named theorem. The independent final
declaration is `prooflab_result`, which is explicitly excluded. Task metadata
supports additional forbidden names and obvious qualified-name aliases.

Name filtering does not automatically detect mathematical equivalence or all
aliases. Elementary benchmark statements can be equivalent to known Mathlib
lemmas. Results therefore distinguish one-step `retrieved_lemma` solutions,
`constructed_derivation`, specialized one-step tactics and native automation.
No statement or proof is claimed mathematically novel.

Future work: extract a larger declaration/type index from the pinned environment,
match normalized conclusion heads and argument patterns, retain source and
license metadata, and evaluate learned retrieval using training-only data.
