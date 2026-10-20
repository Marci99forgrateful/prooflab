"""Post-evaluation diagnostics only: never consumed by model training/selection."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from prooflab.candidates import generate_candidates
from prooflab.continuations import rollout
from prooflab.lean import ROOT, LeanSession, verify
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, Candidate, ProofState, Trace
from prooflab.outcome import MODELS, OutcomeRanking
from prooflab.phase3_data import DIRECTORY, digest
from prooflab.research import DIAGNOSTICS
from prooflab.research_io import raw_bytes, read_json, trace_paths

EXPERIMENT = ROOT / "experiments/phase3/evaluation-v1"


def diagnostic(trace: Trace, source: Path, case: dict[str, Any]) -> dict[str, Any]:
    start = time.monotonic()
    task = trace.task
    if task.split != "held_out" or trace.status != "verified":
        raise ValueError("Diagnostics require a genuine held-out verified source trace")
    before = digest(MODELS / "frozen.json")
    audit = verify(task, trace.proof, timeout=20)
    if not audit.verified:
        raise ValueError("Diagnostic source failed fresh audit")
    phase2, outcome = LearnedRanking(), OutcomeRanking()
    config = json.loads((DIRECTORY / "protocol.json").read_text())["collection"]
    chosen: dict[str, Any] | None = None
    fallback: dict[str, Any] | None = None
    probed = 0
    with LeanSession(task, timeout=30) as lean:
        state = lean.initial
        prefix: list[str] = []
        for depth, positive in enumerate(trace.proof):
            observations = []
            positive_state = None
            for candidate in generate_candidates(state, 24, frozenset(task.forbidden_lemmas)):
                tick = time.monotonic()
                message = lean.step(state.state_id, candidate.tactic, 3)
                if message["status"] not in ("accepted", "invalid_candidate"):
                    raise ValueError("Incomplete diagnostic probe")
                successor = (
                    ProofState(state_id=message["state_id"], goals=message["goals"])
                    if message["status"] == "accepted"
                    else None
                )
                observations.append(
                    {
                        "candidate": candidate.model_dump(),
                        "status": message["status"],
                        "successor": successor.model_dump() if successor else None,
                        "elapsed_s": time.monotonic() - tick,
                        "error": message.get("error"),
                        "continuation": None,
                        "exploration": "not_selected",
                    }
                )
                if candidate.tactic == positive:
                    positive_state = successor
            probed += 1
            if positive_state is None:
                raise ValueError("Original held-out prefix did not replay")
            row: dict[str, Any] = {
                "task_id": task.id,
                "split": task.split,
                "domain": task.domain,
                "depth": depth,
                "prefix": list(prefix),
                "positive_tactic": positive,
                "state": state.model_dump(),
                "observations": observations,
            }
            valid = [
                Candidate.model_validate(o["candidate"])
                for o in observations
                if o["status"] == "accepted"
            ]
            if len(valid) >= 2:
                fallback = fallback or row
                if (
                    phase2.rank_candidates(state, valid)[0]
                    != outcome.rank_candidates(state, valid)[0]
                ):
                    chosen = row
                    break
            prefix.append(positive)
            state = positive_state
        chosen = chosen or fallback
        if chosen is None:
            raise ValueError("No multiple-valid state; report cannot fabricate alternatives")
        valid_observations = [o for o in chosen["observations"] if o["status"] == "accepted"]
        selected = valid_observations[: config["max_continuations_per_state"]]
        positive_observation = next(
            o for o in valid_observations if o["candidate"]["tactic"] == chosen["positive_tactic"]
        )
        if positive_observation not in selected:
            selected[-1] = positive_observation
        for observation in selected:
            c = rollout(
                lean,
                task,
                chosen["prefix"],
                Candidate.model_validate(observation["candidate"]),
                ProofState.model_validate(observation["successor"]),
                Budget.model_validate(config["budget"]),
                config["audit_timeout_s"],
            )
            c["metrics"]["initial_action_s"] = observation["elapsed_s"]
            c["metrics"]["lean_execution_s"] += observation["elapsed_s"]
            observation["continuation"] = c
            observation["exploration"] = "post_evaluation_bounded_rollout"
            if c["termination"] == "resource_limit:lean_timeout":
                break
    if digest(MODELS / "frozen.json") != before:
        raise ValueError("Model artifacts changed during post-evaluation diagnostics")
    return {
        "task_id": task.id,
        "split": task.split,
        "domain": task.domain,
        "case": case,
        "role": "Held-out post-evaluation diagnostic; excluded from every training loader",
        "source_trace": str(source.relative_to(ROOT)),
        "source_trace_raw_sha256": hashlib.sha256(raw_bytes(source)).hexdigest(),
        "source_verification": audit.model_dump(),
        "model_freeze_sha256": before,
        "states": [chosen],
        "probed_states": probed,
        "elapsed_s": time.monotonic() - start,
    }


def run() -> dict[str, Any]:
    report = read_json(EXPERIMENT / "summary.json")
    paths = trace_paths(EXPERIMENT / "traces")
    grouped: dict[str, dict[str, tuple[Trace, Path]]] = {}
    for path in paths:
        trace = Trace.model_validate_json(raw_bytes(path))
        if trace.metadata["repeat"] == "0":
            grouped.setdefault(trace.task.id, {})[trace.algorithm] = (trace, path)
    cases: dict[str, dict[str, Any]] = {}
    for baseline in ("learned", "applicability_only"):
        values = []
        for ident, row in report["per_theorem"].items():
            a, b = row["algorithms"]["outcome"], row["algorithms"][baseline]
            if a["verified"] == a["runs"] and b["verified"] == b["runs"]:
                values.append((a["attempted_candidates"] - b["attempted_candidates"], ident))
        for direction, choices in [
            ("lower_cost", [x for x in values if x[0] < 0]),
            ("higher_cost", [x for x in values if x[0] > 0]),
        ]:
            if not choices:
                continue
            delta, ident = min(choices) if direction == "lower_cost" else max(choices)
            cases.setdefault(
                ident, {"kind": direction, "baseline": baseline, "attempt_delta": delta}
            )
    for ident, policies in sorted(grouped.items()):
        a, b = policies["outcome"][0], policies["bfs"][0]
        if a.status == b.status == "verified" and a.proof != b.proof:
            cases.setdefault(
                ident,
                {
                    "kind": "different_verified_path",
                    "baseline": "bfs",
                    "attempt_delta": a.metrics.attempted_candidates
                    - b.metrics.attempted_candidates,
                },
            )
            break
    DIAGNOSTICS.mkdir(parents=True, exist_ok=False)
    logs = []
    for ident, case in cases.items():
        trace, path = grouped[ident]["outcome"]
        try:
            record = diagnostic(trace, path, case)
            (DIAGNOSTICS / f"{ident}.json").write_text(
                json.dumps(record, indent=2, ensure_ascii=False) + "\n"
            )
            log = {
                "task_id": ident,
                "case": case,
                "status": "recorded",
                "depth": record["states"][0]["depth"],
            }
        except Exception as error:
            log = {
                "task_id": ident,
                "case": case,
                "status": "diagnostic_unavailable",
                "error": str(error),
            }
        logs.append(log)
        print(log, flush=True)
    result = {
        "purpose": "Post-evaluation illustration; never fitting/task selection",
        "model_freeze_sha256": digest(MODELS / "frozen.json"),
        "cases": logs,
    }
    (DIAGNOSTICS / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
