from __future__ import annotations

import json
from pathlib import Path

import pytest

from prooflab.lean import ROOT
from prooflab.research_io import compact, raw_bytes, trace_paths, unpack


def test_real_trace_archive_preserves_every_original_byte(tmp_path: Path) -> None:
    source = ROOT / "experiments/phase2/evaluation-v1/traces/p2_congr_nested--learned--r0.json"
    directory = tmp_path / "experiment"
    (directory / "traces").mkdir(parents=True)
    raw = source.read_bytes()
    (directory / "traces" / source.name).write_bytes(raw)
    storage = compact(directory)
    paths = trace_paths(directory / "traces")
    assert len(paths) == 1 and paths[0].suffix == ".gz"
    assert raw_bytes(paths[0]) == raw
    assert storage["stored_bytes"] < storage["raw_bytes"]
    unpack(directory, tmp_path / "restored")
    assert (tmp_path / "restored" / source.name).read_bytes() == raw
    assert compact(directory) == storage


def test_archive_index_cannot_escape_destination(tmp_path: Path) -> None:
    (tmp_path / "traces").mkdir()
    (tmp_path / "trace-storage.json").write_text(
        json.dumps({"traces": {"../outside.json": {"file": "safe.json.gz"}}})
    )
    with pytest.raises(ValueError, match="Unsafe"):
        unpack(tmp_path, tmp_path / "out")
