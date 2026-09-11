"""Materialize the scenario catalogue into full FAIR specifications.

This bridges the declarative scenario catalogue (ids, assets, techniques, CVE links) to a
numeric model the Monte Carlo engine can simulate. Every derived parameter is
provenance-tagged, and all financial figures are explicitly ``SYNTHETIC_DEMO``.

Derivation rules (deterministic and visible):

    contact frequency     ← asset exposure class (internet-facing / cloud / internal)
    probability of action ← exploitation evidence attached to the scenario (KEV, EPSS)
    threat capability     ← highest CVSS among the scenario's CVEs
    resistance strength   ← *inherent* resistance only (no controls — controls are applied
                            by the evaluation harness, so baking them in would double-count)
    loss magnitudes       ← asset criticality score and internet exposure

The result is a defensible demonstration model, not a claim about any real organization.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.risk.provenance import SourceType
from app.risk.schemas import (
    FrequencyModelSpec,
    MagnitudeModelSpec,
    Parameter,
    PertSpec,
    ProvenanceModel,
    ScenarioSpec,
)

# --- exposure → contact frequency (events/year) -----------------------------------------
EXPOSURE_CONTACT_MODE: dict[str, float] = {
    "internet_facing": 8.0,
    "cloud": 4.0,
    "internal": 2.5,
}
DEFAULT_CONTACT_MODE = 3.0
CONTACT_MIN_FACTOR = 0.25
CONTACT_MAX_FACTOR = 4.0

# --- exploitation evidence → probability of action --------------------------------------
POA_BASE = 0.12
POA_KEV_BUMP = 0.30
POA_RANSOMWARE_BUMP = 0.10
POA_EPSS_WEIGHT = 0.35
POA_CEILING = 0.85

# --- highest CVSS → threat capability (percentile 0-100) --------------------------------
TCAP_FLOOR = 35.0
TCAP_CEILING = 96.0
TCAP_CVSS_SLOPE = 8.0  # CVSS 10 → 80th percentile before clamping/ceiling

# --- inherent resistance strength (percentile 0-100), before any control is applied ------
INHERENT_RESISTANCE_MODE: dict[str, float] = {
    "internet_facing": 22.0,
    "cloud": 30.0,
    "internal": 32.0,
}
DEFAULT_RESISTANCE_MODE = 28.0
RESISTANCE_LOW_SPAN = 12.0
RESISTANCE_HIGH_SPAN = 18.0

# --- loss magnitudes (INR, synthetic) ----------------------------------------------------
CRITICALITY_REFERENCE = 3.0
EXPOSURE_LOSS_FACTOR = 1.6
COMPONENT_MODES: dict[str, float] = {
    "incident_response": 350_000.0,
    "downtime": 300_000.0,
    "recovery": 200_000.0,
    "fraud_theft": 120_000.0,
    "data_restoration": 100_000.0,
    "notification_legal": 200_000.0,
    "regulatory": 250_000.0,
    "customer_impact": 150_000.0,
    "reputational": 250_000.0,
}
EXPOSURE_SCALED_COMPONENTS = ("downtime", "fraud_theft", "reputational")
LOSS_MIN_FACTOR = 0.4
LOSS_MAX_FACTOR = 3.0
REGULATORY_PRESENT_FACTOR = 1.4
REGULATORY_ABSENT_FACTOR = 0.6
SLEF_MIN, SLEF_MODE, SLEF_MAX = 0.10, 0.30, 0.60


@dataclass(frozen=True)
class AssetContext:
    asset_id: str
    name: str
    category: str
    criticality_score: float
    criticality_band: str
    internet_exposed: bool
    regulatory_scope: str | None = None


@dataclass(frozen=True)
class FindingContext:
    cve_id: str | None = None
    cvss_base_score: float | None = None
    cvss_severity: str | None = None
    epss: float | None = None
    kev: bool = False
    kev_ransomware: bool = False


@dataclass(frozen=True)
class ExploitationEvidence:
    max_cvss: float | None
    max_epss: float | None
    any_kev: bool
    any_ransomware: bool
    cve_count: int


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def gather_evidence(findings: Sequence[FindingContext]) -> ExploitationEvidence:
    cvss = [f.cvss_base_score for f in findings if f.cvss_base_score is not None]
    epss = [f.epss for f in findings if f.epss is not None]
    return ExploitationEvidence(
        max_cvss=max(cvss) if cvss else None,
        max_epss=max(epss) if epss else None,
        any_kev=any(f.kev for f in findings),
        any_ransomware=any(f.kev_ransomware for f in findings),
        cve_count=len(findings),
    )


def _money(value: float) -> float:
    return round(value, -3)


def _param(
    minimum: float,
    mode: float,
    maximum: float,
    *,
    source_type: SourceType,
    source: str,
    confidence: float,
    assumption: str,
) -> Parameter:
    low, mid, high = min(minimum, mode, maximum), mode, max(minimum, mode, maximum)
    return Parameter(
        distribution=PertSpec(minimum=low, mode=mid, maximum=high),
        provenance=ProvenanceModel(
            source_type=source_type,
            source=source,
            confidence=confidence,
            assumption_description=assumption,
        ),
    )


def contact_frequency(asset: AssetContext) -> Parameter:
    mode = EXPOSURE_CONTACT_MODE.get(asset.category, DEFAULT_CONTACT_MODE)
    if asset.category == "cloud" and asset.internet_exposed:
        mode = EXPOSURE_CONTACT_MODE["internet_facing"] * 0.75
    return _param(
        mode * CONTACT_MIN_FACTOR,
        mode,
        mode * CONTACT_MAX_FACTOR,
        source_type=SourceType.MODEL_ESTIMATE,
        source="scenario factory: exposure class",
        confidence=0.4,
        assumption=(
            f"Contact attempts per year derived from the '{asset.category}' exposure class"
            f"{' with internet exposure' if asset.internet_exposed else ''}."
        ),
    )


def probability_of_action(evidence: ExploitationEvidence) -> Parameter:
    mode = POA_BASE
    if evidence.any_kev:
        mode += POA_KEV_BUMP
    if evidence.any_ransomware:
        mode += POA_RANSOMWARE_BUMP
    if evidence.max_epss is not None:
        mode += POA_EPSS_WEIGHT * evidence.max_epss
    mode = _clamp(mode, 0.02, POA_CEILING)
    return _param(
        mode * 0.35,
        mode,
        min(0.95, mode * 2.0),
        source_type=SourceType.MODEL_ESTIMATE,
        source="scenario factory: exploitation evidence",
        confidence=0.45,
        assumption=(
            f"Probability the actor acts given contact; KEV={evidence.any_kev}, "
            f"max EPSS={evidence.max_epss if evidence.max_epss is not None else 'n/a'}."
        ),
    )


def threat_capability(evidence: ExploitationEvidence) -> Parameter:
    if evidence.max_cvss is None:
        mode = 50.0
        assumption = "No CVSS available; default capability percentile."
    else:
        mode = _clamp(evidence.max_cvss * TCAP_CVSS_SLOPE, TCAP_FLOOR, TCAP_CEILING)
        assumption = f"Percentile capability implied by highest attached CVSS {evidence.max_cvss}."
    return _param(
        max(10.0, mode - 20.0),
        mode,
        min(99.0, mode + 15.0),
        source_type=SourceType.MODEL_ESTIMATE,
        source="scenario factory: CVSS-implied attacker capability",
        confidence=0.4,
        assumption=assumption,
    )


def resistance_strength(asset: AssetContext) -> Parameter:
    """Inherent resistance, before any control is applied."""
    mode = INHERENT_RESISTANCE_MODE.get(asset.category, DEFAULT_RESISTANCE_MODE)
    return _param(
        max(0.0, mode - RESISTANCE_LOW_SPAN),
        mode,
        min(100.0, mode + RESISTANCE_HIGH_SPAN),
        source_type=SourceType.USER_INPUT,
        source="scenario factory: inherent asset resistance",
        confidence=0.4,
        assumption=(
            "Baseline resistance of the asset class with no controls applied; controls are "
            "applied separately by the evaluation harness."
        ),
    )


def _loss_mode(component: str, asset: AssetContext) -> float:
    scale = asset.criticality_score / CRITICALITY_REFERENCE
    exposure = EXPOSURE_LOSS_FACTOR if asset.internet_exposed else 1.0
    mode = COMPONENT_MODES[component] * scale
    if component in EXPOSURE_SCALED_COMPONENTS:
        mode *= exposure
    if component == "regulatory":
        mode *= REGULATORY_PRESENT_FACTOR if asset.regulatory_scope else REGULATORY_ABSENT_FACTOR
    return mode


def _loss_param(component: str, asset: AssetContext) -> Parameter:
    mode = _loss_mode(component, asset)
    return _param(
        _money(mode * LOSS_MIN_FACTOR),
        _money(mode),
        _money(mode * LOSS_MAX_FACTOR),
        source_type=SourceType.SYNTHETIC_DEMO,
        source="scenario factory: criticality-scaled three-point estimate",
        confidence=0.2,
        assumption=(
            f"Synthetic loss component '{component}' scaled by criticality "
            f"{asset.criticality_score:.2f} ({asset.criticality_band}). Demonstration input."
        ),
    )


def materialize_scenario(
    *,
    scenario_id: str,
    name: str,
    description: str | None,
    asset: AssetContext,
    findings: Sequence[FindingContext],
    currency: str = "INR",
    attack_techniques: Sequence[str] = (),
    cve_ids: Sequence[str] = (),
) -> ScenarioSpec:
    """Build a complete, simulatable FAIR specification for one scenario."""
    evidence = gather_evidence(findings)

    frequency = FrequencyModelSpec(
        contact_frequency=contact_frequency(asset),
        probability_of_action=probability_of_action(evidence),
        threat_capability=threat_capability(evidence),
        resistance_strength=resistance_strength(asset),
    )
    magnitude = MagnitudeModelSpec(
        primary={
            component: _loss_param(component, asset)
            for component in (
                "incident_response",
                "downtime",
                "recovery",
                "fraud_theft",
                "data_restoration",
            )
        },
        secondary={
            component: _loss_param(component, asset)
            for component in (
                "notification_legal",
                "regulatory",
                "customer_impact",
                "reputational",
            )
        },
        secondary_loss_event_frequency=_param(
            SLEF_MIN,
            SLEF_MODE,
            SLEF_MAX,
            source_type=SourceType.MODEL_ESTIMATE,
            source="scenario factory: secondary loss propensity",
            confidence=0.35,
            assumption="Probability a primary loss also triggers secondary loss.",
        ),
    )

    return ScenarioSpec(
        id=scenario_id,
        name=name,
        description=description,
        asset_id=asset.asset_id,
        business_service=None,
        currency=currency,
        cve_ids=list(cve_ids),
        attack_techniques=list(attack_techniques),
        frequency=frequency,
        magnitude=magnitude,
    )


__all__ = [
    "AssetContext",
    "ExploitationEvidence",
    "FindingContext",
    "contact_frequency",
    "gather_evidence",
    "materialize_scenario",
    "probability_of_action",
    "resistance_strength",
    "threat_capability",
]
