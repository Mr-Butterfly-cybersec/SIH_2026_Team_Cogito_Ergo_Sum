"""Tiny JSON persistence for ingested data.

Phase 2 keeps normalized records on disk under ``backend/data/`` (gitignored). Phase 3
moves them into Postgres.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.ingestion.models import VulnerabilityRecord

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CACHE_DIR = DATA_DIR / "cache"
NORMALIZED_DIR = DATA_DIR / "normalized"
VULNERABILITIES_FILE = NORMALIZED_DIR / "vulnerabilities.json"
ATTACK_FILE = NORMALIZED_DIR / "attack.json"


def ensure_dirs() -> None:
    for directory in (DATA_DIR, CACHE_DIR, NORMALIZED_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class VulnerabilityStore:
    """JSON-backed store of normalized vulnerability records, keyed by CVE id."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or VULNERABILITIES_FILE

    def save(self, records: Iterable[VulnerabilityRecord]) -> Path:
        existing = self.load()
        for record in records:
            if record.cve_id:
                existing[record.cve_id] = record
        payload = {
            cve_id: record.model_dump(mode="json") for cve_id, record in sorted(existing.items())
        }
        return write_json(self.path, payload)

    def load(self) -> dict[str, VulnerabilityRecord]:
        payload = read_json(self.path) or {}
        return {
            cve_id: VulnerabilityRecord.model_validate(item) for cve_id, item in payload.items()
        }

    def get(self, cve_id: str) -> VulnerabilityRecord | None:
        return self.load().get(cve_id)


def save_attack_catalog(catalog: Any, path: Path | None = None) -> Path:
    target = path or ATTACK_FILE
    return write_json(target, catalog.model_dump(mode="json"))
