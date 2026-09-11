"""Read-only catalog endpoints: the organization, its assets, findings, controls and scenarios.

Every payload is derived from the same planning context the risk engine uses, so what the UI
displays is exactly what was modelled.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import EngineDep
from app.api.schemas import (
    AssetDetail,
    AssetSummary,
    CandidateModel,
    ControlFactorModel,
    ControlSummary,
    CriticalityModel,
    EvidenceMixModel,
    FindingSummary,
    OrganizationModel,
    OverviewResponse,
    PostureModel,
    ScenarioSpecResponse,
    ScenarioSummary,
)
from app.engine import BASELINE_LABEL
from app.optimization.context import ScenarioCatalogueEntry
from app.risk.asset_criticality import profile_from_asset
from app.risk.control_effect import factor_effect
from app.risk.provenance import MODEL_VERSION, EvidenceMix

router = APIRouter(tags=["catalog"])


def _criticality(criticality: dict[str, int]) -> CriticalityModel:
    return CriticalityModel(**profile_from_asset(criticality).to_dict())


def _finding_summary(engine, finding, asset_names: dict[str, str]) -> FindingSummary:
    record = engine.context.vulnerabilities.get(finding.cve_id) if finding.cve_id else None
    cvss = record.cvss if record else None
    return FindingSummary(
        finding_id=finding.finding_id,
        asset_id=finding.asset_id,
        asset_name=asset_names.get(finding.asset_id, finding.asset_id),
        cve_id=finding.cve_id,
        title=finding.title,
        source=finding.source,
        raw_severity=finding.raw_severity,
        status=finding.status,
        cvss_base_score=cvss.base_score if cvss else None,
        cvss_severity=cvss.severity if cvss else None,
        epss=record.epss if record else None,
        kev=record.kev if record else False,
        kev_ransomware=record.kev_ransomware if record else False,
    )


def _scenario_summary(
    engine, entry: ScenarioCatalogueEntry, exposure: dict | None = None
) -> ScenarioSummary:
    asset = engine.context.assets.get(entry.asset_id) if entry.asset_id else None
    current = (exposure or {}).get(entry.id)
    return ScenarioSummary(
        id=entry.id,
        name=entry.name,
        description=entry.description,
        asset_id=entry.asset_id,
        asset_name=asset.name if asset else None,
        service_id=entry.service_id,
        category=entry.category,
        cve_ids=list(entry.cve_ids),
        attack_techniques=list(entry.attack_techniques),
        max_cvss=engine.context.scenario_cvss(entry.id),
        max_epss=engine.context.scenario_epss(entry.id),
        baseline_eal=current.eal if current else None,
        baseline_p90=current.p90 if current else None,
        baseline_p95=current.p95 if current else None,
    )


def _asset_summary(engine, seed_asset, services: dict, units: dict) -> AssetSummary:
    service = services.get(seed_asset.service_id) if seed_asset.service_id else None
    unit = units.get(service.business_unit_id) if service else None
    findings = engine.context.findings_by_asset.get(seed_asset.asset_id, [])
    return AssetSummary(
        asset_id=seed_asset.asset_id,
        name=seed_asset.name,
        category=seed_asset.category,
        service_id=seed_asset.service_id,
        service_name=service.name if service else None,
        business_unit=unit.name if unit else None,
        owner=seed_asset.owner,
        internet_exposed=seed_asset.internet_exposed,
        criticality=_criticality(seed_asset.criticality),
        finding_count=len(findings),
        scenario_count=len(engine.context.scenarios_for_asset(seed_asset.asset_id)),
        tags=list(seed_asset.tags),
    )


@router.get("/overview", response_model=OverviewResponse)
def overview(engine: EngineDep) -> OverviewResponse:
    """Organization header: posture, counts, criticality mix and evidence confidence."""
    snapshot = engine.snapshot
    baseline = engine.baseline()

    bands: dict[str, int] = {}
    for seed_asset in snapshot.assets:
        band = profile_from_asset(seed_asset.criticality).band.value
        bands[band] = bands.get(band, 0) + 1

    mix = EvidenceMix.from_provenances(
        [p for spec in engine.context.specs.values() for p in spec.provenances()]
    )

    counts = {
        "business_units": len(snapshot.business_units),
        "services": len(snapshot.services),
        "assets": len(snapshot.assets),
        "findings": len(snapshot.findings),
        "controls": len(snapshot.controls),
        "scenarios_total": len(snapshot.scenarios),
        "scenarios_modelled": len(engine.context.scenarios),
        "candidates": len(engine.candidates),
        "vulnerabilities_enriched": len(engine.context.vulnerabilities),
    }

    return OverviewResponse(
        organization=OrganizationModel(**snapshot.organization.model_dump()),
        counts=counts,
        criticality_bands=bands,
        posture=PostureModel(
            baseline_eal=baseline.eal,
            p90=baseline.p90,
            p95=baseline.p95,
            currency=baseline.currency,
            n_scenarios=baseline.n_scenarios,
            n_trials=baseline.n_trials,
            seed=baseline.seed,
        ),
        evidence_mix=EvidenceMixModel(**mix.to_dict()),
        model_version=MODEL_VERSION,
    )


@router.get("/assets", response_model=list[AssetSummary])
def list_assets(engine: EngineDep) -> list[AssetSummary]:
    snapshot = engine.snapshot
    services = {service.id: service for service in snapshot.services}
    units = {unit.id: unit for unit in snapshot.business_units}
    return [
        _asset_summary(engine, asset, services, units)
        for asset in sorted(snapshot.assets, key=lambda a: a.name)
    ]


@router.get("/assets/{asset_id}", response_model=AssetDetail)
def get_asset(asset_id: str, engine: EngineDep) -> AssetDetail:
    snapshot = engine.snapshot
    seed_asset = next((a for a in snapshot.assets if a.asset_id == asset_id), None)
    if seed_asset is None:
        raise HTTPException(status_code=404, detail=f"unknown asset: {asset_id}")

    services = {service.id: service for service in snapshot.services}
    units = {unit.id: unit for unit in snapshot.business_units}
    asset_names = {a.asset_id: a.name for a in snapshot.assets}

    findings = [
        _finding_summary(engine, finding, asset_names)
        for finding in snapshot.findings
        if finding.asset_id == asset_id
    ]
    exposures = engine.baseline_scenario_exposure()
    scenarios = [
        _scenario_summary(engine, entry, exposures)
        for scenario_id in engine.context.scenarios_for_asset(asset_id)
        if (entry := engine.context.catalogue.get(scenario_id)) is not None
    ]

    return AssetDetail(
        asset=_asset_summary(engine, seed_asset, services, units),
        findings=findings,
        scenarios=scenarios,
    )


@router.get("/findings", response_model=list[FindingSummary])
def list_findings(engine: EngineDep) -> list[FindingSummary]:
    snapshot = engine.snapshot
    asset_names = {a.asset_id: a.name for a in snapshot.assets}
    return [_finding_summary(engine, finding, asset_names) for finding in snapshot.findings]


@router.get("/controls", response_model=list[ControlSummary])
def list_controls(engine: EngineDep) -> list[ControlSummary]:
    rows: list[ControlSummary] = []
    for control in engine.context.controls.values():
        effect = factor_effect(control.category, control.effectiveness)
        rows.append(
            ControlSummary(
                control_id=control.control_id,
                name=control.name,
                category=control.category.value,
                effectiveness=round(control.effectiveness, 4),
                cost=control.cost,
                evidence=control.evidence,
                protects=list(control.protects),
                factor=ControlFactorModel(
                    factor=effect.factor.value,
                    multiplier=effect.multiplier,
                    shift=effect.shift,
                    description=effect.describe(),
                ),
            )
        )
    return sorted(rows, key=lambda row: row.control_id)


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios(engine: EngineDep) -> list[ScenarioSummary]:
    """Every modelled scenario with its current-posture exposure, ranked by EAL."""
    exposure = engine.baseline_scenario_exposure()
    rows = [
        _scenario_summary(engine, entry, exposure) for entry in engine.context.catalogue.values()
    ]
    return sorted(rows, key=lambda row: row.baseline_eal or 0.0, reverse=True)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioSpecResponse)
def get_scenario(scenario_id: str, engine: EngineDep) -> ScenarioSpecResponse:
    spec = engine.context.specs.get(scenario_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"scenario not modelled: {scenario_id}")
    return ScenarioSpecResponse(**spec.model_dump(mode="json"))


@router.get("/candidates", response_model=list[CandidateModel])
def list_candidates(engine: EngineDep) -> list[CandidateModel]:
    return [CandidateModel(**candidate.to_dict()) for candidate in engine.candidates]


@router.get("/baseline", response_model=dict)
def baseline(engine: EngineDep) -> dict:
    """Current-posture aggregate outcome (no controls applied)."""
    return engine.baseline().to_dict()


__all__ = ["BASELINE_LABEL", "router"]
