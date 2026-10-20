"""Statement-only Phase 3 curriculum pilot and independent final families.

Run once before freeze. Never filter final tasks using model outcomes.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PILOT = [
    (
        "pilot_fork",
        "logic",
        "(P Q R S T : Prop) (hp : P) (pq : P → Q) (qr : Q → R) (rs : R → S) (pt"
        " : P → T) (ts : T → S)",
        "S",
    ),
    (
        "pilot_nested",
        "logic",
        "(P Q R : Prop) (hp : P) (h : P → Q) (g : Q → R)",
        "(P ∧ Q) ∧ (R ∧ P)",
    ),
    (
        "pilot_cycle",
        "order",
        "(α : Type) [PartialOrder α] (a b c d : α) (ab : a ≤ b) (bc : b ≤ c) "
        "(cd : c ≤ d) (ba : b ≤ a)",
        "a ≤ d",
    ),
    (
        "pilot_two_sides",
        "order",
        "(α : Type) [PartialOrder α] (a b c : α) (ab : a ≤ b) (bc : b ≤ c) (ca : c ≤ a)",
        "a = c",
    ),
    (
        "pilot_rewrite",
        "algebra",
        "(M : Type) [Monoid M] (a b c : M) (h : a = b) (k : b = c)",
        "(a * 1) * 1 = c",
    ),
    (
        "pilot_ring",
        "algebra",
        "(K : Type) [CommRing K] (x y z : K) (h : x = y)",
        "(x + z)^2 = y^2 + 2*y*z + z^2",
    ),
    (
        "pilot_set_chain",
        "sets",
        "(α : Type) (A B C D : Set α) (ab : A ⊆ B) (bc : B ⊆ C) (cd : C ⊆ D)",
        "A ∩ B ⊆ D",
    ),
    (
        "pilot_set_join",
        "sets",
        "(α : Type) (A B C : Set α) (ab : A ⊆ B) (ac : A ⊆ C)",
        "A ⊆ (B ∩ C) ∪ A",
    ),
]

FAMILIES = {
    "disjunctive_routes": (
        "logic",
        [
            (
                "or_chain",
                "(P Q R S T : Prop) (hp : P) (pq : P → Q) (qr : Q → R) (rs : R → S) (pt : P → T)",
                "S ∨ T",
            ),
            (
                "or_dead_branch",
                "(P Q R S T : Prop) (hp : P) (pq : P → Q) (qr : Q → R) (rt : R → T)",
                "S ∨ T",
            ),
            (
                "or_pair_routes",
                "(P Q R S : Prop) (hp : P) (pq : P → Q) (qr : Q → R) (ps : P → S)",
                "(Q ∧ R) ∨ (P ∧ S)",
            ),
            (
                "or_both_long",
                "(P Q R S T U : Prop) (hp : P) (pq : P → Q) (qr : Q → R) (rs : R → S) "
                "(pt : P → T) (tu : T → U)",
                "(R ∧ S) ∨ U",
            ),
        ],
    ),
    "higher_order_routes": (
        "logic",
        [
            ("higher_pair", "(P Q R S : Prop) (hp : P) (hq : Q) (f : P ∧ Q → R) (g : R → S)", "S"),
            (
                "higher_cycle",
                "(P Q R S : Prop) (hp : P) (f : P → Q) (g : Q → P) (k : Q ∧ P → R) (r : R → S)",
                "S ∧ Q",
            ),
            ("higher_discharge", "(P Q R S : Prop) (f : (P → Q) → R) (g : R → S) (hq : Q)", "S"),
            (
                "higher_nested",
                "(P Q R S T : Prop) (hp : P) (hq : Q) (f : P ∧ Q → R) (g : R ∧ Q → S) (h : S → T)",
                "T",
            ),
        ],
    ),
    "relational_diamonds": (
        "order",
        [
            (
                "relation_shortcut",
                "(α : Type) (R : α → α → Prop) (a b c d : α) (ab : R a b) (bc : R b c) "
                "(cd : R c d) (ac : R a c) (tr : ∀ x y z, R x y → R y z → R x z)",
                "R a d",
            ),
            (
                "relation_fork",
                "(α : Type) (R : α → α → Prop) (a b c d e : α) (ab : R a b) (bc : R b "
                "c) (ce : R c e) (ad : R a d) (de : R d e) (tr : ∀ x y z, R x y → R y z"
                " → R x z)",
                "R a e",
            ),
            (
                "relation_reverse",
                "(α : Type) (R : α → α → Prop) (a b c : α) (ab : R a b) (bc : R b c) "
                "(sym : ∀ x y, R x y → R y x) (tr : ∀ x y z, R x y → R y z → R x z)",
                "R c a",
            ),
            (
                "relation_pair",
                "(α : Type) (R : α → α → Prop) (a b c d : α) (ab : R a b) (bc : R b c) "
                "(cd : R c d) (tr : ∀ x y z, R x y → R y z → R x z)",
                "R a c ∧ R a d",
            ),
        ],
    ),
    "ordered_route_products": (
        "order",
        [
            (
                "order_square",
                "(α : Type) [PartialOrder α] (a b c d : α) (ab : a ≤ b) (bc : b ≤ c) "
                "(cd : c ≤ d) (da : d ≤ a)",
                "a = d ∧ b = c",
            ),
            (
                "order_guard",
                "(α : Type) [PartialOrder α] (a b c d e : α) (ab : a ≤ b) (bc : b < c) "
                "(cd : c ≤ d) (de : d ≤ e)",
                "a < e",
            ),
            (
                "order_routes",
                "(α : Type) [PartialOrder α] (a b c d e : α) (ab : a ≤ b) (bc : b ≤ c) "
                "(cd : c ≤ d) (ae : a ≤ e) (ed : e ≤ d)",
                "a ≤ d ∧ a ≤ c",
            ),
            (
                "order_cycle_product",
                "(α : Type) [PartialOrder α] (a b c d : α) (ab : a ≤ b) (bc : b ≤ c) "
                "(ca : c ≤ a) (cd : c ≤ d)",
                "a = b ∧ a ≤ d",
            ),
        ],
    ),
    "noncommutative_rewrite_routes": (
        "algebra",
        [
            (
                "monoid_chain",
                "(M : Type) [Monoid M] (a b c d : M) (h : a = b) (k : b = c)",
                "(a * d) * 1 = c * d",
            ),
            (
                "monoid_reverse",
                "(M : Type) [Monoid M] (a b c d : M) (h : b = a) (k : c = b)",
                "a * (d * 1) = c * d",
            ),
            (
                "monoid_three",
                "(M : Type) [Monoid M] (a b c d e : M) (h : a = b) (k : b = c) (l : c = d)",
                "(1 * a) * e = d * e",
            ),
            (
                "monoid_distractor",
                "(M : Type) [Monoid M] (a b c d : M) (h : a = b) (k : b = c) (decoy : d = a)",
                "(a * c) * 1 = b * c",
            ),
        ],
    ),
    "contextual_polynomial_routes": (
        "algebra",
        [
            (
                "ring_chain",
                "(K : Type) [CommRing K] (a b c x : K) (h : a = b) (k : b = c)",
                "(a+x)^2 = c^2 + 2*c*x + x^2",
            ),
            (
                "ring_reverse",
                "(K : Type) [CommRing K] (a b c x : K) (h : b = a) (k : c = b)",
                "(a-x)*(a+x) = c^2-x^2",
            ),
            (
                "ring_two_equalities",
                "(K : Type) [CommRing K] (a b x y : K) (h : a = b) (k : x = y)",
                "(a+x)^2 = b^2+2*b*y+y^2",
            ),
            (
                "ring_product_pair",
                "(K : Type) [CommRing K] (a b x : K) (h : a = b)",
                "((a+x)^2 = b^2+2*b*x+x^2) ∧ ((a-x)*(a+x) = b^2-x^2)",
            ),
        ],
    ),
    "nested_set_routes": (
        "sets",
        [
            (
                "set_nested_left",
                "(α : Type) (A B C D : Set α) (ab : A ⊆ B) (bc : B ⊆ C)",
                "(A ∩ D) ∩ B ⊆ C ∩ D",
            ),
            (
                "set_choice",
                "(α : Type) (A B C D : Set α) (ab : A ⊆ B) (bc : B ⊆ C) (ad : A ⊆ D)",
                "A ⊆ (C ∩ D) ∪ B",
            ),
            (
                "set_join_elimination",
                "(α : Type) (A B C D : Set α) (ac : A ⊆ C) (bc : B ⊆ C) (cd : C ⊆ D)",
                "A ∪ B ⊆ D",
            ),
            (
                "set_join_product",
                "(α : Type) (A B C D : Set α) (ac : A ⊆ C) (bc : B ⊆ C) (ad : A ⊆ D) (bd : B ⊆ D)",
                "A ∪ B ⊆ C ∩ D",
            ),
        ],
    ),
    "set_exclusion_routes": (
        "sets",
        [
            (
                "set_diff_chain",
                "(α : Type) (A B C D : Set α) (ab : A ⊆ B) (bc : B ⊆ C)",
                "A \\ D ⊆ C \\ D",
            ),
            ("set_complement_product", "(α : Type) (A B C : Set α)", "A ∩ Bᶜ ∩ Cᶜ ⊆ A \\ (B ∪ C)"),
            (
                "set_diff_nested",
                "(α : Type) (A B C D : Set α) (ab : A ⊆ B)",
                "(A \\ C) ∩ D ⊆ (B ∩ D) \\ C",
            ),
            (
                "set_excluded_join",
                "(α : Type) (A B C D : Set α) (ad : A ⊆ D) (bd : B ⊆ D)",
                "(A \\ C) ∪ (B \\ C) ⊆ D \\ C",
            ),
        ],
    ),
}


def task(ident, family, domain, binders, target, split):
    return {
        "id": "p3_" + ident,
        "title": ident.replace("_", " ").capitalize(),
        "domain": domain,
        "difficulty": "challenge",
        "split": split,
        "binders": binders,
        "target": target,
        "display": target,
        "description": f"Phase 3 · {family.replace('_', ' ')}",
        "origin": "Original Phase 3 statement; no mathematical novelty claimed.",
        "forbidden_lemmas": ["prooflab_result"],
    }


def main():
    directory = ROOT / "benchmarks/phase3"
    directory.mkdir(parents=True, exist_ok=True)
    pilot = [
        task(i, "development difficulty pilot", d, b, t, "development") for i, d, b, t in PILOT
    ]
    evaluation = [
        task(i, family, domain, b, t, "held_out")
        for family, (domain, rows) in FAMILIES.items()
        for i, b, t in rows
    ]
    for name, rows in [("pilot", pilot), ("evaluation", evaluation)]:
        (directory / f"{name}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
        )
    (directory / "families.json").write_text(
        json.dumps(
            {"p3_" + i: f for f, (_, rows) in FAMILIES.items() for i, _, _ in rows}, indent=2
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
