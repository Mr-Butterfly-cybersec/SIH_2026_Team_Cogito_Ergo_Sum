"""Monte Carlo engine: structure, reproducibility, monotonicity, aggregation."""

import json

import numpy as np
import pytest

from app.risk.aggregation import portfolio_losses, portfolio_summary, total_eal
from app.risk.demo import EXAMPLE
from app.risk.schemas import ScenarioSpec, simulate

RAW = json.loads(EXAMPLE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenario() -> ScenarioSpec:
    return ScenarioSpec.model_validate(RAW)


def _variant(mutate) -> ScenarioSpec:
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    mutate(raw)
    return ScenarioSpec.model_validate(raw)


def test_result_is_well_formed(scenario: ScenarioSpec) -> None:
    result = simulate(scenario, n_trials=20_000, seed=42)
    s = result.summary
    assert s.eal > 0
    assert s.minimum <= s.p50 <= s.p90 <= s.p95 <= s.p99 <= s.maximum
    assert s.cvar_95 >= s.p95
    assert 0.0 < result.vulnerability < 1.0
    assert result.mean_lef <= result.mean_tef + 1e-9
    assert sum(result.histogram["counts"]) == result.n_trials
    assert len(result.loss_exceedance["loss"]) == len(result.loss_exceedance["probability"])


def test_all_parameters_carry_provenance(scenario: ScenarioSpec) -> None:
    result = simulate(scenario, n_trials=1_000, seed=1)
    # 4 frequency + 5 primary + 4 secondary + 1 secondary-frequency = 14
    assert result.evidence_mix.total == 14
    assert result.evidence_mix.proportions["SYNTHETIC_DEMO"] > 0
    assert result.evidence_mix.confidence_score > 0


def test_reproducible_with_seed(scenario: ScenarioSpec) -> None:
    a = simulate(scenario, n_trials=10_000, seed=42)
    b = simulate(scenario, n_trials=10_000, seed=42)
    assert a.summary.eal == b.summary.eal
    np.testing.assert_array_equal(a.losses, b.losses)
    c = simulate(scenario, n_trials=10_000, seed=43)
    assert c.summary.eal != a.summary.eal


def test_loss_exceedance_is_decreasing(scenario: ScenarioSpec) -> None:
    probs = simulate(scenario, n_trials=10_000, seed=42).loss_exceedance["probability"]
    assert all(probs[i] >= probs[i + 1] for i in range(len(probs) - 1))
    assert probs[0] > probs[-1]


def test_zero_contact_frequency_produces_zero_loss() -> None:
    def mutate(raw: dict) -> None:
        raw["frequency"]["contact_frequency"]["distribution"] = {"kind": "constant", "value": 0}
        raw["frequency"]["probability_of_action"]["distribution"] = {"kind": "constant", "value": 1}

    result = simulate(_variant(mutate), n_trials=2_000, seed=1)
    assert result.summary.eal == 0
    assert result.summary.maximum == 0
    assert result.mean_lef == 0


def test_higher_resistance_strength_lowers_risk(scenario: ScenarioSpec) -> None:
    strong = _variant(
        lambda raw: raw["frequency"].__setitem__(
            "resistance_strength",
            {
                "distribution": {"kind": "pert", "minimum": 95, "mode": 99, "maximum": 100},
                "provenance": raw["frequency"]["resistance_strength"]["provenance"],
            },
        )
    )
    base = simulate(scenario, n_trials=30_000, seed=42)
    hardened = simulate(strong, n_trials=30_000, seed=42)
    assert hardened.vulnerability < base.vulnerability
    assert hardened.summary.eal < base.summary.eal


def test_higher_probability_of_action_raises_risk(scenario: ScenarioSpec) -> None:
    aggressive = _variant(
        lambda raw: raw["frequency"].__setitem__(
            "probability_of_action",
            {
                "distribution": {"kind": "pert", "minimum": 0.6, "mode": 0.85, "maximum": 1.0},
                "provenance": raw["frequency"]["probability_of_action"]["provenance"],
            },
        )
    )
    base = simulate(scenario, n_trials=30_000, seed=42)
    hotter = simulate(aggressive, n_trials=30_000, seed=42)
    assert hotter.summary.eal > base.summary.eal


def test_aggregation_sums_scenarios(scenario: ScenarioSpec) -> None:
    r1 = simulate(scenario, n_trials=5_000, seed=1)
    r2 = simulate(scenario, n_trials=5_000, seed=2)
    combined = portfolio_losses([r1, r2])
    assert combined.shape == (5_000,)
    assert total_eal([r1, r2]) == pytest.approx(r1.summary.eal + r2.summary.eal)
    assert portfolio_summary([r1, r2]).eal == pytest.approx(r1.summary.eal + r2.summary.eal)


def test_aggregation_requires_matching_trial_counts(scenario: ScenarioSpec) -> None:
    r1 = simulate(scenario, n_trials=1_000, seed=1)
    r2 = simulate(scenario, n_trials=2_000, seed=2)
    with pytest.raises(ValueError):
        portfolio_losses([r1, r2])
