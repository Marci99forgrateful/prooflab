"""Exactly matched canonical strategy alternatives for the adaptive mode selector.

Historical source searches remain useful demonstrations, but their old tie rule
and witness engine are not the strategies actually executed by the new selector.
This separate preregistered development-only supplement avoids that mismatch.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from prooflab.adaptive import CanonicalOutcomeRanking, HybridProvider
from prooflab.adaptive_model import MODELS
from prooflab.adaptive_native import AdaptiveSession
from prooflab.adaptive_training import save
from prooflab.frontier import FrontierModel
from prooflab.lean import ROOT
from prooflab.learning import LearnedRanking
from prooflab.models import Budget
from prooflab.outcome import OutcomeRanking
from prooflab.phase3_data import digest
from prooflab.phase6_data import DIRECTORY, check_freeze, read_tasks
from prooflab.research_io import compact, read_json
from prooflab.search import metadata, search

DATA = ROOT / "experiments/phase6/selector-v1"


def collect(destination: Path = DATA) -> None:
    frozen = check_freeze()
    config = read_json(DIRECTORY / "selector-protocol.json")
    if (
        digest(DIRECTORY / "selector-protocol.json")
        != read_json(DIRECTORY / "selector-frozen.json")["protocol_sha256"]
    ):
        raise ValueError("Selector protocol changed")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "traces").mkdir()
    provenance = dict(
        **metadata(),
        evaluation_accessed=False,
        provisional_model_sha256=digest(MODELS / "learned.json"),
        relevance_sha256=__import__("hashlib")
        .sha256(
            json.dumps(read_json(MODELS / "learned.json")["relevance"], sort_keys=True).encode()
        )
        .hexdigest(),
        data_freeze_sha256=digest(DIRECTORY / "frozen.json"),
        selector_protocol_sha256=digest(DIRECTORY / "selector-protocol.json"),
        configuration=config,
        development_ids=frozen["development_ids"],
        source_sha256={
            str(p.relative_to(ROOT)): digest(p)
            for p in (
                ROOT / "ProofLab/Adaptive.lean",
                ROOT / "src/prooflab/adaptive.py",
                ROOT / "src/prooflab/phase6_counterfactuals.py",
            )
        },
    )
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    jobs = [(t, m) for t in read_tasks("development") for m in ("symbolic", "hybrid", "typed")]
    random.Random(6161).shuffle(jobs)

    def one(job: Any) -> None:
        task, mode = job
        provider = HybridProvider("learned", MODELS / "learned.json", forced_mode=mode)
        trace = search(
            task,
            "outcome",
            Budget.model_validate(config["budget"]),
            ranking=CanonicalOutcomeRanking(),
            comparison_ranker=LearnedRanking(),
            comparison_outcome=OutcomeRanking(),
            comparison_frontier=FrontierModel(),
            provider=provider,
            session_factory=AdaptiveSession,
        )
        trace.metadata.update(
            arm=mode, repeat="0", role="exact mode-selector development counterfactual"
        )
        save(destination / "traces" / f"{task.id}--{mode}.json.gz", trace.model_dump())
        print(task.id, mode, trace.status, trace.metrics.attempted_candidates, flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(one, j) for j in jobs]
        for f in as_completed(futures):
            f.result()
    compact(destination)
