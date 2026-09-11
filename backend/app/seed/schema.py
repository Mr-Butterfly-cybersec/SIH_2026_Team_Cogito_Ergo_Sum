"""Validated schema for the demo organization snapshot.

The snapshot is committed and auditable: every asset, control and finding in the demo can
be traced to a line in ``data/org_demo.json``.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.risk.control_effect import ControlCategory


class SeedOrganization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    sector: str | None = None
    currency: str = "INR"
    description: str | None = None
    framework_scope: list[str] = Field(default_factory=list)


class SeedBusinessUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    criticality: int = Field(ge=1, le=5)
    description: str | None = None


class SeedService(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_unit_id: str
    name: str
    revenue_dependency: int | None = Field(default=None, ge=0, le=5)
    regulatory_scope: str | None = None
    description: str | None = None


class SeedAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    name: str
    category: str = "internal"
    service_id: str | None = None
    owner: str | None = None
    internet_exposed: bool = False
    rto_hours: float | None = None
    criticality: dict[str, int] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class SeedControlEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    configuration_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    policy_compliance: float = Field(default=1.0, ge=0.0, le=1.0)
    recent_incident_signal: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_age_days: int | None = Field(default=None, ge=0)


class SeedControl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_id: str
    name: str
    category: ControlCategory
    applies_to_assets: list[str] = Field(default_factory=list)
    cost: float | None = None
    notes: str | None = None
    evidence: SeedControlEvidence


class SeedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    asset_id: str
    cve_id: str | None = None
    title: str | None = None
    source: str = "unknown"
    raw_severity: str | None = None
    detected_at: date | None = None
    status: str = "open"


class SeedScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str | None = None
    asset_id: str | None = None
    service_id: str | None = None
    category: str | None = None
    attack_techniques: list[str] = Field(default_factory=list)
    cve_ids: list[str] = Field(default_factory=list)


class SeedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    kind: str
    occurred_at: datetime | None = None
    asset_id: str | None = None
    severity: str | None = None
    description: str | None = None


class SeedSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization: SeedOrganization
    business_units: list[SeedBusinessUnit]
    services: list[SeedService]
    assets: list[SeedAsset]
    controls: list[SeedControl]
    findings: list[SeedFinding]
    scenarios: list[SeedScenario]
    events: list[SeedEvent] = Field(default_factory=list)

    def validate_references(self) -> None:
        """Fail loudly if the snapshot refers to an entity that does not exist."""
        unit_ids = {u.id for u in self.business_units}
        service_ids = {s.id for s in self.services}
        asset_ids = {a.asset_id for a in self.assets}
        cve_ids = {f.cve_id for f in self.findings if f.cve_id}

        for service in self.services:
            if service.business_unit_id not in unit_ids:
                raise ValueError(f"{service.id}: unknown business unit {service.business_unit_id}")
        for asset in self.assets:
            if asset.service_id and asset.service_id not in service_ids:
                raise ValueError(f"{asset.asset_id}: unknown service {asset.service_id}")
        for control in self.controls:
            unknown = set(control.applies_to_assets) - asset_ids
            if unknown:
                raise ValueError(f"{control.control_id}: unknown assets {sorted(unknown)}")
        for finding in self.findings:
            if finding.asset_id not in asset_ids:
                raise ValueError(f"{finding.finding_id}: unknown asset {finding.asset_id}")
        for scenario in self.scenarios:
            if scenario.asset_id and scenario.asset_id not in asset_ids:
                raise ValueError(f"{scenario.id}: unknown asset {scenario.asset_id}")
            if scenario.service_id and scenario.service_id not in service_ids:
                raise ValueError(f"{scenario.id}: unknown service {scenario.service_id}")
        _ = cve_ids
