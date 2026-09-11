"""ORM models: hierarchy, JSON columns, and relationships (on SQLite)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Asset,
    BusinessUnit,
    Control,
    ControlEvidence,
    Finding,
    Organization,
    Scenario,
    Service,
    Vulnerability,
)


async def test_hierarchy_and_json_roundtrip(db_session: AsyncSession) -> None:
    db_session.add(Organization(id="O1", name="Org", framework_scope=["NIST CSF 2.0"]))
    db_session.add(BusinessUnit(id="B1", organization_id="O1", name="Academic", criticality=5))
    db_session.add(Service(id="S1", business_unit_id="B1", name="Admissions"))
    db_session.add(
        Asset(
            id="A1",
            service_id="S1",
            name="Admissions portal",
            category="internet_facing",
            internet_exposed=True,
            criticality={"availability": 5, "internet_exposure": 5},
            criticality_score=4.6,
            criticality_band="CRITICAL",
            tags=["public", "pii"],
        )
    )
    db_session.add(
        Vulnerability(
            cve_id="CVE-2021-44228",
            cvss_base_score=10.0,
            cvss_severity="CRITICAL",
            kev=True,
            cwes=["CWE-502"],
            sources=["NVD", "EPSS", "CISA-KEV"],
        )
    )
    await db_session.flush()
    db_session.add(
        Finding(id="F1", asset_id="A1", cve_id="CVE-2021-44228", source="vulnerability_mgmt")
    )
    await db_session.commit()

    asset = (
        await db_session.execute(
            select(Asset).options(selectinload(Asset.findings)).where(Asset.id == "A1")
        )
    ).scalar_one()
    assert asset.criticality == {"availability": 5, "internet_exposure": 5}
    assert asset.tags == ["public", "pii"]
    assert asset.internet_exposed is True
    assert [f.id for f in asset.findings] == ["F1"]

    vulnerability = (
        await db_session.execute(
            select(Vulnerability).where(Vulnerability.cve_id == "CVE-2021-44228")
        )
    ).scalar_one()
    assert vulnerability.cwes == ["CWE-502"]
    assert vulnerability.sources == ["NVD", "EPSS", "CISA-KEV"]
    assert vulnerability.kev is True


async def test_control_evidence_relationship(db_session: AsyncSession) -> None:
    db_session.add(
        Control(
            id="CTL-MFA",
            name="MFA for privileged identities",
            category="resistive",
            factor="resistance_strength",
            effectiveness=0.42,
            applies_to_assets=["A1"],
        )
    )
    db_session.add(
        ControlEvidence(
            control_id="CTL-MFA",
            coverage=0.35,
            configuration_strength=0.7,
            policy_compliance=0.8,
            recent_incident_signal=0.4,
            verification_age_days=120,
        )
    )
    await db_session.commit()

    control = (
        await db_session.execute(
            select(Control).options(selectinload(Control.evidence)).where(Control.id == "CTL-MFA")
        )
    ).scalar_one()
    assert control.evidence is not None
    assert control.evidence.coverage == 0.35
    assert control.applies_to_assets == ["A1"]


async def test_scenario_spec_is_nullable(db_session: AsyncSession) -> None:
    db_session.add(Scenario(id="SCN-1", name="Catalogue only", status="catalogue"))
    db_session.add(Scenario(id="SCN-2", name="Specified", status="specified", spec={"id": "SCN-2"}))
    await db_session.commit()

    total = (await db_session.execute(select(func.count()).select_from(Scenario))).scalar_one()
    assert total == 2
    specified = (
        await db_session.execute(select(Scenario).where(Scenario.id == "SCN-2"))
    ).scalar_one()
    assert specified.spec == {"id": "SCN-2"}
