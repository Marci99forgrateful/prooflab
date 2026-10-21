"""One shared bounded engine; named historical and adaptive interventions."""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Event
from typing import Any

from prooflab.adaptive import CanonicalOutcomeRanking, HybridProvider
from prooflab.frontier import FrontierModel
from prooflab.lean import LeanSession
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, SearchAlgorithm, Task, Trace
from prooflab.outcome import OutcomeRanking
from prooflab.phase6_metering import (
    MeteredAdaptive,
    MeteredRetrieval,
    MeteringProvider,
    retrieval_metrics,
)
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
    cpu_started = time.thread_time()
    historical = {
        "phase4": "phase4",
        "symbolic": "phase4",
        "typed5": "typed",
        "learned5": "learned",
        "phase4_canonical": "phase4",
    }
    provider: Any
    factory: type[LeanSession]
    if mode in ("automation", "grind"):
        provider = None
        factory = MeteredRetrieval
        ranking = OutcomeRanking()
    elif mode in historical:
        provider = TypedProvider(historical[mode])
        factory = MeteredRetrieval
        ranking = CanonicalOutcomeRanking() if mode == "phase4_canonical" else OutcomeRanking()
    else:
        provider = HybridProvider("deterministic" if mode == "no_synthesis" else mode, model_path)
        factory = MeteredRetrieval if mode == "no_synthesis" else MeteredAdaptive
        ranking = CanonicalOutcomeRanking()
    algorithm: SearchAlgorithm = (
        "automation" if mode == "automation" else "grind" if mode == "grind" else "outcome"
    )
    if mode in ("automation", "grind"):
        provider = None
        factory = MeteredRetrieval
    provider = MeteringProvider(provider) if provider is not None else None
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
    events = retrieval_metrics(trace, provider)
    trace.metrics.coordinator_cpu_s = time.thread_time() - cpu_started
    active_model = getattr(provider, "model", None)
    trace.metadata.update(
        generator_mode=mode,
        phase="6",
        native_query_events=json.dumps(events, separators=(",", ":")),
        failed_retrieval_queries=str(sum(e["status"] != "completed" for e in events)),
        adaptive_model_sha256=active_model.sha256 if active_model else "not used",
        adaptive_model_file=(model_path.name if model_path else f"{mode}.json")
        if active_model
        else "not used",
        artifact_setup_s=str(artifact_setup_s),
        runner_wall_s=str(time.monotonic() - started),
        tie_policy="historical stable input ties"
        if mode in ("phase4", "symbolic", "typed5", "learned5")
        else "explicit tactic-string ties after unchanged P3 scores",
    )
    return trace
