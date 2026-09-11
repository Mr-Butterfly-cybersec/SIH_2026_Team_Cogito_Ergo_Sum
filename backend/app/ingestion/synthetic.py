"""Synthetic organization adapter.

Reads the committed demo snapshot and projects it onto the normalized telemetry records,
so the rest of the pipeline cannot tell synthetic telemetry from a real source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.ingestion.base import TelemetryAdapter
from app.ingestion.models import AssetRecord, ControlRecord, EventRecord, FindingRecord

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[1] / "seed" / "data" / "org_demo.json"


class SyntheticAdapter(TelemetryAdapter):
    name = "synthetic"

    def __init__(self, path: str | Path | None = None, data: dict[str, Any] | None = None) -> None:
        if data is not None:
            self._data = data
        else:
            source = Path(path) if path is not None else DEFAULT_SNAPSHOT
            self._data = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}

    def fetch_assets(self) -> list[AssetRecord]:
        return [
            AssetRecord(
                asset_id=asset["asset_id"],
                name=asset["name"],
                category=asset.get("category", "internal"),
                business_service=asset.get("service_id"),
                owner=asset.get("owner"),
                internet_exposed=asset.get("internet_exposed", False),
                criticality=asset.get("criticality", {}),
                rto_hours=asset.get("rto_hours"),
                tags=asset.get("tags", []),
            )
            for asset in self._data.get("assets", [])
        ]

    def fetch_findings(self) -> list[FindingRecord]:
        return [
            FindingRecord(
                finding_id=finding["finding_id"],
                asset_id=finding["asset_id"],
                cve_id=finding.get("cve_id"),
                title=finding.get("title"),
                source=finding.get("source", "unknown"),
                raw_severity=finding.get("raw_severity"),
            )
            for finding in self._data.get("findings", [])
        ]

    def fetch_controls(self) -> list[ControlRecord]:
        records = []
        for control in self._data.get("controls", []):
            evidence = control.get("evidence", {})
            records.append(
                ControlRecord(
                    control_id=control["control_id"],
                    name=control["name"],
                    category=control.get("category", "resistive"),
                    coverage=evidence.get("coverage"),
                    configuration_strength=evidence.get("configuration_strength"),
                    policy_compliance=evidence.get("policy_compliance"),
                    recent_incident_signal=evidence.get("recent_incident_signal"),
                    verification_age_days=evidence.get("verification_age_days"),
                    applies_to_assets=control.get("applies_to_assets", []),
                )
            )
        return records

    def fetch_events(self) -> list[EventRecord]:
        return [EventRecord.model_validate(event) for event in self._data.get("events", [])]
