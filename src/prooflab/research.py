"""Inspect/export actual continuation evidence with model annotations only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prooflab.continuations import DATA
from prooflab.dataset import get_task
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Candidate, ProofState
from prooflab.outcome import OutcomeRanking
from prooflab.phase3_data import digest

DIAGNOSTICS = DATA.parent / "diagnostics-v1"


def sources() -> dict[tuple[str, str], Path]:
    return {
        (role, p.stem): p
        for role, directory in [("development", DATA / "tasks"), ("diagnostic", DIAGNOSTICS)]
        for p in sorted(directory.glob("*.json"))
        if p.name != "manifest.json"
    }


def manifest() -> list[dict[str, Any]]:
    result = []
    for (role, ident), path in sources().items():
        record = json.loads(path.read_text())
        for row in record["states"]:
            explored = [o for o in row["observations"] if o["continuation"]]
            if not explored:
                continue
            verified = [o for o in explored if o["continuation"]["verification"]["verified"]]
            costs = [o["continuation"]["metrics"]["attempted_candidates"] for o in verified]
            result.append(
                {
                    "key": f"{role}:{ident}:{row['depth']}",
                    "role": role,
                    "task_id": ident,
                    "title": get_task(ident).title,
                    "depth": row["depth"],
                    "prefix": row["prefix"],
                    "valid": sum(o["status"] == "accepted" for o in row["observations"]),
                    "explored": len(explored),
                    "verified": len(verified),
                    "cost_range": [min(costs), max(costs)] if costs else None,
                    "url": f"phase3/data/continuations/{role}--{ident}.json",
                    "source_sha256": digest(path),
                    "case": record.get("case"),
                }
            )
    return result


def bundle(role: str, ident: str) -> dict[str, Any]:
    path = sources().get((role, ident))
    if path is None:
        raise KeyError("Unknown finite continuation record")
    record = json.loads(path.read_text())
    phase2, outcome = LearnedRanking(), OutcomeRanking()
    annotations = {}
    for row in record["states"]:
        state = ProofState.model_validate(row["state"])
        candidates = [Candidate.model_validate(o["candidate"]) for o in row["observations"]]
        p2 = phase2.rank_candidates(state, candidates)
        p3 = outcome.rank_candidates(state, candidates)
        annotations[str(row["depth"])] = [
            {
                "tactic": c.tactic,
                "phase2_rank": p2.index(c) + 1,
                "outcome_rank": p3.index(c) + 1,
                "phase2_score": phase2.score(state, c),
                "outcome_score": outcome.score(state, c),
                "phase2_contributions": phase2.contributions(state, c),
                "outcome_contributions": outcome.contributions(state, c),
            }
            for c in candidates
        ]
    return {
        "record": record,
        "annotations": annotations,
        "role": role,
        "source_sha256": digest(path),
        "source_path": str(path.relative_to(ROOT)),
        "phase2_model_sha256": phase2.model_hash,
        "outcome_model_sha256": outcome.model_hash,
        "note": (
            "Scores use recorded pre-action states only; "
            "actual successors are analysis data, not model inputs"
        ),
    }
