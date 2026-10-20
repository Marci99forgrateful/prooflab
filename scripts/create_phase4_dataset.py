"""Original statement-only Phase 4 families. Run once before the immutable freeze."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "contrapositive_obligations": (
        "logic",
        [
            ("contra_pair", "(P Q R : Prop) (f : P → Q) (g : Q → R)", "¬ R → ¬ P ∧ ¬ Q"),
            ("contra_disj", "(P Q R S : Prop) (f : P → R) (g : Q → S)", "¬ R ∧ ¬ S → ¬ (P ∨ Q)"),
            ("contra_nested", "(P Q R S : Prop) (f : P ∧ Q → R) (g : R → S) (hq : Q)", "¬ S → ¬ P"),
            (
                "contra_choice",
                "(P Q R : Prop) (f : P → R) (g : Q → R)",
                "¬ R → (¬ P ∧ ¬ Q) ∧ ¬ (P ∨ Q)",
            ),
        ],
    ),
    "quantified_witness_obligations": (
        "logic",
        [
            (
                "witness_pair",
                "(α : Type) (P Q : α → Prop) (a : α) (p : P a) (f : ∀ x, P x → Q x)",
                "∃ x, P x ∧ Q x",
            ),
            (
                "witness_chain",
                "(α : Type) (P Q R : α → Prop) (a : α) (p : P a) (f : ∀ x, P x → Q x) (g : ∀ x, Q x → R x)",
                "∃ x, Q x ∧ R x",
            ),
            (
                "witness_transport",
                "(α β : Type) (f : α → β) (P : α → Prop) (Q : β → Prop) (a : α) (p : P a) (h : ∀ x, P x → Q (f x))",
                "∃ y, Q y",
            ),
            (
                "witness_exists",
                "(α : Type) (P Q R : α → Prop) (h : ∃ x, P x ∧ Q x) (f : ∀ x, Q x → R x)",
                "∃ x, P x ∧ R x",
            ),
        ],
    ),
    "function_relational_transport": (
        "order",
        [
            (
                "transport_edge",
                "(α : Type) (R : α → α → Prop) (f : α → α) (a b : α) (h : R a b) (m : ∀ x y, R x y → R (f x) (f y))",
                "R (f (f a)) (f (f b))",
            ),
            (
                "transport_chain",
                "(α : Type) (R : α → α → Prop) (f : α → α) (a b c : α) (ab : R a b) (bc : R b c) (t : ∀ x y z, R x y → R y z → R x z) (m : ∀ x y, R x y → R (f x) (f y))",
                "R (f a) (f c) ∧ R a c",
            ),
            (
                "transport_fixed",
                "(α : Type) (R : α → α → Prop) (f : α → α) (a b : α) (h : R a b) (k : f a = a) (m : ∀ x y, R x y → R (f x) (f y))",
                "R a (f b)",
            ),
            (
                "transport_symmetric",
                "(α : Type) (R : α → α → Prop) (f : α → α) (a b : α) (h : R a b) (s : ∀ x y, R x y → R y x) (m : ∀ x y, R x y → R (f x) (f y))",
                "R (f b) (f a) ∧ R b a",
            ),
        ],
    ),
    "lattice_meet_join_bounds": (
        "order",
        [
            ("lattice_meet", "(α : Type) [Lattice α] (a b c : α) (h : a ≤ b)", "a ⊓ c ≤ b"),
            ("lattice_join", "(α : Type) [Lattice α] (a b c : α) (h : b ≤ c)", "a ⊓ b ≤ c ⊔ a"),
            (
                "lattice_nested",
                "(α : Type) [Lattice α] (a b c d : α) (h : b ≤ c)",
                "(a ⊓ b) ⊓ d ≤ c ⊔ d",
            ),
            (
                "lattice_product",
                "(α : Type) [Lattice α] (a b c : α) (h : a ≤ b) (k : b ≤ c)",
                "a ⊓ b ≤ c ∧ a ≤ b ⊔ c",
            ),
        ],
    ),
    "group_inverse_context": (
        "algebra",
        [
            ("inverse_right", "(G : Type) [Group G] (a b c : G) (h : a = b)", "(a * c) * c⁻¹ = b"),
            ("inverse_left", "(G : Type) [Group G] (a b c : G) (h : a = b)", "c⁻¹ * (c * a) = b"),
            (
                "inverse_chain",
                "(G : Type) [Group G] (a b c d : G) (h : a = b) (k : b = c)",
                "(a * d) * d⁻¹ = c",
            ),
            (
                "inverse_product",
                "(G : Type) [Group G] (a b c : G) (h : a = b)",
                "((a * c) * c⁻¹ = b) ∧ (c⁻¹ * (c * a) = b)",
            ),
        ],
    ),
    "semiring_cubic_normalization": (
        "algebra",
        [
            (
                "cubic_context",
                "(K : Type) [CommSemiring K] (a b x : K) (h : a = b)",
                "(a+x)^3 = b^3 + 3*b^2*x + 3*b*x^2 + x^3",
            ),
            (
                "cubic_two_contexts",
                "(K : Type) [CommSemiring K] (a b x y : K) (h : a = b) (k : x = y)",
                "(a+x)^3 = b^3 + 3*b^2*y + 3*b*y^2 + y^3",
            ),
            (
                "cubic_factor",
                "(K : Type) [CommSemiring K] (a b x y : K) (h : a = b)",
                "(a+x)*(a+y)*(x+y) = b^2*x+b^2*y+b*x^2+2*b*x*y+b*y^2+x^2*y+x*y^2",
            ),
            (
                "cubic_pair",
                "(K : Type) [CommSemiring K] (a b x : K) (h : a = b)",
                "((a+x)^3 = b^3+3*b^2*x+3*b*x^2+x^3) ∧ (a*(x+1)^2 = b*x^2+2*b*x+b)",
            ),
        ],
    ),
    "set_preimage_obligations": (
        "sets",
        [
            (
                "preimage_chain",
                "(α β : Type) (f : α → β) (A B C : Set β) (h : A ⊆ B) (k : B ⊆ C)",
                "f ⁻¹' A ⊆ f ⁻¹' C",
            ),
            (
                "preimage_inter",
                "(α β : Type) (f : α → β) (A B C : Set β) (h : A ⊆ C)",
                "f ⁻¹' (A ∩ B) ⊆ f ⁻¹' (C ∩ B)",
            ),
            (
                "preimage_union",
                "(α β : Type) (f : α → β) (A B C : Set β) (h : A ⊆ C) (k : B ⊆ C)",
                "f ⁻¹' (A ∪ B) ⊆ f ⁻¹' C",
            ),
            (
                "preimage_diff",
                "(α β : Type) (f : α → β) (A B C : Set β) (h : A ⊆ B)",
                "f ⁻¹' (A \\ C) ⊆ f ⁻¹' (B \\ C)",
            ),
        ],
    ),
    "set_partition_obligations": (
        "sets",
        [
            ("partition_inter", "(α : Type) (A B C : Set α)", "(A ∩ B) ∪ (A \\ B) ⊆ A ∪ C"),
            (
                "partition_exclusion",
                "(α : Type) (A B C : Set α) (h : A ⊆ C)",
                "(A \\ B) ∪ (A ∩ B) ⊆ C",
            ),
            (
                "partition_nested",
                "(α : Type) (A B C D : Set α) (h : A ⊆ D)",
                "((A ∩ B) \\ C) ∪ ((A \\ B) ∩ C) ⊆ D",
            ),
            (
                "partition_pair",
                "(α : Type) (A B C : Set α)",
                "((A \\ B) ∩ C ⊆ A) ∧ (A ∩ (B \\ C) ⊆ B)",
            ),
        ],
    ),
}
PILOT = [
    ("pilot_contra", "logic", "(P Q R : Prop) (f : P → Q) (g : Q → R)", "¬ R → ¬ P"),
    (
        "pilot_witness",
        "logic",
        "(α : Type) (P Q : α → Prop) (a : α) (h : P a) (k : Q a)",
        "∃ x, Q x ∧ P x",
    ),
    ("pilot_lattice", "order", "(α : Type) [Lattice α] (a b c : α)", "a ⊓ b ≤ a ⊔ c"),
    ("pilot_inverse", "algebra", "(G : Type) [Group G] (a b : G)", "(a * b) * b⁻¹ = a"),
    (
        "pilot_preimage",
        "sets",
        "(α β : Type) (f : α → β) (A B : Set β) (h : A ⊆ B)",
        "f ⁻¹' A ⊆ f ⁻¹' B",
    ),
    (
        "pilot_cubic",
        "algebra",
        "(K : Type) [CommSemiring K] (a x : K)",
        "(a+x)^3 = a^3+3*a^2*x+3*a*x^2+x^3",
    ),
]


def task(ident, domain, binders, target, family, split):
    return dict(
        id="p4_" + ident,
        title=ident.replace("_", " ").capitalize(),
        domain=domain,
        difficulty="challenge",
        split=split,
        binders=binders,
        target=target,
        display=target,
        description="Phase 4 · " + family.replace("_", " "),
        forbidden_lemmas=["prooflab_result"],
        origin="Original Phase 4 statement; no benchmark proof imported; no novelty claimed.",
    )


def main():
    directory = ROOT / "benchmarks/phase4"
    if (directory / "frozen.json").exists():
        raise ValueError("Cannot rewrite frozen Phase 4 statements")
    directory.mkdir(parents=True, exist_ok=True)
    final = [
        task(i, d, b, t, f, "held_out") for f, (d, rows) in FAMILIES.items() for i, b, t in rows
    ]
    pilot = [task(i, d, b, t, "difficulty pilot", "development") for i, d, b, t in PILOT]
    for name, value in [
        ("evaluation", final),
        ("pilot", pilot),
        ("families", {"p4_" + i: f for f, (_, rows) in FAMILIES.items() for i, _, _ in rows}),
    ]:
        (directory / f"{name}.json").write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        )


if __name__ == "__main__":
    main()
