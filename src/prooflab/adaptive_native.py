"""Phase 6 native session; unchanged inherited FIFO, step and audit boundary."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from threading import Event
from typing import Any

from prooflab.lean import ROOT, LeanError, lake_command, lean_environment
from prooflab.models import ProofState, Task
from prooflab.native_retrieval import RetrievalSession


class AdaptiveSession(RetrievalSession):
    def __init__(self, task: Task, timeout: float = 20, cancel: Event | None = None) -> None:
        self.resource_usage: dict[str, Any] = {}
        self.cancel = cancel
        self._directory = tempfile.TemporaryDirectory(prefix="prooflab-adaptive-")
        self.process: subprocess.Popen[str] | None = None
        self._request_fd: int | None = None
        self._response_fd: int | None = None
        self._buffer = b""
        self.diagnostics: list[str] = []
        requests = Path(self._directory.name) / "requests.fifo"
        responses = Path(self._directory.name) / "responses.fifo"
        source = Path(self._directory.name) / "Session.lean"
        source.write_text(
            "import ProofLab.Adaptive\nset_option maxHeartbeats 300000\n"
            f"example {task.binders} : {task.target} := by\n"
            f"  prooflab_adaptive_session {json.dumps(str(requests))} "
            f"{json.dumps(str(responses))}\n"
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
