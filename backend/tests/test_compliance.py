"""Compliance mapping tests: catalog integrity, coverage math, and the API."""

from __future__ import annotations

import pytest

from app.compliance import (
    CONTROL_REQUIREMENTS,
    FRAMEWORKS,
    FRAMEWORKS_BY_ID,
    REQUIREMENTS,
    REQUIREMENTS_BY_ID,
    build_report,
    combined_coverage,
    controls_for_requirement,
    requirements_for_control,
    requirements_for_framework,
    status_for,
)
from app.compliance.coverage import CoverageStatus
from app.engine import ScenarioEngine
from app.optimization.context import load_planning_context
from app.risk.control_effect import ControlCategory

TRIALS = 500


@pytest.fixture(scope="module")
def engine() -> ScenarioEngine:
    return ScenarioEngine(load_planning_context())


@pytest.fixture(scope="module")
def report(engine: ScenarioEngine):
    exposure = {s.scenario_id: s.eal for s in engine.baseline(TRIALS).scenarios}
    return build_report(engine.context, exposure)


# --- catalog integrity ------------------------------------------------------------------
def test_requirement_ids_are_unique() -> None:
    ids = [requirement.id for requirement in REQUIREMENTS]
    assert len(ids) == len(set(ids))


def test_every_reference_targets_a_known_framework() -> None:
    for requirement in REQUIREMENTS:
        unknown = set(requirement.references) - set(FRAMEWORKS_BY_ID)
        assert not unknown, f"{requirement.id}: unknown frameworks {sorted(unknown)}"


def test_every_requirement_has_at_least_one_reference() -> None:
    for requirement in REQUIREMENTS:
        assert requirement.reference_for(FRAMEWORKS[0].id) or requirement.references, (
            f"{requirement.id} has no framework references"
        )
        assert sum(len(v) for v in requirement.references.values()) > 0


def test_categories_are_valid_fair_categories() -> None:
    for requirement in REQUIREMENTS:
        for category in requirement.categories:
            assert isinstance(category, ControlCategory)


def test_every_requirement_reference_clause_is_non_empty() -> None:
    for requirement in REQUIREMENTS:
        for framework_id, clauses in requirement.references.items():
            assert clauses, f"{requirement.id}/{framework_id} has an empty clause list"
            assert all(clause.strip() for clause in clauses)


def test_framework_registry_is_versioned_and_sourced() -> None:
    for framework in FRAMEWORKS:
        assert framework.version
        assert framework.publisher
        assert framework.source_url.startswith("https://")
        assert framework.published.year >= 2022


def test_frameworks_are_not_uniform() -> None:
    """Frameworks have genuinely different scope — guard against a fake crosswalk.

    CIS v8.1 is operational and deliberately omits governance, privacy and continuity
    requirements, so it must reference fewer requirements than NIST CSF 2.0.
    """
    cis = len(requirements_for_framework("cis_v8"))
    nist = len(requirements_for_framework("nist_csf"))
    assert cis < nist


# --- mapping ----------------------------------------------------------------------------
def test_control_mapping_targets_real_requirements() -> None:
    for control_id, requirement_ids in CONTROL_REQUIREMENTS.items():
        for requirement_id in requirement_ids:
            assert requirement_id in REQUIREMENTS_BY_ID, f"{control_id} -> {requirement_id}"


def test_reverse_index_is_consistent() -> None:
    for control_id, requirement_ids in CONTROL_REQUIREMENTS.items():
        for requirement_id in requirement_ids:
            assert control_id in controls_for_requirement(requirement_id)
    for requirement_id in REQUIREMENTS_BY_ID:
        for control_id in controls_for_requirement(requirement_id):
            assert requirement_id in requirements_for_control(control_id)


def test_no_duplicate_mappings() -> None:
    for control_id, requirement_ids in CONTROL_REQUIREMENTS.items():
        assert len(requirement_ids) == len(set(requirement_ids)), f"{control_id} repeats"


# --- coverage math ----------------------------------------------------------------------
def test_combined_coverage_single_control() -> None:
    assert combined_coverage([0.5]) == pytest.approx(0.5)


def test_combined_coverage_rewards_a_second_control() -> None:
    assert combined_coverage([0.5, 0.5]) == pytest.approx(0.75)


def test_combined_coverage_is_bounded() -> None:
    assert combined_coverage([]) == 0.0
    assert combined_coverage([1.0, 1.0]) == pytest.approx(1.0)
    assert 0.0 <= combined_coverage([0.3, 0.4, 0.5]) <= 1.0


def test_status_thresholds() -> None:
    assert status_for(0.9, True) is CoverageStatus.COVERED
    assert status_for(0.5, True) is CoverageStatus.PARTIAL
    assert status_for(0.1, True) is CoverageStatus.GAP
    assert status_for(0.0, False) is CoverageStatus.GAP


# --- report -----------------------------------------------------------------------------
def test_report_covers_every_framework(report) -> None:
    assert len(report.frameworks) == len(FRAMEWORKS)
    assert {f.framework.id for f in report.frameworks} == {f.id for f in FRAMEWORKS}


def test_counts_add_up(report) -> None:
    for entry in report.frameworks:
        counts = entry.covered + entry.partial + entry.gaps
        assert counts == len(entry.requirements)


def test_overall_coverage_is_a_fraction(report) -> None:
    assert 0.0 <= report.overall_coverage <= 1.0
    for entry in report.frameworks:
        assert 0.0 <= entry.coverage <= 1.0


def test_top_gaps_are_ranked_by_exposure(report) -> None:
    exposures = [gap.exposure for gap in report.top_gaps]
    assert exposures == sorted(exposures, reverse=True)
    assert all(gap.status is not CoverageStatus.COVERED for gap in report.top_gaps)


def test_gaps_are_priced_in_rupees(report) -> None:
    priced = [gap for gap in report.top_gaps if gap.exposure > 0]
    assert priced, "at least one gap should carry modelled exposure"
    assert all(gap.scenarios for gap in priced)


def test_gaps_offer_a_way_to_close_them(report) -> None:
    for gap in report.top_gaps:
        if gap.contributions:
            assert gap.closable_by, f"{gap.requirement.id} has controls but no candidate"


def test_unmapped_requirements_expose_real_gaps(report) -> None:
    assert "REQ-PENTEST" in report.unmapped_requirements
    assert "REQ-AWARENESS" in report.unmapped_requirements
    for requirement_id in report.unmapped_requirements:
        assert requirement_id in REQUIREMENTS_BY_ID
        assert controls_for_requirement(requirement_id) == ()


def test_every_org_control_maps_into_the_ontology(engine: ScenarioEngine, report) -> None:
    """No control should exist without a compliance story."""
    assert report.unmapped_controls == ()
    for control_id in engine.context.controls:
        assert requirements_for_control(control_id)


def test_requirement_coverage_uses_real_effectiveness(engine: ScenarioEngine, report) -> None:
    """Coverage must come from measured control effectiveness, not a tick-box."""
    entry = next(f for f in report.frameworks if f.framework.id == "nist_csf")
    for row in entry.requirements:
        expected = combined_coverage([c.effectiveness for c in row.contributions])
        assert row.coverage == pytest.approx(expected)


def test_report_is_reproducible(engine: ScenarioEngine, report) -> None:
    again = engine.compliance_report(TRIALS, 42)
    assert again.overall_coverage == pytest.approx(report.overall_coverage)


# --- DPDP Act 2023 and ISO/IEC 42001 -----------------------------------------------------
def test_new_frameworks_are_registered_and_versioned() -> None:
    dpdp = FRAMEWORKS_BY_ID["dpdp_2023"]
    assert dpdp.is_regulation
    assert dpdp.version == "2023"
    assert dpdp.source_url.startswith("https://")

    aims = FRAMEWORKS_BY_ID["iso_42001"]
    assert not aims.is_regulation
    assert "42001" in aims.name
    assert aims.publisher == "ISO/IEC"


def test_dpdp_carries_its_own_statutory_obligations() -> None:
    """DPDP is a data-protection law, so it must not be an alias for ISO 27001."""
    dpdp_requirements = requirements_for_framework("dpdp_2023")
    dedicated = [r for r in dpdp_requirements if r.id.startswith("REQ-DPDP-")]
    assert len(dedicated) >= 6, "DPDP obligations should be modelled explicitly"

    names = {r.name for r in dedicated}
    for expected in (
        "Notice and lawful consent",
        "Data principal rights and grievance redressal",
        "Personal data breach notification",
        "Children's data and verifiable parental consent",
    ):
        assert expected in names


def test_ai_requirements_are_dedicated_to_iso_42001() -> None:
    """AI governance is new territory — the cyber frameworks above are silent on it."""
    ai_requirements = [r for r in REQUIREMENTS if r.id.startswith("REQ-AI-")]
    assert len(ai_requirements) >= 6

    for requirement in ai_requirements:
        assert requirement.reference_for("iso_42001"), (
            f"{requirement.id} must cite an ISO 42001 Annex A control"
        )
        assert not requirement.reference_for("cis_v8"), (
            f"{requirement.id}: CIS v8.1 is a cyber control set and does not cover AI management"
        )


def test_no_framework_is_a_superset_of_every_other() -> None:
    """Each framework must be genuinely scoped, or the crosswalk is decorative.

    Guards the whole point of the ontology: DPDP is narrower than NIST (data protection
    only), CIS is operational, and ISO 42001 covers AI where the others do not.
    """
    counts = {
        framework.id: len(requirements_for_framework(framework.id)) for framework in FRAMEWORKS
    }
    nist = counts["nist_csf"]
    assert counts["dpdp_2023"] < nist
    assert counts["cis_v8"] < nist

    # ISO 42001 must reference requirements that a purely operational cyber framework does
    # not reach — otherwise it adds no scope and the crosswalk is decorative.
    ai_only = [
        r for r in REQUIREMENTS if r.reference_for("iso_42001") and not r.reference_for("cis_v8")
    ]
    assert ai_only, "ISO 42001 must contribute scope CIS v8.1 lacks"


def test_estate_without_ai_systems_reports_ai_gaps_honestly(engine: ScenarioEngine) -> None:
    """No AI systems in scope means AI requirements are gaps — not silently 'covered'.

    This is the behaviour that makes the crosswalk trustworthy: an ontology reporting
    coverage for something the estate does not do is worse than no ontology.
    """
    report = engine.compliance_report(TRIALS, 42)
    aims = next(f for f in report.frameworks if f.framework.id == "iso_42001")

    decision = {row.requirement.id: row.status for row in aims.requirements}
    for requirement_id in (
        "REQ-AI-POLICY",
        "REQ-AI-IMPACT",
        "REQ-AI-TRANSPARENCY",
        "REQ-AI-LIFECYCLE",
    ):
        assert decision[requirement_id] is CoverageStatus.GAP, requirement_id
