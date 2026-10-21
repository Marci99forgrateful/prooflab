# ruff: noqa: E501
"""Original mathematical curriculum and unseen combinations, never proof scripts.

All tasks retained after native duplicate auditing; no difficulty selection on test.
"""

from __future__ import annotations

import json

from prooflab.lean import ROOT

D = ROOT / "benchmarks/phase6"
CURRICULUM: dict[str, tuple[str, str, list[tuple[str, str]]]] = {}


def family(name, domain, base, rows):
    CURRICULUM[name] = (domain, base, rows)


family(
    "continuation_logic",
    "logic",
    "(P Q R S : Prop)",
    [
        ("(h : (P → R) ∧ (Q → R)) (k : P ∨ Q)", "R"),
        ("(h : P → Q → R) (k : P) (t : Q)", "R ∧ P"),
        ("(h : (P ∧ Q) → R) (k : P) (t : Q)", "R ∨ S"),
        ("(h : P → Q) (k : Q → R) (t : R → S)", "P → S"),
        ("(h : P ∨ Q) (k : P → R) (t : Q → S)", "R ∨ S"),
        ("(h : P → False) (k : P ∨ (Q ∧ R))", "R ∧ Q"),
        ("(h : P ↔ Q) (k : Q → R) (t : R → P)", "Q ↔ R"),
        ("(h : (P → R) → S) (k : Q → R) (t : Q)", "S"),
        ("(h : P → Q → False) (k : Q)", "¬ P"),
        ("(h : P ∧ (Q ∨ R)) (k : P → Q → S) (t : R → S)", "S"),
    ],
)
family(
    "quantifier_transport",
    "logic",
    "(α : Type) (P Q R : α → Prop)",
    [
        ("(h : ∀ x, P x → Q x) (k : ∃ x, P x ∧ R x)", "∃ x, Q x ∧ R x"),
        ("(h : ∀ x, P x ∧ Q x)", "(∀ x, P x) ∧ (∀ x, Q x)"),
        ("(h : ∀ x, P x → Q x) (k : ∀ x, Q x → R x)", "∀ x, P x → R x"),
        ("(h : ∃ x, P x ∧ Q x) (k : ∀ x, Q x → False)", "False"),
        ("(a : α) (h : P a) (k : ∀ x, P x → Q x ∨ R x)", "∃ x, Q x ∨ R x"),
        ("(h : ∀ x, P x ↔ Q x) (k : ∃ x, Q x)", "∃ x, P x"),
        ("(h : ∀ x, P x → Q x) (k : ∀ x, ¬ Q x)", "∀ x, ¬ P x"),
        ("(h : ∃ x, P x) (k : ∀ x, P x → ∀ y, Q y → R x)", "(∃ y, Q y) → ∃ x, R x"),
        ("(h : ∀ x, P x ∨ Q x) (k : ∀ x, ¬ P x)", "∀ x, Q x"),
        ("(h : ∀ x, P x → Q x ∧ R x)", "∀ x, P x → R x ∧ Q x"),
    ],
)
family(
    "relation_closure",
    "order",
    "(α : Type) (R : α → α → Prop) (a b c d : α)",
    [
        ("(h : R a b) (k : R b c) (t : ∀ x y z, R x y → R y z → R x z)", "R a c"),
        ("(h : R a b) (s : ∀ x y, R x y → R y x)", "R b a ∧ R a b"),
        ("(h : R a b) (k : R b c) (l : R c d) (t : ∀ x y z, R x y → R y z → R x z)", "R a d"),
        ("(h : R a b) (s : ∀ x y, R x y → R y x) (t : ∀ x y z, R x y → R y z → R x z)", "R b b"),
        ("(h : ∀ x, R x x)", "R a a ∧ R b b"),
        ("(h : ∀ x y, R x y → x = y) (k : R a b)", "R b a"),
        ("(h : R a b) (s : ∀ x y, R x y → R y x) (k : R a c)", "∃ x, R x a ∧ R a c"),
        ("(h : ∀ x y, R x y → ¬ R y x) (k : R a b)", "¬ R b a"),
        ("(h : ∀ x y, R x y ↔ x = y)", "R a a"),
        ("(h : R a b ∨ R a c) (k : R a b → R a d) (l : R a c → R a d)", "R a d"),
    ],
)
family(
    "ordered_bounds",
    "order",
    "(α : Type) [PartialOrder α] (a b c d : α)",
    [
        ("(h : a ≤ b) (k : c ≤ d) (l : b ≤ c)", "a ≤ d ∧ a ≤ c"),
        ("(h : a ≤ b) (k : b ≤ a)", "a = b ∧ b ≤ a"),
        ("(h : a ≤ b) (k : b ≤ c) (l : c ≤ a)", "a = c"),
        ("(h : a = b) (k : c ≤ a)", "c ≤ b"),
        ("(h : a ≤ b) (k : b ≤ c)", "a ≤ c ∧ a ≤ b"),
        ("(h : a < b) (k : b ≤ c)", "a < c"),
        ("(h : a ≤ b) (k : b < c)", "a < c"),
        ("(h : a < b)", "¬ b ≤ a"),
        ("(h : a = b) (k : b = c)", "c ≤ a"),
        ("(h : a ≤ b) (k : c ≤ d) (l : b ≤ c)", "a ≤ d ∧ b ≤ d"),
    ],
)
family(
    "lattice_maps",
    "order",
    "(α : Type) [Lattice α] (a b c : α)",
    [
        ("", "a ⊓ b ≤ b ⊔ c"),
        ("", "a ≤ a ⊔ (b ⊓ c)"),
        ("", "(a ⊓ b) ⊓ c ≤ a"),
        ("(h : a ≤ b)", "a ⊓ c ≤ b ⊔ c"),
        ("(h : a ≤ c) (k : b ≤ c)", "a ⊔ b ≤ c ⊔ (a ⊓ b)"),
        ("(h : c ≤ a) (k : c ≤ b)", "c ≤ a ⊓ b"),
        ("", "(a ⊓ b) ⊔ (a ⊓ c) ≤ a"),
        ("", "a ≤ (a ⊔ b) ⊓ (a ⊔ c)"),
        ("(h : a ≤ b)", "a ⊔ b = b"),
        ("(h : b ≤ a)", "a ⊓ b = b"),
    ],
)
family(
    "monoid_words",
    "algebra",
    "(M : Type) [Monoid M] (a b c : M)",
    [
        ("", "(a * 1) * (1 * b) = a * b"),
        ("", "a * (b * (c * 1)) = (a * b) * c"),
        ("(h : a * b = c)", "(a * 1) * b = c"),
        ("(h : a = 1)", "(b * a) * c = b * c"),
        ("(h : a * b = 1)", "(a * b) * c = c"),
        ("", "(1 * a) * (b * c) = (a * b) * c"),
        ("(h : b = c)", "a * (b * 1) = a * c"),
        ("(h : a * b = c)", "a * (b * a) = c * a"),
        ("", "(a * b) * (1 * c) = a * (b * c)"),
        ("(h : b * c = 1)", "(a * b) * c = a"),
    ],
)
family(
    "group_equations",
    "algebra",
    "(G : Type) [Group G] (a b c : G)",
    [
        ("", "(a * b)⁻¹ * (a * b) = 1"),
        ("", "(a * a⁻¹) * b = b"),
        ("", "a * (a⁻¹ * b) = b"),
        ("", "(a * b) * b⁻¹ = a"),
        ("(h : a * b = c)", "a * b * c⁻¹ = 1"),
        ("(h : a * b = 1)", "b = a⁻¹"),
        ("(h : a = b)", "a⁻¹ * b = 1"),
        ("", "(a⁻¹)⁻¹ * 1 = a"),
        ("", "(a * 1)⁻¹ = a⁻¹"),
        ("(h : a * b = c)", "c * b⁻¹ = a"),
    ],
)
family(
    "ring_expansion",
    "algebra",
    "(R : Type) [CommRing R] (a b c : R)",
    [
        ("", "(a+b)*(a-b) = a^2-b^2"),
        ("", "(a+b)^2 = a^2+2*a*b+b^2"),
        ("", "(a+b)*c = c*a+b*c"),
        ("", "(a-b)^2 = a^2-2*a*b+b^2"),
        ("(h : a=b+c)", "a*b = b^2+b*c"),
        ("", "(a+b+c)^2 = a*a+b*b+c*c+2*(a*b+a*c+b*c)"),
        ("", "a*(b-c)+a*c = a*b"),
        ("", "(a+b)*(a+b) - (a-b)*(a-b) = 4*a*b"),
        ("(h : a*b=c)", "a*b+a*b = 2*c"),
        ("", "(a+b)^3 = a^3+3*a^2*b+3*a*b^2+b^3"),
    ],
)
family(
    "set_images",
    "sets",
    "(α β : Type) (f : α → β) (A B : Set α) (a : α)",
    [
        ("(h : a ∈ A)", "f a ∈ f '' A"),
        ("(h : a ∈ A ∩ B)", "f a ∈ f '' A ∩ f '' B"),
        ("(h : a ∈ A ∪ B)", "f a ∈ f '' A ∪ f '' B"),
        ("(h : A ⊆ B)", "f '' A ⊆ f '' B"),
        ("", "f '' (A ∪ B) = f '' A ∪ f '' B"),
        ("", "f '' (A ∩ B) ⊆ f '' B"),
        ("(h : a ∈ B)", "∃ y, y ∈ f '' B"),
        ("(h : f a ∉ f '' A)", "a ∉ A"),
        ("", "f '' (∅ : Set α) = ∅"),
        ("", "f '' ({a} : Set α) = {f a}"),
    ],
)
family(
    "preimage_algebra",
    "sets",
    "(α β : Type) (f : α → β) (A B : Set β)",
    [
        ("", "f ⁻¹' (A ∩ B) = (f ⁻¹' A) ∩ (f ⁻¹' B)"),
        ("", "f ⁻¹' (A ∪ B) = (f ⁻¹' A) ∪ (f ⁻¹' B)"),
        ("", "f ⁻¹' Aᶜ = (f ⁻¹' A)ᶜ"),
        ("", "f ⁻¹' (A \\ B) = (f ⁻¹' A) \\ (f ⁻¹' B)"),
        ("(h : A ⊆ B)", "(f ⁻¹' A) \\ (f ⁻¹' B) = ∅"),
        ("", "f ⁻¹' (∅ : Set β) = ∅"),
        ("", "f ⁻¹' (Set.univ : Set β) = Set.univ"),
        ("(a : α) (h : f a ∈ A) (k : f a ∉ B)", "a ∈ f ⁻¹' (A \\ B)"),
        ("(a : α) (h : a ∈ f ⁻¹' A)", "f a ∈ A"),
        ("", "(f ⁻¹' A) ∩ (f ⁻¹' B) ⊆ f ⁻¹' A"),
    ],
)
family(
    "set_difference",
    "sets",
    "(α : Type) (A B C : Set α)",
    [
        ("", "(A \\ B) ∩ B = ∅"),
        ("", "A \\ A = ∅"),
        ("", "A ∩ Aᶜ = ∅"),
        ("", "(A \\ B) ⊆ A"),
        ("", "(A ∩ B) \\ C = (A \\ C) ∩ (B \\ C)"),
        ("", "A \\ (B ∪ C) = (A \\ B) ∩ (A \\ C)"),
        ("(h : A ⊆ B)", "(A \\ C) ∩ B = A \\ C"),
        ("", "A ∪ (A ∩ B) = A"),
        ("", "(A ∪ B)ᶜ = Aᶜ ∩ Bᶜ"),
        ("", "(A \\ B) ∪ (A ∩ B) = A"),
    ],
)
family(
    "function_retractions",
    "logic",
    "(α β : Type) (f : α → β) (g : β → α)",
    [
        ("(h : Function.LeftInverse g f)", "Function.Injective f"),
        ("(h : Function.RightInverse g f)", "Function.Surjective f"),
        ("(h : Function.LeftInverse g f) (a : α)", "g (f (g (f a))) = a"),
        ("(h : Function.RightInverse g f) (b : β)", "f (g (f (g b))) = b"),
        ("(h : Function.Injective f) (a b : α) (k : f a = f b)", "g (f a) = g (f b) ∧ a = b"),
        ("(h : Function.Surjective f) (P : β → Prop) (k : ∀ a, P (f a))", "∀ b, P b"),
        ("(h : Function.LeftInverse g f) (a : α)", "∃ b, g b = a"),
        ("(h : Function.RightInverse g f) (b : β)", "∃ a, f a = b"),
        ("(h : Function.Injective f) (a b : α)", "f a = f b ↔ a = b"),
        ("(h : Function.LeftInverse g f) (k : Function.RightInverse g f)", "Function.Bijective f"),
    ],
)
family(
    "curried_construction",
    "logic",
    "(α β γ : Type) (f : α → β → γ) (a : α) (b : β)",
    [
        ("", "∃ z, z = f a b"),
        ("(P : γ → Prop) (h : ∀ x y, P (f x y))", "∃ z, P z"),
        ("(P Q : γ → Prop) (h : ∀ x y, P (f x y) ∧ Q (f x y))", "∃ z, Q z ∧ P z"),
        ("(P : γ → Prop) (h : P (f a b))", "∃ z, z = f a b ∧ P z"),
        ("(g : γ → α)", "∃ x, x = g (f a b)"),
        ("(g : γ → β) (P : β → Prop) (h : ∀ x y, P (g (f x y)))", "∃ z, P z"),
        ("", "∃ k : β → γ, k b = f a b"),
        ("", "∃ z : γ × α, z.1 = f a b ∧ z.2 = a"),
        ("(P : γ → Prop) (h : ∀ x y, P (f x y))", "∃ z, P z ∨ False"),
        ("(g : γ → γ)", "∃ z, z = g (f a b) ∧ z = g (f a b)"),
    ],
)
family(
    "product_graphs",
    "logic",
    "(α β γ : Type) (a : α) (b : β) (c : γ)",
    [
        ("", "∃ z : α × β × γ, z.1 = a ∧ z.2.1 = b ∧ z.2.2 = c"),
        ("", "∃ z : (α × β) × γ, z.1.1 = a ∧ z.1.2 = b ∧ z.2 = c"),
        ("(f : α × β → γ)", "∃ z : α × β, f z = f (a,b)"),
        ("(P : α → Prop) (h : P a)", "∃ z : α × β, P z.1"),
        ("(R : α → β → Prop) (h : ∀ x y, R x y)", "∃ z : α × β, R z.1 z.2"),
        ("(f : α → γ)", "∃ z : γ × β, z.1 = f a ∧ z.2 = b"),
        ("(P : β → Prop) (h : P b)", "∃ z : β × α, P z.1 ∧ z.2 = a"),
        ("(f : α → β → γ)", "∃ z : α × γ, z.1 = a ∧ z.2 = f a b"),
        ("", "∃ z : β × γ, z.2 = c ∧ z.1 = b"),
        ("(f : α × β → γ) (P : γ → Prop) (h : ∀ z, P (f z))", "∃ z : α × β, P (f z)"),
    ],
)
family(
    "dependent_contexts",
    "logic",
    "(α : Type) (β : α → Type) (a : α) (b : β a)",
    [
        ("", "∃ z : β a, z = b"),
        ("(P : ∀ x, β x → Prop) (h : P a b)", "∃ z, P a z"),
        ("(f : ∀ x, β x → β x)", "∃ z, z = f a b"),
        ("(f : ∀ x, β x) (P : ∀ x, β x → Prop) (h : ∀ x, P x (f x))", "∃ z : β a, P a z"),
        ("(P Q : β a → Prop) (h : P b) (k : Q b)", "∃ z, Q z ∧ P z ∧ z = b"),
        ("(f : ∀ x, β x) (g : β a → β a)", "∃ z, z = g (f a)"),
        ("(P : β a → Prop) (h : ∀ z, P z)", "P b ∧ ∃ z, P z"),
        ("(f : ∀ x, β x → α)", "∃ x : α, x = f a b"),
        ("(P : β a → Prop) (h : P b)", "∃ z : β a × β a, P z.1 ∧ P z.2"),
        ("(c : β a) (h : b = c) (P : β a → Prop) (k : P b)", "P c ∧ b = c"),
    ],
)
family(
    "heterogeneous_transport",
    "logic",
    "(α β γ : Type) (f : α → β) (g : β → γ) (a c : α)",
    [
        ("(h : a = c)", "f a = f c ∧ g (f a) = g (f c)"),
        ("(P : β → Prop) (h : a = c) (k : P (f a))", "P (f c) ∧ g (f a) = g (f c)"),
        ("(h : f a = f c)", "∃ z, z = g (f a) ∧ z = g (f c)"),
        ("(P : γ → Prop) (h : ∀ x, P (g (f x)))", "∃ z, P z ∧ z = g (f c)"),
        ("(h : g (f a) = g (f c))", "g (f c) = g (f a)"),
        ("(k : γ → α) (h : ∀ x, k (g (f x)) = x)", "k (g (f a)) = a ∧ k (g (f c)) = c"),
        ("(h : Function.Injective g) (k : g (f a) = g (f c))", "f a = f c"),
        ("(h : Function.Injective f) (k : f a = f c)", "a = c ∧ g (f a) = g (f c)"),
        ("(P Q : γ → Prop) (h : P (g (f a)) → Q (g (f a))) (k : P (g (f a)))", "∃ z, P z ∧ Q z"),
        ("(h : ∀ x, g (f x) = g (f a))", "∀ x, g (f x) = g (f c)"),
    ],
)

# New combinations/families, fixed independently of any solver output.
TEST = {
    "ternary_witness_pipeline": (
        "logic",
        "(α β γ δ : Type) (f : α → β → γ → δ) (a : α) (b : β) (c : γ)",
        [
            ("(P : δ → Prop) (h : ∀ x y z, P (f x y z))", "∃ t, P t"),
            (
                "(P Q : δ → Prop) (h : ∀ x y z, P (f x y z)) (k : ∀ x y z, Q (f x y z))",
                "∃ t, Q t ∧ P t",
            ),
            ("(g : δ → α) (P : α → Prop) (h : ∀ x y z, P (g (f x y z)))", "∃ t, P t"),
            ("(P : δ → Prop) (h : ∀ x y z, P (f x y z))", "∃ t, P t ∧ t = f a b c"),
        ],
    ),
    "callable_composition": (
        "logic",
        "(α β γ δ : Type) (f : α → β → γ) (g : γ → δ) (a : α) (b : β)",
        [
            ("(P : δ → Prop) (h : ∀ x y, P (g (f x y)))", "∃ t, P t ∧ t = g (f a b)"),
            ("(k : δ → α) (P : α → Prop) (h : ∀ x y, P (k (g (f x y))))", "∃ t, P t"),
            ("(P : γ → Prop) (h : ∀ x y, P (f x y))", "∃ t : γ × β, P t.1 ∧ t.2 = b"),
            ("(k : α → β) (P : δ → Prop) (h : ∀ x, P (g (f x (k x))))", "∃ t, P t"),
        ],
    ),
    "conjugation_commutator_words": (
        "algebra",
        "(G : Type) [Group G] (a b c d : G)",
        [
            ("", "(a*b*c) * c⁻¹ * b⁻¹ * a⁻¹ = 1"),
            ("", "(a*b*a⁻¹)⁻¹ = a*b⁻¹*a⁻¹"),
            ("(h : a*b = c*d)", "a⁻¹*c*d*b⁻¹ = 1"),
            ("", "(a*b*a⁻¹)*(a*c*a⁻¹)*(a*d*a⁻¹) = a*(b*c*d)*a⁻¹"),
        ],
    ),
    "noncommutative_context_systems": (
        "algebra",
        "(G : Type) [Group G] (a b c d : G)",
        [
            ("(h : a*b=c) (k : c*d=1)", "b*d=a⁻¹"),
            ("(h : a*b=c*d)", "c⁻¹*a*b=d"),
            ("(h : a*b=c) (k : b*d=1)", "c*d=a ∧ a⁻¹*c=b"),
            ("(h : a*b=c) (k : c⁻¹*d=b⁻¹)", "a*b*b⁻¹=d"),
        ],
    ),
    "polynomial_constraint_systems": (
        "algebra",
        "(R : Type) [CommRing R] (a b c d : R)",
        [
            ("(h : a=b+c) (k : d=b-c)", "a*d=b^2-c^2"),
            ("(h : c=a+b) (k : d=a-b)", "c^2-d^2=4*a*b"),
            ("(h : a*b=c) (k : b*d=a)", "a*b*d=a^2"),
            ("(h : c=a+b)", "(c-a)^3=b^3 ∧ c^2-a^2=b*(2*a+b)"),
        ],
    ),
    "lattice_mixed_intervals": (
        "order",
        "(α : Type) [Lattice α] (a b c d e : α)",
        [
            ("(h : a ≤ b) (k : b ≤ c) (l : c ≤ d)", "a ⊔ b ≤ d ⊓ (c ⊔ e)"),
            ("(h : a ≤ c) (k : b ≤ d)", "(a ⊓ b) ⊔ (a ⊓ b ⊓ e) ≤ c ⊓ d"),
            ("(h : a ≤ b) (k : b ≤ a) (l : c ≤ d)", "a ⊔ c ≤ b ⊔ d"),
            ("(h : a ≤ b) (k : c ≤ d) (l : b ≤ e) (m : d ≤ e)", "a ⊔ c ≤ e"),
        ],
    ),
    "image_preimage_composition": (
        "sets",
        "(α β γ : Type) (f : α → β) (g : β → γ) (A : Set α) (B : Set β) (C : Set γ)",
        [
            ("", "g '' (f '' A) = (g ∘ f) '' A"),
            ("", "f ⁻¹' (g ⁻¹' C) = (g ∘ f) ⁻¹' C"),
            ("(h : f '' A ⊆ B) (k : g '' B ⊆ C)", "(g ∘ f) '' A ⊆ C"),
            ("", "f '' (A ∩ f ⁻¹' B) ⊆ B ∩ f '' A"),
        ],
    ),
    "set_nested_partition": (
        "sets",
        "(α : Type) (A B C D : Set α)",
        [
            ("", "((A ∪ B) \\ C) ∩ D = ((A ∩ D) \\ C) ∪ ((B ∩ D) \\ C)"),
            ("", "(A \\ (B \\ C)) ∩ B = A ∩ B ∩ C"),
            ("(h : A ⊆ B ∪ C) (k : A ∩ B = ∅)", "A ⊆ C"),
            ("", "(A ∩ (B ∪ C)) \\ D = (A ∩ (B \\ D)) ∪ (A ∩ (C \\ D))"),
        ],
    ),
    "quantified_case_witness": (
        "logic",
        "(α : Type) (P Q R S : α → Prop)",
        [
            (
                "(h : ∃ x, (P x ∧ Q x) ∨ R x) (k : ∀ x, P x → Q x → S x) (l : ∀ x, R x → S x)",
                "∃ x, S x ∧ (Q x ∨ R x)",
            ),
            (
                "(h : ∀ x, P x → Q x ∨ R x) (k : ∀ x, Q x → S x) (l : ∀ x, R x → S x)",
                "∀ x, P x → S x",
            ),
            ("(h : ∃ x, P x ∧ (Q x → R x)) (k : ∀ x, P x → Q x)", "∃ x, R x ∧ P x"),
            (
                "(h : ∀ x, P x ∨ Q x) (k : ∀ x, P x → R x) (l : ∀ x, Q x → S x)",
                "∀ x, (R x ∨ S x) ∧ (Q x ∨ P x)",
            ),
        ],
    ),
    "dependent_function_graphs": (
        "logic",
        "(α : Type) (β : α → Type) (f : ∀ x, β x → β x) (g : ∀ x, β x) (a : α)",
        [
            (
                "(P : ∀ x, β x → Prop) (h : ∀ x, P x (f x (g x)))",
                "∃ z : β a, P a z ∧ z = f a (g a)",
            ),
            ("(P Q : β a → Prop) (h : P (g a)) (k : ∀ z, P z → Q (f a z))", "∃ z, Q z"),
            ("(P : β a → Prop) (h : ∀ z, P (f a z))", "∃ z : β a × β a, P z.1 ∧ P z.2"),
            ("(h : ∀ x, f x (g x) = g x)", "∃ z : β a, f a z = z ∧ z = g a"),
        ],
    ),
    "relation_diamond_context": (
        "order",
        "(α : Type) (R : α → α → Prop) (a b c d e : α)",
        [
            (
                "(h : R a b) (k : R b c) (l : R c d) (m : R d e) (t : ∀ x y z, R x y → R y z → R x z)",
                "R a e ∧ R b d",
            ),
            (
                "(h : R a b) (k : R a c) (s : ∀ x y, R x y → R y x) (t : ∀ x y z, R x y → R y z → R x z)",
                "∃ x, R b x ∧ R x c",
            ),
            (
                "(h : R a b) (k : R b c) (s : ∀ x y, R x y → R y x) (t : ∀ x y z, R x y → R y z → R x z)",
                "R c a ∧ R b b",
            ),
            (
                "(h : R a b ∨ R a c) (k : R b d) (l : R c d) (t : ∀ x y z, R x y → R y z → R x z)",
                "R a d",
            ),
        ],
    ),
    "inverse_contextual_chain": (
        "logic",
        "(α β γ : Type) (f : α → β) (g : β → α) (k : β → γ) (l : γ → β)",
        [
            (
                "(h : Function.LeftInverse g f) (q : Function.LeftInverse l k) (a b : α) (r : k (f a)=k (f b))",
                "a=b",
            ),
            (
                "(h : Function.RightInverse g f) (q : Function.RightInverse l k) (c : γ)",
                "∃ a, k (f a)=c",
            ),
            ("(h : Function.LeftInverse g f) (a : α)", "∃ b, g b=a ∧ f (g b)=b"),
            (
                "(h : Function.RightInverse g f) (q : Function.LeftInverse l k) (b : β)",
                "l (k (f (g b)))=b",
            ),
        ],
    ),
}


def write():
    D.mkdir(parents=True, exist_ok=True)
    if (D / "frozen.json").exists():
        raise ValueError("Frozen curriculum may not be regenerated")
    registry = {}
    for name, spec in [("development", CURRICULUM), ("evaluation", TEST)]:
        tasks = []
        for fam, (domain, base, rows) in spec.items():
            for i, (extra, target) in enumerate(rows):
                ident = f"p6_{'dev' if name == 'development' else 'test'}_{fam}_{i + 1:02}"
                registry[ident] = fam
                tasks.append(
                    dict(
                        id=ident,
                        title=f"{fam.replace('_', ' ')} {i + 1}",
                        domain=domain,
                        difficulty="challenge",
                        split="development" if name == "development" else "held_out",
                        binders=base + " " + extra,
                        target=target,
                        display=target,
                        description=f"Original Phase 6 {name} statement in {fam}; retained independently of solver outcomes.",
                    )
                )
        (D / f"{name}.json").write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n")
    (D / "families.json").write_text(json.dumps(registry, indent=2) + "\n")
    print(
        "Statements",
        sum(len(s[2]) for s in CURRICULUM.values()),
        sum(len(s[2]) for s in TEST.values()),
    )


if __name__ == "__main__":
    write()
