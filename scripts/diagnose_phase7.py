"""Historical Phase 6 execution evidence for Phase 7 design, never training labels."""

from __future__ import annotations

from prooflab.lean import ROOT
from prooflab.phase3_data import digest
from prooflab.phase7_data import save
from prooflab.research_io import read_json


def main() -> None:
    base = ROOT / "experiments/phase6/evaluation-v1/traces"
    cases = []
    counts = {"learned": 0, "staged": 0}
    for task in read_json(ROOT / "benchmarks/phase6/evaluation.json"):
        ident = task["id"]
        left_path = base / f"{ident}--learned--r0.json.gz"
        right_path = base / f"{ident}--staged--r0.json.gz"
        learned, staged = read_json(left_path), read_json(right_path)
        for name, t in [("learned", learned), ("staged", staged)]:
            counts[name] += int(t["verification"]["verified"])
        if learned["status"] == "verified" and staged["status"] == "verified":
            continue
        q = learned["retrievals"][0] if learned["retrievals"] else {}
        cases.append(
            dict(
                task_id=ident,
                learned_status=learned["status"],
                staged_status=staged["status"],
                learned_termination=learned["termination"],
                staged_termination=staged["termination"],
                learned_attempts=learned["metrics"]["attempted_candidates"],
                staged_attempts=staged["metrics"]["attempted_candidates"],
                root_decision=q.get("decision"),
                predicted_conditional_log_cost=q.get("predicted_log_costs"),
                independently_verified_staged_proof=staged["proof"]
                if staged["verification"]["verified"]
                else [],
                sources={str(p.relative_to(ROOT)): digest(p) for p in [left_path, right_path]},
            )
        )
    save(
        ROOT / "research/phase7/phase6-diagnosis.json",
        dict(
            diagnosis_only=True,
            training_labels=False,
            source_commit="a8af9eb8698819d07bb10f7f1bacd855f9b1213a",
            repeat=0,
            counts=counts,
            cases=cases,
            mechanisms=[
                "Conditional costs ignore observed bounded failures.",
                "Small cost differences can suppress an available witness expert.",
                "A retained branch can starve under a fixed expansion budget.",
                "Root-only supervision shifts at intermediate states and budgets.",
            ],
            limitation="Matched observed runs diagnose mechanisms; they do not label "
            "unsearched mathematical alternatives.",
        ),
    )
    print(counts)


if __name__ == "__main__":
    main()
