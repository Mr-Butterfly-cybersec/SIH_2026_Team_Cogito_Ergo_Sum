"""Demo organization snapshot and seeding."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.risk.asset_criticality import profile_from_asset
from app.seed.org_demo import load_snapshot, seed


def test_snapshot_shape() -> None:
    snapshot = load_snapshot()
    assert snapshot.organization.id == "ORG-VIT-01"
    assert len(snapshot.business_units) == 3
    assert len(snapshot.services) == 8
    assert len(snapshot.assets) == 33
    assert len(snapshot.controls) == 11
    assert len(snapshot.findings) == 24
    assert len(snapshot.scenarios) == 8


def test_snapshot_size_is_within_the_demo_target() -> None:
    snapshot = load_snapshot()
    assert 25 <= len(snapshot.assets) <= 50
    assert 8 <= len(snapshot.controls) <= 12
    assert 6 <= len(snapshot.scenarios) <= 10


def test_every_asset_has_an_in_range_criticality_score() -> None:
    for asset in load_snapshot().assets:
        profile = profile_from_asset(asset.criticality)
        assert 1.0 <= profile.score <= 5.0
        assert profile.band.value in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_the_same_cve_appears_on_several_assets() -> None:
    assets_by_cve: dict[str, set[str]] = {}
    for finding in load_snapshot().findings:
        if finding.cve_id:
            assets_by_cve.setdefault(finding.cve_id, set()).add(finding.asset_id)
    assert len(assets_by_cve["CVE-2021-44228"]) >= 3
    assert len(assets_by_cve) == 18


async def test_seed_persists_the_whole_snapshot(db_session: AsyncSession) -> None:
    snapshot = load_snapshot()
    counts = await seed(db_session, snapshot)
    await db_session.commit()

    assert counts["assets"] == 33
    assert counts["controls"] == 11
    assert counts["scenarios"] == 8
    assert counts["specified_scenarios"] == 1

    async def count(model) -> int:
        return (await db_session.execute(select(func.count()).select_from(model))).scalar_one()

    assert await count(Organization) == 1
    assert await count(BusinessUnit) == 3
    assert await count(Service) == 8
    assert await count(Asset) == 33
    assert await count(Control) == 11
    assert await count(ControlEvidence) == 11
    assert await count(Finding) == 24
    assert await count(Scenario) == 8
    assert await count(Vulnerability) == 18

    controls = (await db_session.execute(select(Control))).scalars().all()
    assert all(0.0 <= (c.effectiveness or 0.0) <= 1.0 for c in controls)
    assert {c.factor for c in controls} <= {
        "contact_frequency",
        "probability_of_action",
        "resistance_strength",
        "loss_magnitude",
    }

    scenarios = (await db_session.execute(select(Scenario))).scalars().all()
    specified = [s for s in scenarios if s.status == "specified"]
    assert len(specified) == 1
    assert specified[0].id == "SCN-RANSOM-01"
    assert specified[0].spec is not None
    assert specified[0].spec["frequency"]["contact_frequency"] is not None


async def test_reseed_is_idempotent(db_session: AsyncSession) -> None:
    snapshot = load_snapshot()
    await seed(db_session, snapshot)
    await db_session.commit()
    await seed(db_session, snapshot)
    await db_session.commit()

    total = (await db_session.execute(select(func.count()).select_from(Asset))).scalar_one()
    assert total == 33
    evidence = (
        await db_session.execute(select(func.count()).select_from(ControlEvidence))
    ).scalar_one()
    assert evidence == 11
