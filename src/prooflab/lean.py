"""Persistent Lean subprocess sessions, JSON protocol and independent proof audits."""

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from threading import Event
from types import TracebackType
from typing import Any

from prooflab.models import ProofState, Task, Verification

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "PROOFLAB:"
AUDIT = "PROOFLAB_AUDIT:"


class LeanError(RuntimeError):
    """A toolchain, protocol or process error; never a mathematical counterexample."""


class LeanTimeout(LeanError):
    pass


class Cancelled(LeanError):
    pass


def lean_environment() -> dict[str, str]:
    result = dict(os.environ)
    # Prefer an explicitly configured toolchain, then this cloud's retained local toolchain.
    cloud = Path("/workspace/.toolchains/elan")
    portable = Path(result.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    local = (
        Path(result["ELAN_HOME"])
        if "ELAN_HOME" in result
        else (cloud if cloud.is_dir() else portable / "prooflab-tools/elan")
    )
    if local.is_dir():
        result["ELAN_HOME"] = str(local)
        result["PATH"] = str(local / "bin") + os.pathsep + result.get("PATH", "")
    return result


def lake_command() -> list[str]:
    env = lean_environment()
    lake = shutil.which("lake", path=env.get("PATH"))
    if not lake:
        raise LeanError("Lean/Lake is missing. Run scripts/bootstrap.sh first.")
    return [lake, "env", "lean", "--memory=2048"]


def theorem_source(task: Task, steps: list[str]) -> str:
    # These strings are trusted, repository-owned dataset entries and generated tactics.
    return (
        "import ProofLab.Bridge\n\nset_option maxHeartbeats 300000\n"
        f"theorem prooflab_result {task.binders} : {task.target} := by\n"
        + "".join(f"  {step}\n" for step in steps)
        + "\n#prooflab_audit prooflab_result\n"
    )


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()


class LeanSession:
    """One theorem, one native Lean elaborator, many isolated saved branches.

    A timed-out tactic terminates the session. We do not reuse possibly poisoned state.
    The caller must run the fresh-process audit to certify any successful path.
    """

    def __init__(self, task: Task, timeout: float = 20, cancel: Event | None = None) -> None:
        self.cancel = cancel
        self._directory = tempfile.TemporaryDirectory(prefix="prooflab-session-")
        self.process: subprocess.Popen[str] | None = None
        self._request_fd: int | None = None
        self._response_fd: int | None = None
        self._buffer = b""
        self.diagnostics: list[str] = []
        requests = Path(self._directory.name) / "requests.fifo"
        responses = Path(self._directory.name) / "responses.fifo"
        source = Path(self._directory.name) / "Session.lean"
        source.write_text(
            "import ProofLab.Bridge\nset_option maxHeartbeats 300000\n"
            f"example {task.binders} : {task.target} := by\n"
            f"  prooflab_session {json.dumps(str(requests))} {json.dumps(str(responses))}\n"
        )
        try:
            for path in (requests, responses):
                os.mkfifo(path, 0o600)
            self._request_fd = os.open(requests, os.O_RDWR | os.O_NONBLOCK)
            self._response_fd = os.open(responses, os.O_RDWR | os.O_NONBLOCK)
            self.process = subprocess.Popen(
                [*lake_command(), str(source)],
                cwd=ROOT,
                env=lean_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            message = self._receive(timeout)
            if message.get("status") != "ready":
                raise LeanError(str(message))
            self.initial = ProofState.model_validate(
                {"state_id": message["state_id"], "goals": message["goals"]}
            )
        except BaseException:
            self.close()
            raise

    def _receive(self, timeout: float) -> dict[str, Any]:
        assert self.process is not None and self.process.stdout is not None
        assert self._response_fd is not None
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(self._response_fd, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                if self.cancel is not None and self.cancel.is_set():
                    raise Cancelled("Search cancelled")
                if b"\n" in self._buffer:
                    line, self._buffer = self._buffer.split(b"\n", 1)
                    if not line.startswith(PREFIX.encode()):
                        raise LeanError("Malformed Lean protocol frame")
                    value: dict[str, Any] = json.loads(line[len(PREFIX) :])
                    return value
                if self.process.poll() is not None:
                    raise LeanError("Lean exited: " + self.process.stdout.read()[-6000:])
                if not selector.select(timeout=min(0.05, max(0, deadline - time.monotonic()))):
                    continue
                self._buffer += os.read(self._response_fd, 65536)
                if len(self._buffer) > 2_000_000:
                    raise LeanError("Lean protocol response exceeded 2 MB")
        raise LeanTimeout(f"Lean exceeded {timeout:.2f}s")

    def step(self, parent: int, tactic: str, timeout: float) -> dict[str, Any]:
        assert self._request_fd is not None
        message = (json.dumps({"parent": parent, "tactic": tactic}) + "\n").encode()
        if len(message) > 4096 or os.write(self._request_fd, message) != len(message):
            raise LeanError("Lean request exceeded protocol limits")
        return self._receive(timeout)

    def close(self) -> None:
        if self.process is not None:
            stop_process(self.process)
        for name in ("_request_fd", "_response_fd"):
            descriptor = getattr(self, name)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)
        self._directory.cleanup()

    def __enter__(self) -> LeanSession:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def verify(
    task: Task, steps: list[str], timeout: float = 20, cancel: Event | None = None
) -> Verification:
    """Re-elaborate and kernel check from scratch, then inspect transitive axioms.

    The axiom audit is authoritative; this lexical screen is additional defense.
    Only propext, Classical.choice, Quot.sound are accepted.
    """
    source = theorem_source(task, steps)
    digest = hashlib.sha256(source.encode()).hexdigest()
    start = time.monotonic()
    if re.search(r"\b(sorry|admit|axiom|unsafe|run_tac|native_decide|implemented_by)\b", source):
        return Verification(error="Forbidden proof construct", source_sha256=digest)
    with tempfile.TemporaryDirectory(prefix="prooflab-verify-") as directory:
        path = Path(directory) / "Verified.lean"
        path.write_text(source)
        process = subprocess.Popen(
            [*lake_command(), str(path)],
            cwd=ROOT,
            env=lean_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            deadline = start + timeout
            while True:
                if cancel is not None and cancel.is_set():
                    raise Cancelled("Verification cancelled")
                try:
                    output, _ = process.communicate(
                        timeout=min(0.1, max(0.001, deadline - time.monotonic()))
                    )
                    break
                except subprocess.TimeoutExpired:
                    if time.monotonic() >= deadline:
                        return Verification(
                            error="Independent verification timed out",
                            elapsed_s=time.monotonic() - start,
                            source_sha256=digest,
                        )
            for line in output.splitlines():
                if AUDIT in line and process.returncode == 0:
                    audit = json.loads(line.split(AUDIT, 1)[1])
                    return Verification(
                        verified=audit["verified"],
                        axioms=audit["axioms"],
                        elapsed_s=time.monotonic() - start,
                        source_sha256=digest,
                    )
            return Verification(
                error=output[-6000:] or "Independent audit marker missing",
                elapsed_s=time.monotonic() - start,
                source_sha256=digest,
            )
        finally:
            stop_process(process)
