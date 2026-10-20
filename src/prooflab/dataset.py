from __future__ import annotations

import json

from prooflab.lean import ROOT
from prooflab.models import Task


def load_tasks() -> list[Task]:
    rows = json.loads((ROOT / "benchmarks/tasks.json").read_text())
    tasks = [Task.model_validate(row) for row in rows]
    if len({task.id for task in tasks}) != len(tasks):
        raise ValueError("Duplicate benchmark task IDs")
    return tasks


def get_task(ident: str) -> Task:
    for task in load_tasks():
        if task.id == ident:
            return task
    raise KeyError(ident)
