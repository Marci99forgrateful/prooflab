"""Pre-model evaluation statements: new whole-theorem families, no answer hints."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = {
    "existential_elimination": [
        (
            "exists_project",
            "Project an existential witness",
            "(α : Type) (P Q : α → Prop) (h : ∃ x, P x ∧ Q x)",
            "∃ x, P x",
        ),
        (
            "exists_nested",
            "Nested witness projection",
            "(α : Type) (P Q R : α → Prop) (h : ∃ x, P x ∧ Q x ∧ R x)",
            "∃ x, R x",
        ),
        (
            "exists_transport",
            "Transport an existential property",
            "(α : Type) (P Q : α → Prop) (h : ∃ x, P x) (f : ∀ x, P x → Q x)",
            "∃ x, Q x",
        ),
        (
            "exists_swap",
            "Reassemble a witness property",
            "(α : Type) (P Q : α → Prop) (h : ∃ x, P x ∧ Q x)",
            "∃ x, Q x ∧ P x",
        ),
    ],
    "witness_construction": [
        (
            "witness_single",
            "Construct an existential witness",
            "(α : Type) (P : α → Prop) (a : α) (h : P a)",
            "∃ x, P x",
        ),
        (
            "witness_pair",
            "Construct a joint witness",
            "(α : Type) (P Q : α → Prop) (a : α) (hp : P a) (hq : Q a)",
            "∃ x, P x ∧ Q x",
        ),
        (
            "witness_binary",
            "Two dependent witnesses",
            "(α β : Type) (R : α → β → Prop) (a : α) (b : β) (h : R a b)",
            "∃ x, ∃ y, R x y",
        ),
        (
            "witness_augment",
            "Augment an existing witness",
            "(α : Type) (P Q : α → Prop) (h : ∃ x, P x) (hq : ∀ x, Q x)",
            "∃ x, P x ∧ Q x",
        ),
    ],
    "function_congruence": [
        (
            "congr_single",
            "Congruence of a function",
            "(α β : Type) (f : α → β) (a b : α) (h : a = b)",
            "f a = f b",
        ),
        (
            "congr_nested",
            "Congruence through composition",
            "(α β γ : Type) (f : α → β) (g : β → γ) (a b : α) (h : a = b)",
            "g (f a) = g (f b)",
        ),
        (
            "congr_function_argument",
            "Rewrite function and argument",
            "(α β : Type) (f g : α → β) (a b : α) (hf : f = g) (ha : a = b)",
            "f a = g b",
        ),
        (
            "congr_binary",
            "Congruence in two arguments",
            "(α β γ : Type) (f : α → β → γ) (a b : α) (x y : β) (ha : a = b) (hx : x = y)",
            "f a x = f b y",
        ),
    ],
    "predicate_transport": [
        (
            "predicate_argument",
            "Transport a predicate",
            "(α : Type) (P : α → Prop) (a b : α) (h : a = b) (ha : P a)",
            "P b",
        ),
        (
            "predicate_function",
            "Transport under function equality",
            "(α β : Type) (P : β → Prop) (f g : α → β) (x : α) (h : f = g) (hp : P (f x))",
            "P (g x)",
        ),
        (
            "predicate_binary",
            "Transport a binary relation",
            "(α β : Type) (R : α → β → Prop) (a b : α) (x y : β) "
            "(ha : a = b) (hx : x = y) (hr : R a x)",
            "R b y",
        ),
        (
            "predicate_negative",
            "Transport a negated predicate",
            "(α : Type) (P : α → Prop) (a b : α) (h : a = b) (hn : ¬ P a)",
            "¬ P b",
        ),
    ],
    "set_preimages": [
        (
            "preimage_member",
            "Read preimage membership",
            "(α β : Type) (f : α → β) (A : Set β) (x : α) (h : x ∈ f ⁻¹' A)",
            "f x ∈ A",
        ),
        (
            "preimage_inter_member",
            "Preimage intersection membership",
            "(α β : Type) (f : α → β) (A B : Set β) (x : α) (ha : x ∈ f ⁻¹' A) (hb : x ∈ f ⁻¹' B)",
            "x ∈ f ⁻¹' (A ∩ B)",
        ),
        (
            "preimage_inter_subset",
            "Preimage distributes into intersection",
            "(α β : Type) (f : α → β) (A B : Set β)",
            "f ⁻¹' (A ∩ B) ⊆ (f ⁻¹' A) ∩ (f ⁻¹' B)",
        ),
        (
            "preimage_monotone",
            "Monotonicity through preimages",
            "(α β : Type) (f : α → β) (A B : Set β) (h : A ⊆ B)",
            "f ⁻¹' A ⊆ f ⁻¹' B",
        ),
    ],
    "set_differences": [
        (
            "difference_member",
            "Project a set difference",
            "(α : Type) (A B : Set α) (x : α) (h : x ∈ A \\ B)",
            "x ∈ A",
        ),
        (
            "difference_exclusion",
            "Extract exclusion evidence",
            "(α : Type) (A B : Set α) (x : α) (h : x ∈ A \\ B)",
            "x ∉ B",
        ),
        (
            "difference_construct",
            "Construct difference membership",
            "(α : Type) (A B : Set α) (x : α) (ha : x ∈ A) (hn : x ∉ B)",
            "x ∈ A \\ B",
        ),
        (
            "difference_monotone",
            "Monotonicity of set difference",
            "(α : Type) (A B C : Set α) (h : A ⊆ B)",
            "A \\ C ⊆ B \\ C",
        ),
    ],
}


def main() -> None:
    tasks = []
    families = {}
    for family, rows in ROWS.items():
        for index, (ident, title, binders, target) in enumerate(rows):
            ident = "p2_" + ident
            families[ident] = family
            tasks.append(
                {
                    "id": ident,
                    "title": title,
                    "domain": "sets"
                    if family.startswith("set_")
                    else "algebra"
                    if family == "function_congruence"
                    else "logic",
                    "difficulty": "easy"
                    if index == 0
                    else "moderate"
                    if index < 3
                    else "challenge",
                    "split": "held_out",
                    "binders": binders,
                    "target": target,
                    "display": target,
                    "description": f"Phase 2 frozen evaluation · {family.replace('_', ' ')}.",
                    "origin": "Original Phase 2 statement. Family fixed before model selection.",
                    "forbidden_lemmas": ["prooflab_result"],
                }
            )
    directory = ROOT / "benchmarks/phase2"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "evaluation.json").write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False) + "\n"
    )
    protocol = {
        "version": 1,
        "phase1_source": "experiments/phase1-v3",
        "evaluation_tasks": 24,
        "evaluation_families": families,
        "training_permission": "Phase 1 split=development only",
        "selection_train": "development tasks outside order domain",
        "selection_validation": "development tasks in order domain (never evaluation tasks)",
        "final_refit": "all permitted Phase 1 development tasks",
        "model": "pairwise logistic linear ranker; pure Python CPU",
        "hyperparameters": {
            "l2": [0.001, 0.01, 0.1],
            "epochs": 200,
            "learning_rate": 0.15,
            "seed": 0,
        },
        "selection_metric": "mean validation pairwise logistic loss",
        "labels": "verified-path action preferred to an actually Lean-rejected sibling; "
        "valid or unexecuted alternatives unlabeled",
        "frontier": "same handcrafted state-priority function for learned and best_first; "
        "learned changes candidate ordering only",
        "algorithms": ["bfs", "best_first", "learned", "automation"],
        "repetitions": 3,
        "workers": 2,
        "budget": {
            "max_depth": 8,
            "max_expansions": 60,
            "max_candidates": 24,
            "max_attempts": 400,
            "timeout_s": 12,
            "tactic_timeout_s": 3,
        },
        "uncertainty": {
            "bootstrap_samples": 10000,
            "seed": 1729,
            "unit": "theorem cluster, all repetitions kept together",
            "interval": 0.95,
        },
        "constraints": "Candidate generator and Lean verifier remain unchanged; "
        "evaluation run only after frozen model selection. No model retuning after test outcomes.",
    }
    (directory / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")


if __name__ == "__main__":
    main()
