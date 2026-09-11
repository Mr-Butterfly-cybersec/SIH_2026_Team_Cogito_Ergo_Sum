"""Normalized record types emitted by every telemetry adapter.

All adapters converge on these shapes so downstream code never has to know which
security product a record came from.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.risk.schemas import ProvenanceModel


class CvssScore(BaseModel):
    """A CVSS score with the version it came from (never mix versions)."""

    model_config = ConfigDict(extra="forbid")

    version: str  # "4.0" | "3.1" | "3.0" | "2.0"
    base_score: float
    severity: str  # NONE | LOW | MEDIUM | HIGH | CRITICAL
    vector: str | None = None
    source: str | None = None
    metric_type: str | None = None  # Primary | Secondary
    exploitability_score: float | None = None
    impact_score: float | None = None


class EpssScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cve_id: str
    epss: float
    percentile: float
    score_date: date | None = None


class KevEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cve_id: str
    vendor_project: str | None = None
    product: str | None = None
    vulnerability_name: str | None = None
    date_added: date | None = None
    due_date: date | None = None
    known_ransomware: bool = False
    required_action: str | None = None
    cwes: list[str] = Field(default_factory=list)


class VulnerabilityRecord(BaseModel):
    """A CVE enriched from public vulnerability intelligence."""

    model_config = ConfigDict(extra="forbid")

    cve_id: str
    description: str | None = None
    published: datetime | None = None
    last_modified: datetime | None = None
    status: str | None = None

    cvss: CvssScore | None = None
    cwes: list[str] = Field(default_factory=list)
    affected_cpe: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    epss: float | None = None
    epss_percentile: float | None = None
    epss_date: date | None = None

    kev: bool = False
    kev_date_added: date | None = None
    kev_due_date: date | None = None
    kev_ransomware: bool = False
    kev_required_action: str | None = None

    attack_techniques: list[str] = Field(default_factory=list)

    sources: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceModel] = Field(default_factory=list)

    @property
    def has_cvss(self) -> bool:
        return self.cvss is not None

    @property
    def has_epss(self) -> bool:
        return self.epss is not None

    @property
    def enriched(self) -> bool:
        """A record counts as enriched when both severity and likelihood are present."""
        return self.has_cvss and self.has_epss


class AssetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    name: str
    category: str = "internal"  # internet_facing | internal | cloud
    business_unit: str | None = None
    business_service: str | None = None
    owner: str | None = None
    internet_exposed: bool = False
    criticality: dict[str, int] = Field(default_factory=dict)
    rto_hours: float | None = None
    tags: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceModel] = Field(default_factory=list)


class FindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    asset_id: str
    cve_id: str | None = None
    title: str | None = None
    source: str = (
        "unknown"  # vulnerability_mgmt | siem | edr | cspm | iam | inventory | threat_intel
    )
    raw_severity: str | None = None
    detected_at: date | None = None
    provenance: list[ProvenanceModel] = Field(default_factory=list)


class ControlRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_id: str
    name: str
    category: str = "resistive"  # avoidance | deterrent | resistive | responsive
    coverage: float | None = None
    configuration_strength: float | None = None
    policy_compliance: float | None = None
    recent_incident_signal: float | None = None
    verification_age_days: int | None = None
    applies_to_assets: list[str] = Field(default_factory=list)
    provenance: list[ProvenanceModel] = Field(default_factory=list)


class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    kind: str
    occurred_at: datetime | None = None
    asset_id: str | None = None
    severity: str | None = None
    description: str | None = None
    provenance: list[ProvenanceModel] = Field(default_factory=list)
