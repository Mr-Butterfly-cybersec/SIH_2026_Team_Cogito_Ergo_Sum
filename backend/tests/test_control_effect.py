"""Control evidence, effectiveness, and FAIR factor application."""

from __future__ import annotations

import pytest

from app.risk.control_effect import (
    RESISTANCE_SHIFT_MAX,
    ControlApplication,
    ControlCategory,
    ControlEvidence,
    Factor,
    apply_control_effects,
    factor_effect,
    scale_distribution,
    shift_distribution,
)
from app.risk.distributions import BetaPert, Constant, Poisson
from app.risk.frequency import FrequencyModel
from app.risk.magnitude import MagnitudeModel
from app.risk.monte_carlo import CompiledScenario, SimulationConfig, run_simulation


def _freq() -> FrequencyModel:
    return FrequencyModel(
        contact_frequency=BetaPert(2, 6, 20),
        probability_of_action=BetaPert(0.05, 0.2, 0.6),
        threat_capability=BetaPert(40, 65, 95),
        resistance_strength=BetaPert(20, 45, 80),
    )


def _mag() -> MagnitudeModel:
    return MagnitudeModel(
        primary={"downtime": BetaPert(100_000, 500_000, 2_000_000)},
        secondary={"regulatory": BetaPert(0, 200_000, 1_000_000)},
        secondary_loss_event_frequency=BetaPert(0.1, 0.3, 0.6),
    )


def _run(frequency: FrequencyModel, magnitude: MagnitudeModel):
    scenario = CompiledScenario(
        id="T", name="test", currency="INR", frequency=frequency, magnitude=magnitude
    )
    return run_simulation(scenario, SimulationConfig(n_trials=20_000, seed=42))


def test_effectiveness_bounds() -> None:
    perfect = ControlEvidence(
        coverage=1.0, configuration_strength=1.0, policy_compliance=1.0, verification_age_days=0
    )
    none = ControlEvidence(
        coverage=0.0, configuration_strength=0.0, policy_compliance=0.0, verification_age_days=0
    )
    assert perfect.effectiveness() == pytest.approx(1.0)
    assert none.effectiveness() == 0.0
    assert 0.0 <= none.effectiveness() <= 1.0


def test_recent_incidents_and_staleness_reduce_effectiveness() -> None:
    clean = ControlEvidence(
        coverage=1.0, configuration_strength=1.0, policy_compliance=1.0, recent_incident_signal=0.0
    )
    incident = ControlEvidence(
        coverage=1.0, configuration_strength=1.0, policy_compliance=1.0, recent_incident_signal=1.0
    )
    assert incident.effectiveness() < clean.effectiveness()

    fresh = ControlEvidence(
        coverage=1.0, configuration_strength=1.0, policy_compliance=1.0, verification_age_days=10
    )
    stale = ControlEvidence(
        coverage=1.0, configuration_strength=1.0, policy_compliance=1.0, verification_age_days=400
    )
    assert stale.effectiveness() < fresh.effectiveness()
    assert stale.effectiveness() == pytest.approx(1.0 - 0.15)


def test_unverified_control_has_no_staleness_penalty() -> None:
    unknown = ControlEvidence(coverage=1.0, configuration_strength=1.0, policy_compliance=1.0)
    assert unknown.staleness_penalty == 0.0


def test_rejects_out_of_range_evidence() -> None:
    with pytest.raises(ValueError):
        ControlEvidence(coverage=1.5)
    with pytest.raises(ValueError):
        ControlEvidence(recent_incident_signal=-0.1)


def test_category_to_factor_mapping() -> None:
    assert factor_effect(ControlCategory.AVOIDANCE, 0.5).factor is Factor.CONTACT_FREQUENCY
    assert factor_effect(ControlCategory.DETERRENT, 0.5).factor is Factor.PROBABILITY_OF_ACTION
    assert factor_effect(ControlCategory.RESPONSIVE, 0.5).factor is Factor.LOSS_MAGNITUDE
    resistive = factor_effect(ControlCategory.RESISTIVE, 0.5)
    assert resistive.factor is Factor.RESISTANCE_STRENGTH
    assert resistive.multiplier == 1.0
    assert resistive.shift == pytest.approx(0.5 * RESISTANCE_SHIFT_MAX)


def test_factor_effect_multiplier_is_complementary() -> None:
    assert factor_effect(ControlCategory.AVOIDANCE, 0.4).multiplier == pytest.approx(0.6)
    assert factor_effect(ControlCategory.AVOIDANCE, 1.0).multiplier == pytest.approx(0.0)


def test_scale_distribution() -> None:
    scaled = scale_distribution(BetaPert(10, 20, 30), 0.5)
    assert (scaled.minimum, scaled.mode, scaled.maximum) == (5.0, 10.0, 15.0)
    assert scale_distribution(BetaPert(10, 20, 30), 0.0) == Constant(0.0)
    capped = scale_distribution(BetaPert(0.2, 0.5, 0.9), 2.0, cap=1.0)
    assert capped.maximum == 1.0
    assert scale_distribution(Poisson(4.0), 0.5).rate == 2.0
    unchanged = BetaPert(1, 2, 3)
    assert scale_distribution(unchanged, 1.0) is unchanged


def test_shift_distribution_caps_at_ceiling() -> None:
    shifted = shift_distribution(BetaPert(60, 70, 80), 40.0, cap=100.0)
    assert (shifted.minimum, shifted.mode, shifted.maximum) == (100.0, 100.0, 100.0)
    assert shift_distribution(BetaPert(1, 2, 3), 0.0).mode == 2.0


def test_applying_controls_reduces_risk() -> None:
    frequency, magnitude = _freq(), _mag()
    before = _run(frequency, magnitude)

    hardened_frequency, hardened_magnitude = apply_control_effects(
        frequency=frequency,
        magnitude=magnitude,
        applications=[
            ControlApplication("CTL-MFA-PRIV", ControlCategory.RESISTIVE, 0.8),
            ControlApplication("CTL-BACKUP", ControlCategory.RESPONSIVE, 0.6),
            ControlApplication("CTL-WAF", ControlCategory.AVOIDANCE, 0.5),
            ControlApplication("CTL-EDR", ControlCategory.DETERRENT, 0.4),
        ],
    )
    after = _run(hardened_frequency, hardened_magnitude)

    assert after.vulnerability < before.vulnerability
    assert after.summary.eal < before.summary.eal
    assert after.mean_lef < before.mean_lef


def test_no_controls_leaves_the_model_unchanged() -> None:
    frequency, magnitude = _freq(), _mag()
    new_frequency, new_magnitude = apply_control_effects(
        frequency=frequency, magnitude=magnitude, applications=[]
    )
    assert new_frequency.contact_frequency is frequency.contact_frequency
    assert new_frequency.probability_of_action is frequency.probability_of_action
    assert new_magnitude.primary["downtime"] is magnitude.primary["downtime"]
