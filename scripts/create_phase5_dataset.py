# ruff: noqa: E501
"""Original Phase 5 statements; no proof scripts. Refuses a frozen rewrite."""

from __future__ import annotations

import json

from prooflab.lean import ROOT

FAMILIES = {
    "heterogeneous_composition_witness": (
        "logic",
        [
            (
                "compose_terminal",
                "(α β γ : Type) (f : α → β) (g : β → γ) (P : γ → Prop) (a : α) (h : P (g (f a)))",
                "∃ z, P z ∧ z = g (f a)",
            ),
            (
                "compose_pair",
                "(α β γ : Type) (f : α → β) (g : β → γ) (P Q : γ → Prop) (a : α) (h : P (g (f a))) (k : Q (g (f a)))",
                "∃ z, Q z ∧ P z",
            ),
            (
                "compose_conditional",
                "(α β γ : Type) (f : α → β) (g : β → γ) (P : α → Prop) (Q : γ → Prop) (a : α) (h : P a) (t : ∀ x, P x → Q (g (f x)))",
                "∃ z, Q z ∨ False",
            ),
            (
                "compose_disjunction",
                "(α β γ : Type) (f : α → β) (g : β → γ) (P Q : γ → Prop) (a : α) (h : P (g (f a)) ∨ Q (g (f a)))",
                "∃ z, Q z ∨ P z",
            ),
        ],
    ),
    "typed_product_construction": (
        "logic",
        [
            ("product_graph", "(α β : Type) (a : α) (b : β)", "∃ z : α × β, z.1 = a ∧ z.2 = b"),
            (
                "product_predicate",
                "(α β : Type) (a : α) (b : β) (R : α → β → Prop) (h : R a b)",
                "∃ z : α × β, R z.1 z.2",
            ),
            (
                "product_function",
                "(α β γ : Type) (a : α) (b : β) (f : α × β → γ) (P : γ → Prop) (h : P (f (a,b)))",
                "∃ z : α × β, P (f z) ∧ z.1 = a",
            ),
            (
                "product_two_properties",
                "(α β : Type) (a : α) (b : β) (P : α → Prop) (Q : β → Prop) (h : P a) (k : Q b)",
                "∃ z : α × β, Q z.2 ∧ P z.1",
            ),
        ],
    ),
    "inverse_function_consequences": (
        "logic",
        [
            (
                "left_inverse_injective",
                "(α β : Type) (f : α → β) (g : β → α) (h : Function.LeftInverse g f) (a b : α)",
                "f a = f b → a = b",
            ),
            (
                "right_inverse_witness",
                "(α β : Type) (f : α → β) (g : β → α) (h : Function.RightInverse g f) (b : β)",
                "∃ a, f a = b ∧ g (f a) = g b",
            ),
            (
                "inverse_unique",
                "(α β : Type) (f : α → β) (g : β → α) (h : Function.LeftInverse g f) (a b : α) (k : f a = f b)",
                "a = b ∧ g (f a) = b",
            ),
            (
                "inverse_transport",
                "(α β : Type) (f : α → β) (g : β → α) (h : Function.RightInverse g f) (P : β → Prop) (b : β) (p : P b)",
                "∃ a, P (f a) ∧ f a = b",
            ),
        ],
    ),
    "noncommutative_conjugation": (
        "algebra",
        [
            ("conjugate_identity", "(G : Type) [Group G] (a b : G)", "a * (b * b⁻¹) * a⁻¹ = 1"),
            (
                "conjugate_context",
                "(G : Type) [Group G] (a b c : G) (h : a*b = c)",
                "a⁻¹ * c * b⁻¹ = 1",
            ),
            (
                "conjugate_cancel",
                "(G : Type) [Group G] (a b c : G)",
                "(a*b*a⁻¹) * (a*c*a⁻¹) = a*(b*c)*a⁻¹",
            ),
            (
                "inverse_equality",
                "(G : Type) [Group G] (a b c : G) (h : a*b = c)",
                "b = a⁻¹*c ∧ a = c*b⁻¹",
            ),
        ],
    ),
    "lattice_sandwich_constraints": (
        "order",
        [
            (
                "sandwich_eq",
                "(α : Type) [Lattice α] (a b c : α) (h : a ≤ b) (k : b ≤ c) (t : c ≤ a)",
                "(a ⊔ b) ⊓ c = a",
            ),
            (
                "join_upper",
                "(α : Type) [Lattice α] (a b c d : α) (h : a ≤ c) (k : b ≤ c) (t : c ≤ d)",
                "a ⊔ b ≤ c ⊓ d",
            ),
            (
                "meet_lower",
                "(α : Type) [Lattice α] (a b c d : α) (h : a ≤ b) (k : a ≤ c) (t : d ≤ a)",
                "a ⊔ d ≤ b ⊓ c",
            ),
            (
                "two_sided_lattice",
                "(α : Type) [Lattice α] (a b c d : α) (h : a ≤ b) (k : c ≤ d)",
                "a ⊓ c ≤ b ⊔ d ∧ a ⊓ c ≤ b",
            ),
        ],
    ),
    "image_preimage_roundtrip": (
        "sets",
        [
            (
                "image_witness",
                "(α β : Type) (f : α → β) (A : Set α) (a : α) (h : a ∈ A)",
                "∃ y, y ∈ f '' A ∧ y = f a",
            ),
            (
                "image_preimage_element",
                "(α β : Type) (f : α → β) (A : Set α) (B : Set β) (h : ∀ x, x ∈ A → f x ∈ B) (a : α) (k : a ∈ A)",
                "f a ∈ f '' A ∩ B",
            ),
            (
                "preimage_witness",
                "(α β : Type) (f : α → β) (B : Set β) (a : α) (h : f a ∈ B)",
                "∃ x, x ∈ f ⁻¹' B ∧ f x ∈ B",
            ),
            (
                "image_injective_back",
                "(α β : Type) (f : α → β) (A : Set α) (h : Function.Injective f) (a : α) (k : f a ∈ f '' A)",
                "a ∈ A",
            ),
        ],
    ),
    "pointwise_set_exclusion": (
        "sets",
        [
            (
                "exclusion_transport",
                "(α : Type) (A B C : Set α) (a : α) (h : A ⊆ B) (k : a ∈ A \\ C)",
                "a ∈ B ∧ a ∉ C",
            ),
            (
                "exclusion_choice",
                "(α : Type) (A B C : Set α) (a : α) (h : a ∈ A ∪ B) (k : a ∉ C)",
                "a ∈ (A \\ C) ∪ (B \\ C)",
            ),
            (
                "complement_contradiction",
                "(α : Type) (A B : Set α) (a : α) (h : a ∈ A ∩ Bᶜ)",
                "a ∉ B ∧ a ∈ A",
            ),
            (
                "exclusion_disjoint",
                "(α : Type) (A B : Set α) (a : α) (h : a ∈ A \\ B)",
                "¬ (a ∈ B ∧ a ∈ A)",
            ),
        ],
    ),
    "quantified_choice_context": (
        "logic",
        [
            (
                "choice_shared",
                "(α : Type) (P Q R : α → Prop) (a : α) (h : P a ∨ Q a) (f : ∀ x, P x → R x) (g : ∀ x, Q x → R x)",
                "∃ x, R x ∧ (P x ∨ Q x)",
            ),
            (
                "choice_refutation",
                "(α : Type) (P Q : α → Prop) (a : α) (h : P a ∨ Q a) (k : ¬ P a)",
                "∃ x, Q x",
            ),
            (
                "choice_all",
                "(α : Type) (P Q R : α → Prop) (h : ∀ x, P x ∨ Q x) (f : ∀ x, P x → R x) (g : ∀ x, Q x → R x)",
                "∀ x, R x ∧ (Q x ∨ P x)",
            ),
            (
                "choice_exists",
                "(α : Type) (P Q R : α → Prop) (h : ∃ x, P x ∨ Q x) (f : ∀ x, P x → R x) (g : ∀ x, Q x → R x)",
                "∃ x, R x ∨ False",
            ),
        ],
    ),
    "relational_intermediate_witness": (
        "order",
        [
            (
                "relation_middle",
                "(α : Type) (R S : α → α → Prop) (a b c : α) (h : R a b) (k : S b c)",
                "∃ x, R a x ∧ S x c",
            ),
            (
                "relation_composed",
                "(α β : Type) (R : α → α → Prop) (S : β → β → Prop) (f : α → β) (a b c : α) (h : R a b) (k : R b c) (t : ∀ x y, R x y → S (f x) (f y))",
                "∃ y, S (f a) y ∧ S y (f c)",
            ),
            (
                "relation_reverse_middle",
                "(α : Type) (R : α → α → Prop) (a b c : α) (h : R a b) (k : R b c) (s : ∀ x y, R x y → R y x)",
                "∃ x, R c x ∧ R x a",
            ),
            (
                "relation_diagonal",
                "(α : Type) (R : α → α → Prop) (a b : α) (h : R a b) (s : ∀ x y, R x y → R y x) (t : ∀ x y z, R x y → R y z → R x z)",
                "∃ x, R x x ∧ R a x",
            ),
        ],
    ),
    "heterogeneous_binary_congruence": (
        "logic",
        [
            (
                "binary_congruence",
                "(α β γ : Type) (f : α → β → γ) (a a' : α) (b b' : β) (h : a = a') (k : b = b')",
                "f a b = f a' b' ∧ f a' b = f a b'",
            ),
            (
                "binary_predicate",
                "(α β : Type) (R : α → β → Prop) (a a' : α) (b b' : β) (h : a = a') (k : b = b') (r : R a b)",
                "R a' b' ∧ R a b'",
            ),
            (
                "binary_graph_exists",
                "(α β γ : Type) (f : α → β → γ) (a : α) (b : β)",
                "∃ z, z = f a b ∧ f a b = z",
            ),
            (
                "congruence_chain",
                "(α β γ : Type) (f : α → β) (g : β → γ) (a b : α) (h : f a = f b)",
                "g (f a) = g (f b) ∧ g (f b) = g (f a)",
            ),
        ],
    ),
}
PILOT = [
    (
        "pilot_compose",
        "logic",
        "(α β : Type) (f : α → β) (a : α) (P : β → Prop) (h : P (f a))",
        "∃ b, P b ∧ b = f a",
    ),
    ("pilot_pair", "logic", "(α β : Type) (a : α) (b : β)", "∃ z : α × β, z.1 = a"),
    ("pilot_group", "algebra", "(G : Type) [Group G] (a b : G)", "a⁻¹ * (a*b) * b⁻¹ = 1"),
    (
        "pilot_bound",
        "order",
        "(α : Type) [Lattice α] (a b c : α) (h : a ≤ c) (k : b ≤ c)",
        "a ⊔ b ≤ c",
    ),
    (
        "pilot_set",
        "sets",
        "(α β : Type) (f : α → β) (a : α) (A : Set α) (h : a ∈ A)",
        "f a ∈ f '' A",
    ),
    ("pilot_logic", "logic", "(P Q R : Prop) (h : P ∨ Q) (f : P → R) (g : Q → R)", "R ∧ (Q ∨ P)"),
]


def task(i, d, b, t, f, split):
    return dict(
        id="p5_" + i,
        title=i.replace("_", " ").capitalize(),
        domain=d,
        difficulty="challenge",
        split=split,
        binders=b,
        target=t,
        display=t,
        description="Phase 5 · " + f.replace("_", " "),
        forbidden_lemmas=["prooflab_result"],
        origin="Original Phase 5 statement; shared elementary primitives, no mathematical novelty claimed.",
    )


def main():
    folder = ROOT / "benchmarks/phase5"
    folder.mkdir(exist_ok=True)
    if (folder / "frozen.json").exists():
        raise ValueError("Already frozen")
    final = [task(i, d, b, t, f, "held_out") for f, (d, rs) in FAMILIES.items() for i, b, t in rs]
    pilot = [task(i, d, b, t, "development pilot", "development") for i, d, b, t in PILOT]
    for n, v in [
        ("evaluation", final),
        ("pilot", pilot),
        ("families", {"p5_" + i: f for f, (_, rs) in FAMILIES.items() for i, _, _ in rs}),
    ]:
        (folder / (n + ".json")).write_text(json.dumps(v, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
