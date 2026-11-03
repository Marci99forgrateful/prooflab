"""Create and audit Phase 7 statements before any model selection or test search."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from prooflab.lean import ROOT
from prooflab.models import Task
from prooflab.phase3_data import digest
from prooflab.phase6_data import check_freeze
from prooflab.splits import equivalent, graph_hash, native_structures

D = ROOT / "benchmarks/phase7"


def write(path: Path, value: Any) -> None:
    if path.exists():
        raise ValueError("Refusing to overwrite frozen research input: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    check_freeze()
    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    families: dict[str, str] = {}

    def add(role: str, family: str, domain: str, binders: str, target: str, index: int) -> None:
        ident = f"p7_{role}_{family}_{index:02}"
        row = dict(
            id=ident,
            title=family.replace("_", " ") + f" {index}",
            domain=domain,
            difficulty="challenge",
            split="held_out" if role == "test" else "development",
            binders=binders,
            target=target,
            display=target,
            description=(
                f"Phase 7 {role} statement in {family}; fixed independently of solver outcomes."
            ),
        )
        (test if role == "test" else dev).append(row)
        families[ident] = family

    old = json.loads((ROOT / "benchmarks/phase6/development.json").read_text())
    oldfamilies = json.loads((ROOT / "benchmarks/phase6/families.json").read_text())
    available = sorted({oldfamilies[t["id"]] for t in old})
    selected = ["continuation_logic", "lattice_maps"] + [
        f
        for f in available
        if f not in ("continuation_logic", "lattice_maps", "set_difference", "product_graphs")
    ][:6]
    reused = {}
    for family in selected:
        for i, t in enumerate([t for t in old if oldfamilies[t["id"]] == family][:4], 1):
            add("dev", "previous_" + family, t["domain"], t["binders"], t["target"], i)
            reused[dev[-1]["id"]] = t["id"]
    group = "(G : Type) [Group G] (a b c d : G)"
    ring = "(R : Type) [CommRing R] (x y z : R)"
    lattice = "(α : Type) [Lattice α] (a b c d : α)"
    sets = "(α : Type) (A B C D : Set α)"
    for i in range(1, 5):
        n = i + 2
        chain = "x"
        for _ in range(i):
            chain = f"f ({chain})"
        add(
            "dev",
            "iterated_predicates",
            "logic",
            "(α : Type) (f : α → α) (P : α → Prop) (x : α) (h : ∀ t, P (f t))",
            f"∃ y, P y ∧ y = {chain}",
            i,
        )
        add(
            "dev",
            "power_cancellation",
            "algebra",
            group,
            f"(a ^ {n} * b) * (b⁻¹ * (a ^ {n})⁻¹) = 1",
            i,
        )
        add(
            "dev",
            "polynomial_distribution",
            "algebra",
            ring,
            f"(x+y)^{n} * (z+1) = (x+y)^{n} * z + (x+y)^{n}",
            i,
        )
        terms = ["a ⊓ (b ⊔ c)", "(a ⊓ b) ⊔ (a ⊓ c)", "a ⊔ (b ⊓ c)", "(a ⊔ b) ⊓ (a ⊔ c)"]
        add(
            "dev",
            "lattice_assumption_pairs",
            "order",
            lattice + f" (h : {terms[i - 1]} ≤ d)",
            f"{terms[i - 1]} ≤ d ∧ {terms[i - 1]} ⊓ a ≤ d",
            i,
        )
        stmts = [
            "A ∩ (B ∪ C) ⊆ (A ∩ B) ∪ (A ∩ C)",
            "A \\ (B ∪ C) ⊆ (A \\ B) ∩ (A \\ C)",
            "(A ∪ B) \\ C ⊆ (A \\ C) ∪ (B \\ C)",
            "(A \\ B) ∩ C ⊆ (A ∩ C) \\ B",
        ]
        add("dev", "set_transport_rules", "sets", sets, stmts[i - 1], i)
        ps = ["P ∧ Q", "Q ∧ P", "P ∧ (P ∧ Q)", "(Q ∧ P) ∧ Q"]
        add(
            "dev",
            "conjunctive_continuations",
            "logic",
            "(P Q : Prop) (hp : P) (hq : Q)",
            f"({ps[i - 1]}) ∧ (P ∨ Q)",
            i,
        )
        add(
            "dev",
            "dependent_output",
            "logic",
            "(α β : Type) (f : α → β) (P : β → Prop) (a : α) (h : ∀ x, P (f x))",
            f"∃ y, P y ∧ {' ∧ '.join(['y = f a'] * i)}",
            i,
        )
        add(
            "dev",
            "guarded_cases",
            "logic",
            "(P Q R S : Prop) (h : P ∨ Q) (f : P → R) (g : Q → R) (s : S)",
            f"R ∧ {' ∧ '.join(['S'] * i)}",
            i,
        )
    for i in range(1, 5):
        n = i + 3
        exprs = ["(a*b)*(c*d)", "a*(b*(c*d))", "(a*b*c)*d", "a*b*(c*d*a)"]
        e = exprs[i - 1]
        add(
            "test",
            "inverse_product_context",
            "algebra",
            group + f" (h : {e} = 1)",
            f"({e})⁻¹ * a = a",
            i,
        )
        add(
            "test",
            "high_degree_factorization",
            "algebra",
            ring,
            f"(x+y)^{n + 1} - (x+y)^{n} * x = y * (x+y)^{n}",
            i,
        )
        rels = ["a ⊓ b ≤ c", "a ≤ b ⊔ c", "a ⊔ b ≤ c ⊓ d", "a ⊓ b ≤ c ⊔ d"]
        r = rels[i - 1]
        add(
            "test",
            "lattice_guard_export",
            "order",
            lattice + f" (h : {r})",
            f"({r}) ∧ (a ⊓ b ≤ a ⊔ c)",
            i,
        )
        exps = ["A ∩ (B \\ C)", "(A \\ B) ∪ C", "(A ∪ B) ∩ (C ∪ D)", "A \\ (B ∩ C)"]
        ex = exps[i - 1]
        add(
            "test",
            "preimage_boolean_transport",
            "sets",
            "(α β : Type) (f : α → β) (A B C D : Set β)",
            f"f ⁻¹' ({ex}) ⊆ f ⁻¹' (A ∪ B ∪ C ∪ D)",
            i,
        )
        inners = ["(A ∩ B) ∪ (C ∩ D)", "(A \\ B) ∩ C", "(A ∪ B) \\ (C ∪ D)", "(A ∩ C) \\ (B ∩ D)"]
        add(
            "test",
            "image_preimage_roundtrip",
            "sets",
            "(α β : Type) (f : α → β) (A B C D : Set α)",
            f"{inners[i - 1]} ⊆ f ⁻¹' (f '' ({inners[i - 1]}))",
            i,
        )
        cs = ["Q ∧ R", "R ∧ Q", "Q ∧ (R ∧ Q)", "(Q ∧ R) ∧ (R ∧ Q)"]
        add(
            "test",
            "disjunctive_branch_completion",
            "logic",
            "(P Q R S : Prop) (h : P ∨ S) (f : P → Q) (g : S → Q) (r : R)",
            f"({cs[i - 1]}) ∧ (P ∨ S)",
            i,
        )
        nests = ["Q y ∧ P x", "P x ∧ (Q y ∧ P x)", "(Q y ∧ P x) ∧ Q y", "Q y ∧ (P x ∧ Q y)"]
        add(
            "test",
            "quantified_witness_pair",
            "logic",
            "(α β : Type) (P : α → Prop) (Q : β → Prop) (h : ∃ x, P x) (f : ∀ x, P x → ∃ y, Q y)",
            f"∃ x y, {nests[i - 1]}",
            i,
        )
        chain = "f a"
        for _ in range(i):
            chain = f"g ({chain})"
        add(
            "test",
            "composed_output_certificate",
            "logic",
            "(α β : Type) (f : α → β) (g : β → β) (P Q : β → Prop) (a : α) (h : ∀ y, "
            "P (g y) ∧ Q (g y))",
            f"∃ z, P z ∧ Q z ∧ z = {chain}",
            i,
        )
        w = ["(f a, g a)", "(f a, g (f a))", "(g (f a), f a)", "(f (g a), g (f a))"][i - 1]
        add(
            "test",
            "typed_pair_certificate",
            "logic",
            "(α : Type) (f g : α → α) (a : α) (R : α × α → Prop)" + f" (h : R {w})",
            f"∃ z : α × α, R z ∧ z = {w}",
            i,
        )
        add(
            "test",
            "monoid_context_transport",
            "algebra",
            "(M : Type) [Monoid M] (a b c d : M)" + f" (h : a * b = c ^ {n})",
            f"a * (b * d) = c ^ {n} * d",
            i,
        )
        shapes = ["(A ∩ B) ∪ C", "A ∩ (B ∪ C)", "(A \\ B) ∪ (B \\ A)", "(A ∩ B) \\ C"]
        add(
            "test",
            "set_conjunction_witness",
            "sets",
            sets + f" (x : α) (h : x ∈ {shapes[i - 1]})",
            f"∃ y, y ∈ {shapes[i - 1]} ∧ y ∈ A ∪ B ∪ C",
            i,
        )
        goals = [
            "Q (f a) ∧ P a",
            "P a ∧ (Q (f a) ∧ P a)",
            "(Q (f a) ∧ P a) ∧ Q (f a)",
            "Q (f a) ∧ (Q (f a) ∧ P a)",
        ]
        add(
            "test",
            "guarded_function_application",
            "logic",
            "(α β : Type) (f : α → β) (P : α → Prop) (Q : β → Prop) (a : α) (h : P "
            "a) (k : ∀ x, P x → Q (f x))",
            goals[i - 1],
            i,
        )
    assert len(dev) == 64 and len(test) == 48
    validation = [
        "previous_continuation_logic",
        "previous_lattice_maps",
        "guarded_cases",
        "dependent_output",
    ]
    protocol = dict(
        schema_version=1,
        base_commit="a8af9eb8698819d07bb10f7f1bacd855f9b1213a",
        primary="conservative minus phase6_staged",
        workers=2,
        seed=707,
        evaluation_budget=dict(
            max_depth=12,
            max_expansions=80,
            max_candidates=24,
            max_attempts=600,
            timeout_s=18,
            tactic_timeout_s=2,
        ),
        collection_budgets=[
            dict(
                max_depth=10,
                max_expansions=28,
                max_candidates=24,
                max_attempts=160,
                timeout_s=8,
                tactic_timeout_s=2,
            ),
            dict(
                max_depth=12,
                max_expansions=80,
                max_candidates=24,
                max_attempts=600,
                timeout_s=18,
                tactic_timeout_s=2,
            ),
        ],
        source_budget=dict(
            max_depth=10,
            max_expansions=28,
            max_candidates=24,
            max_attempts=160,
            timeout_s=8,
            tactic_timeout_s=2,
        ),
        states_per_task=2,
        source_state_rule=(
            "Root plus first nonterminal nonroot expanded state; if unavailable, "
            "first accepted nonterminal successor. No success-conditioned source "
            "selection."
        ),
        strategies=["symbolic", "hybrid", "typed"],
        validation_families=validation,
        architectures=["linear", "boosted"],
        tree_depth=2,
        tree_iterations=48,
        conservative_margins=[0.1, 0.2, 0.3],
        selection=(
            "Equal-family validation Brier score for completion, successful "
            "conditional log-attempt MSE for cost; ties favor linear. "
            "Conservative margin maximizes matched validation completion, ties "
            "favor larger margin. No refit on validation."
        ),
        arms=[
            "phase4",
            "phase6_staged",
            "phase6_learned",
            "completion",
            "cost",
            "joint",
            "conservative",
            "root_trained",
            "staged",
            "automation",
            "grind",
        ],
        labels=(
            "1 means independent verification within the stated budget; 0 is "
            "observed bounded noncompletion, never mathematical falsity. Errors, "
            "unavailable and unrun observations are missing, never zeros."
        ),
        joint_rule="p - .25*p*min(conditional_attempts/remaining_attempts,2)",
        automation=(
            "Separate opaque Aesop/grind reference, 2 seconds per call under the "
            "same outer 18-second cap; attempts are not primitive work."
        ),
        inference=(
            "Current native goals/context and remaining budgets only. No IDs, "
            "prefixes, future outcomes or answer scripts."
        ),
        uncertainty=(
            "10000 paired theorem bootstrap samples seed707; separate "
            "equal-family cluster sensitivity; all regressions retained; no "
            "final-result retuning."
        ),
        boundary=(
            "Historical evaluation is diagnosis only; old permitted development "
            "statements may be recollected. New evaluation families differ from "
            "development schemata, but share elementary proof primitives; not "
            "externally blinded."
        ),
    )
    for name, value in [
        ("development.json", dev),
        ("evaluation.json", test),
        ("families.json", families),
        ("protocol.json", protocol),
        ("development-reuse.json", reused),
    ]:
        write(D / name, value)
    audit(dev, test, reused)


def audit(dev: list[Any], test: list[Any], reused: dict[str, str]) -> None:
    trees = native_structures([Task.model_validate(t) for t in dev + test])
    previous = {}
    for p in (ROOT / "benchmarks").glob("phase[2-6]/frozen.json"):
        previous.update(json.loads(p.read_text()).get("expression_trees", {}))
    groups: dict[str, list[tuple[str, Any]]] = defaultdict(list)
    for ident, tree in previous.items():
        groups[graph_hash(tree)].append((ident, tree))
    duplicates = []
    for row in dev + test:
        ident = row["id"]
        tree = trees[ident]
        sha = graph_hash(tree)
        for other, old in groups[sha]:
            if equivalent(tree, old) and not (ident in reused and other == reused[ident]):
                # Recollection of permitted development is explicit; never reuse any test statement.
                if ident not in reused:
                    duplicates.append([ident, other])
        groups[sha].append((ident, tree))
    if duplicates:
        raise ValueError("Structural duplicates: " + repr(duplicates))
    write(
        D / "frozen.json",
        dict(
            schema_version=1,
            files={p.name: digest(p) for p in D.glob("*.json")},
            expression_trees=trees,
            duplicate_pairs=[],
            evaluation_accessed=False,
            prior_phase6_freeze_sha256=digest(ROOT / "models/phase6/frozen.json"),
        ),
    )
    print(
        "Frozen 64 development and 48 evaluation statements; every statement "
        "elaborated and passed typed-graph duplicate auditing."
    )


if __name__ == "__main__":
    main()
