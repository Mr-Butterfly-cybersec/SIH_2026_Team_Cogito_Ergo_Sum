"""Load the demo organization into the database.

    uv run python -m app.seed.org_demo
    uv run python -m app.seed.org_demo --database-url sqlite+aiosqlite:///./demo.db

Reseeding is destructive by design: the seeded tables are cleared and rewritten so the
demo environment is always reproducible.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.ingestion.models import VulnerabilityRecord
from app.ingestion.store import VulnerabilityStore
from app.models import (
    Asset,
    Base,
    BusinessUnit,
    Control,
    ControlEvidence,
    Finding,
    Organization,
    Scenario,
    Service,
    Vulnerability,
)
from app.normalization.vulnerabilities import empty_record
from app.risk.asset_criticality import profile_from_asset
from app.risk.control_effect import ControlCategory, factor_effect
from app.risk.control_effect import ControlEvidence as ControlEvidenceScore
from app.seed.schema import SeedSnapshot

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = Path(__file__).parent / "data" / "org_demo.json"
RANSOMWARE_SPEC = BACKEND_DIR / "app" / "risk" / "examples" / "ransomware.json"

# Children before parents, so deletes never violate a foreign key.
_RESET_ORDER = (
    ControlEvidence,
    Control,
    Finding,
    Scenario,
    Vulnerability,
    Asset,
    Service,
    BusinessUnit,
    Organization,
)


def load_snapshot(path: str | Path = DATA_FILE) -> SeedSnapshot:
    snapshot = SeedSnapshot.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
    snapshot.validate_references()
    return snapshot


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def reset(session: AsyncSession) -> None:
    for model in _RESET_ORDER:
        await session.execute(delete(model))
    # Drop stale identities so a re-seed can insert rows with the same primary keys.
    session.expunge_all()


def _vulnerability_row(record: VulnerabilityRecord) -> Vulnerability:
    cvss = record.cvss
    return Vulnerability(
        cve_id=record.cve_id,
        description=record.description,
        published=record.published,
        last_modified=record.last_modified,
        status=record.status,
        cvss_version=cvss.version if cvss else None,
        cvss_base_score=cvss.base_score if cvss else None,
        cvss_severity=cvss.severity if cvss else None,
        cvss_vector=cvss.vector if cvss else None,
        cwes=record.cwes,
        affected_cpe=record.affected_cpe,
        epss=record.epss,
        epss_percentile=record.epss_percentile,
        epss_date=record.epss_date,
        kev=record.kev,
        kev_date_added=record.kev_date_added,
        kev_due_date=record.kev_due_date,
        kev_ransomware=record.kev_ransomware,
        kev_required_action=record.kev_required_action,
        attack_techniques=record.attack_techniques,
        references=record.references,
        sources=record.sources,
        provenance=[p.model_dump(mode="json") for p in record.provenance],
    )


def _vulnerability_rows(snapshot: SeedSnapshot) -> list[Vulnerability]:
    store = VulnerabilityStore()
    known = store.load() if store.path.exists() else {}
    needed: list[str] = []
    for finding in snapshot.findings:
        if finding.cve_id and finding.cve_id not in needed:
            needed.append(finding.cve_id)

    rows: list[Vulnerability] = []
    for cve_id in needed:
        record = known.get(cve_id) or empty_record(cve_id)
        rows.append(_vulnerability_row(record))
    return rows


async def seed(session: AsyncSession, snapshot: SeedSnapshot) -> dict[str, int]:
    await reset(session)

    organization = snapshot.organization
    session.add(
        Organization(
            id=organization.id,
            name=organization.name,
            sector=organization.sector,
            currency=organization.currency,
            description=organization.description,
            framework_scope=organization.framework_scope,
        )
    )
    session.add_all(
        [
            BusinessUnit(
                id=unit.id,
                organization_id=organization.id,
                name=unit.name,
                criticality=unit.criticality,
                description=unit.description,
            )
            for unit in snapshot.business_units
        ]
    )
    session.add_all(
        [
            Service(
                id=service.id,
                business_unit_id=service.business_unit_id,
                name=service.name,
                revenue_dependency=service.revenue_dependency,
                regulatory_scope=service.regulatory_scope,
                description=service.description,
            )
            for service in snapshot.services
        ]
    )

    assets = []
    for asset in snapshot.assets:
        profile = profile_from_asset(asset.criticality)
        assets.append(
            Asset(
                id=asset.asset_id,
                service_id=asset.service_id,
                name=asset.name,
                category=asset.category,
                owner=asset.owner,
                internet_exposed=asset.internet_exposed,
                rto_hours=asset.rto_hours,
                criticality=profile.as_dict(),
                criticality_score=profile.score,
                criticality_band=profile.band.value,
                tags=asset.tags,
            )
        )
    session.add_all(assets)
    # Flush in dependency order: Scenario/Control rows carry foreign keys but no ORM
    # relationship, so the unit of work cannot infer the ordering on its own.
    await session.flush()

    for control in snapshot.controls:
        evidence = control.evidence
        score = ControlEvidenceScore(
            coverage=evidence.coverage,
            configuration_strength=evidence.configuration_strength,
            policy_compliance=evidence.policy_compliance,
            recent_incident_signal=evidence.recent_incident_signal,
            verification_age_days=evidence.verification_age_days,
        )
        effectiveness = score.effectiveness()
        effect = factor_effect(ControlCategory(control.category), effectiveness)
        session.add(
            Control(
                id=control.control_id,
                name=control.name,
                category=ControlCategory(control.category).value,
                factor=effect.factor.value,
                effectiveness=effectiveness,
                applies_to_assets=control.applies_to_assets,
                cost=control.cost,
                notes=control.notes,
                provenance=[
                    {
                        "source_type": "OBSERVED_TELEMETRY",
                        "source": "demo control assessment",
                        "confidence": 0.5,
                        "assumption_description": "Synthetic control evidence (demo).",
                    }
                ],
            )
        )
        session.add(
            ControlEvidence(
                control_id=control.control_id,
                coverage=evidence.coverage,
                configuration_strength=evidence.configuration_strength,
                policy_compliance=evidence.policy_compliance,
                recent_incident_signal=evidence.recent_incident_signal,
                verification_age_days=evidence.verification_age_days,
            )
        )

    await session.flush()

    vulnerabilities = _vulnerability_rows(snapshot)
    session.add_all(vulnerabilities)
    await session.flush()
    known_cves = {row.cve_id for row in vulnerabilities}

    session.add_all(
        [
            Finding(
                id=finding.finding_id,
                asset_id=finding.asset_id,
                cve_id=finding.cve_id if finding.cve_id in known_cves else None,
                title=finding.title,
                source=finding.source,
                raw_severity=finding.raw_severity,
                status=finding.status,
                detected_at=finding.detected_at,
            )
            for finding in snapshot.findings
        ]
    )
    await session.flush()

    spec = (
        json.loads(RANSOMWARE_SPEC.read_text(encoding="utf-8"))
        if RANSOMWARE_SPEC.exists()
        else None
    )
    scenarios = []
    for scenario in snapshot.scenarios:
        has_spec = spec is not None and spec.get("id") == scenario.id
        scenarios.append(
            Scenario(
                id=scenario.id,
                name=scenario.name,
                description=scenario.description,
                asset_id=scenario.asset_id,
                service_id=scenario.service_id,
                category=scenario.category,
                status="specified" if has_spec else "catalogue",
                attack_techniques=scenario.attack_techniques,
                cve_ids=scenario.cve_ids,
                spec=spec if has_spec else None,
            )
        )
    session.add_all(scenarios)

    await session.flush()
    return {
        "business_units": len(snapshot.business_units),
        "services": len(snapshot.services),
        "assets": len(snapshot.assets),
        "controls": len(snapshot.controls),
        "vulnerabilities": len(vulnerabilities),
        "findings": len(snapshot.findings),
        "scenarios": len(snapshot.scenarios),
        "specified_scenarios": sum(1 for s in scenarios if s.status == "specified"),
    }


async def run(
    database_url: str | None = None,
) -> tuple[dict[str, int], SeedSnapshot, list[tuple[str, float]]]:
    engine = create_async_engine(database_url or get_settings().database_url)
    try:
        await create_schema(engine)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        snapshot = load_snapshot()
        async with session_factory() as session:
            counts = await seed(session, snapshot)
            await session.commit()
            rows = (
                await session.execute(
                    select(Control.name, Control.effectiveness).order_by(Control.effectiveness)
                )
            ).all()
        return counts, snapshot, [(name, value or 0.0) for name, value in rows]
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load the demo organization into the database.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--snapshot", type=Path, default=DATA_FILE)
    args = parser.parse_args(argv)

    counts, snapshot, controls = asyncio.run(run(args.database_url))

    print(f"\nSeeded: {snapshot.organization.name}")
    print("-" * 52)
    for key, value in counts.items():
        print(f"  {key:<22} {value:>6}")
    print("-" * 52)
    print("  control effectiveness (lowest first)")
    for name, effectiveness in controls:
        print(f"    {name[:44]:<46} {effectiveness:.3f}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
