"""Measure attempted native retrieval, including failed/time-limited round trips.

No change to request framing, native proof steps, state restoration or verification.
Incomplete native probe/heartbeat counts remain unknown, never estimated.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from prooflab.adaptive_native import AdaptiveSession
from prooflab.lean import LeanSession
from prooflab.models import Candidate, ProofState, Trace
from prooflab.native_retrieval import RetrievalSession


def measured_retrieve(
    session: Any, call: Callable[..., dict[str, Any]], parent: int, names: list[str], timeout: float
) -> dict[str, Any]:
    if not hasattr(session, "retrieval_events"):
        session.retrieval_events = []
    event: dict[str, Any] = dict(
        parent_state_id=parent, status="failed", requested_declarations=len(names)
    )
    session.last_native_frame = None
    tick = time.monotonic()
    try:
        result = call(parent, names, timeout)
        event.update(
            status="completed",
            native={
                k: result.get(k, 0)
                for k in (
                    "declaration_probes",
                    "rewrite_probes",
                    "term_constructions",
                    "heartbeats",
                )
            },
        )
        return result
    except Exception as error:
        event.update(error=str(error), error_kind=type(error).__name__)
        frame = getattr(session, "last_native_frame", None)
        if frame and "native_heartbeats" in frame:
            event["native"] = {"heartbeats": frame["native_heartbeats"]}
            event["native_elapsed_s"] = frame.get("native_elapsed_ns", 0) / 1e9
        raise
    finally:
        event["elapsed_s"] = time.monotonic() - tick
        session.retrieval_events.append(event)


class MeteredRetrieval(RetrievalSession):
    def _receive(self, timeout: float) -> dict[str, Any]:
        result = super()._receive(timeout)
        self.last_native_frame = result
        return result

    def retrieve(self, parent: int, names: list[str], timeout: float = 2) -> dict[str, Any]:
        return measured_retrieve(self, super().retrieve, parent, names, timeout)


class MeteredAdaptive(AdaptiveSession):
    def _receive(self, timeout: float) -> dict[str, Any]:
        result = super()._receive(timeout)
        self.last_native_frame = result
        return result

    def retrieve(self, parent: int, names: list[str], timeout: float = 2) -> dict[str, Any]:
        return measured_retrieve(self, super().retrieve, parent, names, timeout)


class MeteringProvider:
    def __init__(self, base: Any) -> None:
        self.base = base
        self.model = getattr(base, "model", None)
        self.session: LeanSession | None = None

    def generate(
        self,
        lean: LeanSession,
        state: ProofState,
        limit: int,
        forbidden: frozenset[str],
        timeout: float,
    ) -> tuple[list[Candidate], dict[str, Any]]:
        self.session = lean
        result: tuple[list[Candidate], dict[str, Any]] = self.base.generate(
            lean, state, limit, forbidden, timeout
        )
        return result


def retrieval_metrics(trace: Trace, provider: MeteringProvider | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = (
        getattr(provider.session, "retrieval_events", []) if provider else []
    )
    mapping = {n.state.state_id: n.id for n in trace.nodes if n.state is not None}
    for event in events:
        event["node_id"] = mapping.get(event["parent_state_id"])
    actual = sum(e["elapsed_s"] for e in events)
    trace.metrics.lean_execution_s += actual - trace.metrics.retrieval_s
    trace.metrics.retrieval_s = actual
    trace.metrics.retrieval_queries = len(events)
    for field in ("declaration_probes", "rewrite_probes", "term_constructions"):
        setattr(trace.metrics, field, sum(e.get("native", {}).get(field, 0) for e in events))
    trace.metrics.retrieval_heartbeats = sum(
        e.get("native", {}).get("heartbeats", 0) for e in events
    )
    return events
