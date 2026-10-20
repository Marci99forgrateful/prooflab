"""Lossless, deterministic compression of large genuine execution traces."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def raw_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def read_json(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(raw_bytes(path))
    return value


def trace_paths(directory: Path) -> list[Path]:
    paths = sorted([*directory.glob("*.json"), *directory.glob("*.json.gz")])
    names = [p.name.removesuffix(".gz") for p in paths]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate raw/compressed trace; keep one canonical copy")
    return paths


def compact(directory: Path) -> dict[str, Any]:
    """Retain exact source bytes and their hashes; never drop execution fields."""
    records: dict[str, dict[str, Any]] = {}
    for path in trace_paths(directory / "traces"):
        raw = raw_bytes(path)
        target = path if path.suffix == ".gz" else path.with_suffix(".json.gz")
        if path.suffix != ".gz":
            compressed = gzip.compress(raw, compresslevel=6, mtime=0)
            if gzip.decompress(compressed) != raw:
                raise ValueError("Lossless compression verification failed")
            target.write_bytes(compressed)
        records[path.name.removesuffix(".gz")] = {
            "file": target.name,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "gzip_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "raw_bytes": len(raw),
            "stored_bytes": target.stat().st_size,
        }
        if path != target:
            path.unlink()  # Reversible: byte-exact original is retained in verified gzip.
    report = {
        "format": "gzip of exact original JSON bytes; mtime=0; SHA-256 indexed",
        "traces": records,
        "raw_bytes": sum(r["raw_bytes"] for r in records.values()),
        "stored_bytes": sum(r["stored_bytes"] for r in records.values()),
        "inspect": (
            "gzip -dc traces/<name>.json.gz; or prooflab unpack-traces "
            "--experiment <dir> --output <new-dir>"
        ),
    }
    (directory / "trace-storage.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def unpack(directory: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    manifest = read_json(directory / "trace-storage.json")
    for name, entry in manifest["traces"].items():
        if Path(name).name != name or Path(entry["file"]).name != entry["file"]:
            raise ValueError("Unsafe archive index path")
        path = directory / "traces" / entry["file"]
        raw = raw_bytes(path)
        if hashlib.sha256(raw).hexdigest() != entry["raw_sha256"]:
            raise ValueError("Archive integrity check failed")
        (destination / name).write_bytes(raw)
