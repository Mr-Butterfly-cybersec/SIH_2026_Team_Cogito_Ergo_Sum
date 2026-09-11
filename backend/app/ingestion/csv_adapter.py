"""CSV adapter — the simplest way to load an organization's own telemetry."""

from __future__ import annotations

import csv
from pathlib import Path

from app.ingestion.base import TelemetryAdapter
from app.ingestion.models import AssetRecord, ControlRecord, FindingRecord
from app.normalization.vulnerabilities import parse_date


def _rows(path: str | Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open(newline="", encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle)]


def _float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _int(value: str | None) -> int | None:
    number = _float(value)
    return int(number) if number is not None else None


def _bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


class CsvAdapter(TelemetryAdapter):
    name = "csv"

    def __init__(
        self,
        *,
        findings_path: str | Path | None = None,
        assets_path: str | Path | None = None,
        controls_path: str | Path | None = None,
    ) -> None:
        self.findings_path = findings_path
        self.assets_path = assets_path
        self.controls_path = controls_path

    def fetch_findings(self) -> list[FindingRecord]:
        findings = []
        for index, row in enumerate(_rows(self.findings_path)):
            asset_id = row.get("asset_id", "").strip()
            if not asset_id:
                continue
            cve_id = (row.get("cve_id") or "").strip() or None
            findings.append(
                FindingRecord(
                    finding_id=row.get("finding_id", "").strip() or f"FND-{index + 1:04d}",
                    asset_id=asset_id,
                    cve_id=cve_id,
                    title=row.get("title") or None,
                    source=(row.get("source") or "unknown").strip() or "unknown",
                    raw_severity=row.get("raw_severity") or None,
                    detected_at=parse_date(row.get("detected_at")),
                )
            )
        return findings

    def fetch_assets(self) -> list[AssetRecord]:
        assets = []
        for row in _rows(self.assets_path):
            asset_id = row.get("asset_id", "").strip()
            if not asset_id:
                continue
            assets.append(
                AssetRecord(
                    asset_id=asset_id,
                    name=row.get("name", asset_id),
                    category=(row.get("category") or "internal").strip() or "internal",
                    business_unit=row.get("business_unit") or None,
                    business_service=row.get("business_service") or None,
                    owner=row.get("owner") or None,
                    internet_exposed=_bool(row.get("internet_exposed")),
                    rto_hours=_float(row.get("rto_hours")),
                )
            )
        return assets

    def fetch_controls(self) -> list[ControlRecord]:
        controls = []
        for row in _rows(self.controls_path):
            control_id = row.get("control_id", "").strip()
            if not control_id:
                continue
            applies = [
                a.strip() for a in (row.get("applies_to_assets") or "").split(";") if a.strip()
            ]
            controls.append(
                ControlRecord(
                    control_id=control_id,
                    name=row.get("name", control_id),
                    category=(row.get("category") or "resistive").strip() or "resistive",
                    coverage=_float(row.get("coverage")),
                    configuration_strength=_float(row.get("configuration_strength")),
                    policy_compliance=_float(row.get("policy_compliance")),
                    recent_incident_signal=_float(row.get("recent_incident_signal")),
                    verification_age_days=_int(row.get("verification_age_days")),
                    applies_to_assets=applies,
                )
            )
        return controls
