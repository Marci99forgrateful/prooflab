"""Bounded read-only native retrieval on a separately named Lean session.

The original LeanSession, Bridge, independent verifier and FIFO framing remain
unchanged. This subclass reuses framing/lifecycle, supplying a different bootstrap.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from threading import Event
from typing import Any

from prooflab.lean import ROOT, LeanError, LeanSession, lake_command, lean_environment
from prooflab.models import ProofState, Task

INDEX = ROOT / "benchmarks/phase5/declarations.json"


class RetrievalSession(LeanSession):
    def __init__(self, task: Task, timeout: float = 20, cancel: Event | None = None) -> None:
        self.resource_usage: dict[str, Any] = {}
        self.cancel = cancel
        self._directory = tempfile.TemporaryDirectory(prefix="prooflab-retrieval-")
        self.process: subprocess.Popen[str] | None = None
        self._request_fd: int | None = None
        self._response_fd: int | None = None
        self._buffer = b""
        self.diagnostics: list[str] = []
        requests = Path(self._directory.name) / "requests.fifo"
        responses = Path(self._directory.name) / "responses.fifo"
        source = Path(self._directory.name) / "Session.lean"
        source.write_text(
            "import ProofLab.Retrieval\nset_option maxHeartbeats 300000\n"
            f"example {task.binders} : {task.target} := by\n"
            f"  prooflab_retrieval_session {json.dumps(str(requests))} "
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

    def close(self) -> None:
        # Sample live process tree before lifecycle cleanup. Linux-only practical
        # resource accounting; independent audit processes are outside this sample.
        if self.process is not None and self.process.poll() is None:
            try:
                processes: dict[int, tuple[int, float, int]] = {}
                for base in Path("/proc").glob("[0-9]*"):
                    try:
                        fields = (base / "stat").read_text().rsplit(")", 1)[1].split()
                        cpu = (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
                        status = (base / "status").read_text().splitlines()
                        peak = next(
                            (int(x.split()[1]) for x in status if x.startswith("VmHWM:")), 0
                        )
                        processes[int(base.name)] = (int(fields[1]), cpu, peak)
                    except (OSError, ValueError, IndexError):
                        continue
                family = {self.process.pid}
                while True:
                    found = {pid for pid, (parent, _, _) in processes.items() if parent in family}
                    if found <= family:
                        break
                    family |= found
                self.resource_usage = dict(
                    cpu_s=sum(processes[p][1] for p in family if p in processes),
                    peak_rss_kib=sum(processes[p][2] for p in family if p in processes),
                    process_count=len(family),
                    scope=(
                        "live session tree CPU; sum of process HWM bounds, not "
                        "simultaneous peak; independent audits excluded"
                    ),
                )
            except (OSError, ValueError, IndexError):
                pass
        super().close()

    def retrieve(self, parent: int, names: list[str], timeout: float = 2) -> dict[str, Any]:
        if len(names) > 128 or len(names) != len(set(names)):
            raise ValueError("Declaration query exceeds frozen bounded index")
        assert self._request_fd is not None
        message = (json.dumps(dict(kind="retrieve", parent=parent, names=names)) + "\n").encode()
        if len(message) > 16000 or os.write(self._request_fd, message) != len(message):
            raise LeanError("Retrieval request exceeded protocol limits")
        response = self._receive(timeout)
        if response.get("status") != "retrieved" or response.get("state_id") != parent:
            raise LeanError("Native retrieval failed: " + str(response))
        result: dict[str, Any] = response["retrieval"]
        return result


def declarations() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(INDEX.read_text())
    rows: list[dict[str, Any]] = data["declarations"]
    if not 24 < len(rows) <= 128 or len({r["name"] for r in rows}) != len(rows):
        raise ValueError("Invalid bounded native declaration index")
    return rows
