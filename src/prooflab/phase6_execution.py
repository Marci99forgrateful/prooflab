"""One shared bounded engine; named historical and adaptive interventions."""

from __future__ import annotations

import time
from pathlib import Path
from threading import Event
from typing import Any

from prooflab.adaptive import CanonicalOutcomeRanking, HybridProvider
from prooflab.adaptive_native import AdaptiveSession
from prooflab.frontier import FrontierModel
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, SearchAlgorithm, Task, Trace
from prooflab.native_retrieval import RetrievalSession
from prooflab.outcome import OutcomeRanking
from prooflab.retrieval import TypedProvider
from prooflab.search import search


def run_task(
    task: Task,
    mode: str,
    budget: Budget,
    model_path: Path | None = None,
    cancel: Event | None = None,
) -> Trace:
    started = time.monotonic()
    historical = {
        "phase4": "phase4",
        "symbolic": "phase4",
        "typed5": "typed",
        "learned5": "learned",
        "phase4_canonical": "phase4",
    }
    provider: Any
    if mode in ("automation", "grind"):
        provider = None
        factory = RetrievalSession
        ranking = OutcomeRanking()
    elif mode in historical:
        provider = TypedProvider(historical[mode])
        factory = RetrievalSession
        ranking = CanonicalOutcomeRanking() if mode == "phase4_canonical" else OutcomeRanking()
    else:
        provider = HybridProvider("deterministic" if mode == "no_synthesis" else mode, model_path)
        factory = RetrievalSession if mode == "no_synthesis" else AdaptiveSession
        ranking = CanonicalOutcomeRanking()
    algorithm: SearchAlgorithm = (
        "automation" if mode == "automation" else "grind" if mode == "grind" else "outcome"
    )
    if mode in ("automation", "grind"):
        provider = None
        factory = RetrievalSession
    frontier = FrontierModel()
    comparison = LearnedRanking()
    comparison_outcome = OutcomeRanking()
    artifact_setup_s = time.monotonic() - started
    trace = search(
        task,
        algorithm,
        budget,
        ranking=ranking,
        cancel=cancel,
        comparison_frontier=frontier,
        comparison_ranker=comparison,
        comparison_outcome=comparison_outcome,
        provider=provider,
        session_factory=factory,
    )
    trace.metadata.update(
        generator_mode=mode,
        phase="6",
        artifact_setup_s=str(artifact_setup_s),
        runner_wall_s=str(time.monotonic() - started),
        tie_policy="historical stable input ties"
        if mode in ("phase4", "symbolic", "typed5", "learned5")
        else "explicit tactic-string ties after unchanged P3 scores",
    )
    return trace
