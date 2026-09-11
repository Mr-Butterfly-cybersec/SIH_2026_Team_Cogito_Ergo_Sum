"""Scenario factory: catalogue → full FAIR specification."""

from __future__ import annotations

from app.risk.monte_carlo import SimulationConfig, run_simulation
from app.risk.scenario_factory import (
    AssetContext,
    ExploitationEvidence,
    FindingContext,
    contact_frequency,
    gather_evidence,
    materialize_scenario,
    probability_of_action,
    resistance_strength,
    threat_capability,
)


def _asset(**overrides: object) -> AssetContext:
    base = {
        "asset_id": "AST-TEST-01",
        "name": "Test asset",
        "category": "internet_facing",
        "criticality_score": 3.0,
        "criticality_band": "HIGH",
        "internet_exposed": True,
        "regulatory_scope": "Student PII",
    }
    return AssetContext(**{**base, **overrides})  # type: ignore[arg-type]


def _spec(asset: AssetContext | None = None, findings: list[FindingContext] | None = None):
    return materialize_scenario(
        scenario_id="SCN-TEST-01",
        name="Test scenario",
        description="unit test scenario",
        asset=asset or _asset(),
        findings=findings
        if findings is not None
        else [FindingContext(cvss_base_score=9.8, epss=0.9, kev=True)],
        cve_ids=["CVE-2021-44228"],
        attack_techniques=["T1190"],
    )


def test_gather_evidence_takes_the_worst_case() -> None:
    evidence = gather_evidence(
        [
            FindingContext(cvss_base_score=7.0, epss=0.2, kev=False),
            FindingContext(cvss_base_score=9.8, epss=0.9, kev=True, kev_ransomware=True),
        ]
    )
    assert evidence.max_cvss == 9.8
    assert evidence.max_epss == 0.9
    assert evidence.any_kev is True
    assert evidence.any_ransomware is True
    assert evidence.cve_count == 2


def test_probability_of_action_rises_with_exploitation_evidence() -> None:
    quiet = probability_of_action(ExploitationEvidence(None, None, False, False, 0))
    loud = probability_of_action(ExploitationEvidence(10.0, 0.95, True, True, 3))
    assert loud.distribution.mode > quiet.distribution.mode


def test_threat_capability_tracks_highest_cvss() -> None:
    low = threat_capability(ExploitationEvidence(4.0, None, False, False, 1))
    high = threat_capability(ExploitationEvidence(10.0, None, False, False, 1))
    assert high.distribution.mode > low.distribution.mode


def test_contact_frequency_follows_exposure_class() -> None:
    internal = contact_frequency(_asset(category="internal", internet_exposed=False))
    cloud = contact_frequency(_asset(category="cloud", internet_exposed=False))
    exposed = contact_frequency(_asset(category="internet_facing"))
    assert exposed.distribution.mode > cloud.distribution.mode > internal.distribution.mode


def test_resistance_strength_is_inherent_not_control_dependent() -> None:
    strong = resistance_strength(_asset(category="internal"))
    weak = resistance_strength(_asset(category="internet_facing"))
    assert strong.distribution.mode > weak.distribution.mode
    assert 0.0 <= weak.distribution.minimum <= weak.distribution.maximum <= 100.0


def test_materialized_scenario_is_valid_and_provenanced() -> None:
    spec = _spec()
    assert spec.id == "SCN-TEST-01"
    assert spec.cve_ids == ["CVE-2021-44228"]
    assert spec.attack_techniques == ["T1190"]

    compiled = spec.compile()
    assert compiled.frequency.contact_frequency.mean > 0

    provenances = spec.provenances()
    # 4 frequency + 5 primary + 4 secondary + 1 secondary-frequency
    assert len(provenances) == 14

    primary_sources = {p.provenance.source_type.value for p in spec.magnitude.primary.values()}
    assert primary_sources == {"SYNTHETIC_DEMO"}
    frequency_sources = {p.provenance.source_type.value for p in spec.frequency.iter_parameters()}
    assert "MODEL_ESTIMATE" in frequency_sources


def test_higher_criticality_increases_loss_and_is_monotonic() -> None:
    low = _spec(_asset(criticality_score=2.0))
    high = _spec(_asset(criticality_score=5.0))
    assert (
        high.magnitude.primary["downtime"].distribution.mode
        > low.magnitude.primary["downtime"].distribution.mode
    )
    assert (
        high.magnitude.secondary["reputational"].distribution.mode
        > low.magnitude.secondary["reputational"].distribution.mode
    )


def test_secondary_loss_propensity_is_a_probability() -> None:
    spec = _spec()
    slef = spec.magnitude.secondary_loss_event_frequency.distribution
    assert 0.0 <= slef.minimum <= slef.mode <= slef.maximum <= 1.0


def test_materialized_scenario_simulates() -> None:
    result = run_simulation(_spec().compile(), SimulationConfig(n_trials=2_000, seed=7))
    assert result.summary.eal > 0
    assert result.evidence_mix.total == 14
