"""Planning context for the optimizer.

Projects the demo organization (assets, controls, findings, public intelligence) into
everything Phase 4 needs: materialized scenarios, control posture, and exploitation
evidence. Built entirely from committed inputs so it runs offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.ingestion.models import VulnerabilityRecord
from app.ingestion.store import VulnerabilityStore
from app.risk.asset_criticality import profile_from_asset
from app.risk.control_effect import ControlCategory
from app.risk.control_effect import ControlEvidence as ControlEvidenceScore
from app.risk.monte_carlo import CompiledScenario
from app.risk.scenario_factory import AssetContext, FindingContext, materialize_scenario
from app.risk.schemas import ScenarioSpec
from app.seed.org_demo import load_snapshot
from app.seed.schema import SeedSnapshot


@dataclass(frozen=True)
class ScenarioCatalogueEntry:
    id: str
    name: str
    description: str | None
    asset_id: str | None
    service_id: str | None
    category: str | None
    attack_techniques: tuple[str, ...] = ()
    cve_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ControlContext:
    control_id: str
    name: str
    category: ControlCategory
    effectiveness: float
    cost: float
    protects: tuple[str, ...]  # scenario ids
    evidence: dict[str, float | int | None] = field(default_factory=dict)


@dataclass
class PlanningContext:
    organization_name: str
    currency: str
    assets: dict[str, AssetContext]
    scenarios: dict[str, CompiledScenario]
    specs: dict[str, ScenarioSpec]
    catalogue: dict[str, ScenarioCatalogueEntry]
    controls: dict[str, ControlContext]
    vulnerabilities: dict[str, VulnerabilityRecord]
    findings_by_asset: dict[str, list[FindingContext]] = field(default_factory=dict)

    def scenario_cvss(self, scenario_id: str) -> float | None:
        entry = self.catalogue.get(scenario_id)
        if entry is None:
            return None
        scores = [
            self.vulnerabilities[cve].cvss.base_score
            for cve in entry.cve_ids
            if cve in self.vulnerabilities and self.vulnerabilities[cve].cvss is not None
        ]
        return max(scores) if scores else None

    def scenario_epss(self, scenario_id: str) -> float | None:
        entry = self.catalogue.get(scenario_id)
        if entry is None:
            return None
        scores = [
            self.vulnerabilities[cve].epss
            for cve in entry.cve_ids
            if cve in self.vulnerabilities and self.vulnerabilities[cve].epss is not None
        ]
        return max(scores) if scores else None

    def scenarios_for_asset(self, asset_id: str) -> tuple[str, ...]:
        return tuple(
            scenario_id
            for scenario_id, entry in self.catalogue.items()
            if entry.asset_id == asset_id
        )


def _asset_context(snapshot: SeedSnapshot) -> dict[str, AssetContext]:
    services = {service.id: service for service in snapshot.services}
    contexts: dict[str, AssetContext] = {}
    for asset in snapshot.assets:
        profile = profile_from_asset(asset.criticality)
        service = services.get(asset.service_id) if asset.service_id else None
        contexts[asset.asset_id] = AssetContext(
            asset_id=asset.asset_id,
            name=asset.name,
            category=asset.category,
            criticality_score=profile.score,
            criticality_band=profile.band.value,
            internet_exposed=asset.internet_exposed,
            regulatory_scope=service.regulatory_scope if service else None,
        )
    return contexts


def _findings_by_asset(
    snapshot: SeedSnapshot, vulnerabilities: dict[str, VulnerabilityRecord]
) -> dict[str, list[FindingContext]]:
    grouped: dict[str, list[FindingContext]] = {}
    for finding in snapshot.findings:
        record = vulnerabilities.get(finding.cve_id) if finding.cve_id else None
        grouped.setdefault(finding.asset_id, []).append(
            FindingContext(
                cve_id=finding.cve_id,
                cvss_base_score=record.cvss.base_score if record and record.cvss else None,
                cvss_severity=record.cvss.severity if record and record.cvss else None,
                epss=record.epss if record else None,
                kev=record.kev if record else False,
                kev_ransomware=record.kev_ransomware if record else False,
            )
        )
    return grouped


def load_planning_context(
    snapshot_path: str | Path | None = None,
    *,
    store: VulnerabilityStore | None = None,
) -> PlanningContext:
    snapshot = load_snapshot() if snapshot_path is None else load_snapshot(snapshot_path)
    vulnerability_store = store or VulnerabilityStore()
    vulnerabilities = vulnerability_store.load() if vulnerability_store.path.exists() else {}

    assets = _asset_context(snapshot)
    findings_by_asset = _findings_by_asset(snapshot, vulnerabilities)

    catalogue: dict[str, ScenarioCatalogueEntry] = {}
    specs: dict[str, ScenarioSpec] = {}
    scenarios: dict[str, CompiledScenario] = {}

    for scenario in snapshot.scenarios:
        entry = ScenarioCatalogueEntry(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            asset_id=scenario.asset_id,
            service_id=scenario.service_id,
            category=scenario.category,
            attack_techniques=tuple(scenario.attack_techniques),
            cve_ids=tuple(scenario.cve_ids),
        )
        catalogue[scenario.id] = entry

        if scenario.asset_id is None or scenario.asset_id not in assets:
            continue
        spec = materialize_scenario(
            scenario_id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            asset=assets[scenario.asset_id],
            findings=findings_by_asset.get(scenario.asset_id, []),
            currency=snapshot.organization.currency,
            attack_techniques=entry.attack_techniques,
            cve_ids=entry.cve_ids,
        )
        specs[scenario.id] = spec
        scenarios[scenario.id] = spec.compile()

    controls: dict[str, ControlContext] = {}
    for control in snapshot.controls:
        evidence = control.evidence
        effectiveness = ControlEvidenceScore(
            coverage=evidence.coverage,
            configuration_strength=evidence.configuration_strength,
            policy_compliance=evidence.policy_compliance,
            recent_incident_signal=evidence.recent_incident_signal,
            verification_age_days=evidence.verification_age_days,
        ).effectiveness()
        protects = tuple(
            scenario_id
            for scenario_id, entry in catalogue.items()
            if entry.asset_id in set(control.applies_to_assets)
        )
        controls[control.control_id] = ControlContext(
            control_id=control.control_id,
            name=control.name,
            category=ControlCategory(control.category),
            effectiveness=effectiveness,
            cost=float(control.cost or 0.0),
            protects=protects,
            evidence=evidence.model_dump(),
        )

    return PlanningContext(
        organization_name=snapshot.organization.name,
        currency=snapshot.organization.currency,
        assets=assets,
        scenarios=scenarios,
        specs=specs,
        catalogue=catalogue,
        controls=controls,
        vulnerabilities=vulnerabilities,
        findings_by_asset=findings_by_asset,
    )
