"""Loopback-only, finite-dataset API. No endpoint accepts Lean or tactic source."""

from __future__ import annotations

import atexit
import secrets
import threading
from collections.abc import AsyncIterator, Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from prooflab.dataset import get_task, load_phase2_tasks, load_phase3_tasks, load_tasks
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Budget, Model, Trace
from prooflab.outcome import MODELS, OutcomeRanking
from prooflab.search import search


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    shutdown()


app = FastAPI(title="ProofLab", version="0.3.0", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="prooflab")
lock = threading.Lock()


@dataclass
class Job:
    cancel: threading.Event = field(default_factory=threading.Event)
    state: str = "running"
    trace: Trace | None = None
    error: str | None = None


jobs: dict[str, Job] = {}


class SearchRequest(Model):
    task_id: str
    algorithm: Literal["bfs", "best_first", "learned", "outcome"] = "best_first"
    budget: Budget = Budget()


@app.middleware("http")
async def local_only(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Browsers may read replay assets anywhere; computation is a same-origin operation.
    if request.url.path.startswith("/api/") and request.method != "GET":
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin is not None and origin != expected:
            return Response("Cross-origin computation is disabled", status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return Response("Cross-site computation is disabled", status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    return response


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"service": "prooflab", "mode": "local", "tasks": len(load_tasks())}


@app.get("/api/tasks")
def tasks(dataset: Literal["phase1", "phase2", "phase3"] = "phase1") -> list[dict[str, object]]:
    loader = {"phase1": load_tasks, "phase2": load_phase2_tasks, "phase3": load_phase3_tasks}[
        dataset
    ]
    return [t.model_dump() for t in loader()]


@app.get("/api/model")
def model(
    variant: Literal["phase2", "outcome", "applicability_only", "old_features_outcome"] = "phase2",
) -> dict[str, object]:
    ranker = LearnedRanking() if variant == "phase2" else OutcomeRanking(MODELS / f"{variant}.json")
    return {"sha256": ranker.model_hash, **ranker.model.model_dump()}


@app.get("/api/continuations")
def continuation_index() -> list[dict[str, object]]:
    from prooflab.research import manifest

    return manifest()


@app.get("/api/continuations/{role}/{task_id}")
def continuation_record(
    role: Literal["development", "diagnostic"], task_id: str
) -> dict[str, object]:
    from prooflab.research import bundle

    try:
        return bundle(role, task_id)
    except KeyError:
        raise HTTPException(404, "Unknown repository-owned continuation record") from None


def execute(job: Job, body: SearchRequest) -> None:
    try:
        job.trace = search(
            get_task(body.task_id),
            body.algorithm,
            body.budget,
            job.cancel,
            comparison_ranker=LearnedRanking(),
            comparison_outcome=OutcomeRanking(),
        )
        job.state = "completed"
    except Exception as error:
        job.error = str(error)
        job.state = "error"


@app.post("/api/search", status_code=202)
def start_search(body: SearchRequest) -> dict[str, str]:
    try:
        get_task(body.task_id)
    except KeyError:
        raise HTTPException(404, "Unknown repository-owned task") from None
    with lock:
        if sum(job.state == "running" for job in jobs.values()) >= 2:
            raise HTTPException(429, "Two searches are already running")
        if len(jobs) >= 24:
            done = next((key for key, job in jobs.items() if job.state != "running"), None)
            if done:
                del jobs[done]
        ident = secrets.token_hex(16)
        job = Job()
        jobs[ident] = job
        pool.submit(execute, job, body)
    return {"job_id": ident}


@app.get("/api/jobs/{ident}")
def get_job(ident: str) -> dict[str, object]:
    job = jobs.get(ident)
    if job is None:
        raise HTTPException(404, "Unknown job")
    return {"state": job.state, "trace": job.trace, "error": job.error}


@app.delete("/api/jobs/{ident}")
def cancel_job(ident: str) -> dict[str, str]:
    job = jobs.get(ident)
    if job is None:
        raise HTTPException(404, "Unknown job")
    job.cancel.set()
    return {"state": "cancellation_requested"}


def shutdown() -> None:
    for job in jobs.values():
        job.cancel.set()
    pool.shutdown(wait=False, cancel_futures=True)


atexit.register(shutdown)

web = ROOT / "web/dist"
if web.is_dir():
    app.mount("/", StaticFiles(directory=web, html=True), name="app")
else:

    @app.get("/")
    def index() -> FileResponse:
        raise HTTPException(503, "Build the frontend: cd web && npm ci && npm run build")
