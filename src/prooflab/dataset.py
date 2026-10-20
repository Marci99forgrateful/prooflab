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
    for loader in (load_tasks, load_phase2_tasks, load_phase3_tasks, load_phase4_tasks):
        for task in loader():
            if task.id == ident:
                return task
    raise KeyError(ident)


def load_phase2_tasks() -> list[Task]:
    rows = json.loads((ROOT / "benchmarks/phase2/evaluation.json").read_text())
    tasks = [Task.model_validate(row) for row in rows]
    if len({task.id for task in tasks}) != len(tasks):
        raise ValueError("Duplicate Phase 2 task IDs")
    return tasks


def load_phase3_tasks() -> list[Task]:
    rows = json.loads((ROOT / "benchmarks/phase3/evaluation.json").read_text())
    tasks = [Task.model_validate(row) for row in rows]
    if len({task.id for task in tasks}) != len(tasks):
        raise ValueError("Duplicate Phase 3 task IDs")
    return tasks


def load_phase4_tasks() -> list[Task]:
    rows = json.loads((ROOT / "benchmarks/phase4/evaluation.json").read_text())
    tasks = [Task.model_validate(row) for row in rows]
    if len({task.id for task in tasks}) != len(tasks):
        raise ValueError("Duplicate Phase 4 task IDs")
    return tasks
