"""Scenario engine tests (offline, deterministic, small trial counts)."""

from __future__ import annotations

import pytest

from app.engine import ScenarioEngine, get_engine, reset_engine
from app.optimization.context import load_planning_context

TRIALS = 500
OTHER_SCENARIO = "SCN-WEBAPP-01"


@pytest.fixture(scope="module")
def engine() -> ScenarioEngine:
    return ScenarioEngine(load_planning_context())


def test_context_is_fully_materialized(engine: ScenarioEngine) -> None:
    assert engine.context.assets
    assert engine.context.scenarios
    assert engine.candidates
    assert engine.snapshot.assets


def test_baseline_matches_empty_outcome(engine: ScenarioEngine) -> None:
    baseline = engine.baseline(TRIALS)
    empty = engine.outcome((), n_trials=TRIALS)
    assert baseline.eal == pytest.approx(empty.eal)
    assert baseline.selection == ()


def test_selection_reduces_expected_loss(engine: ScenarioEngine) -> None:
    baseline = engine.baseline(TRIALS)
    hardened = engine.outcome(["INV-CTL-WAF"], n_trials=TRIALS)
    assert hardened.eal <= baseline.eal
    assert hardened.risk_reduction >= 0.0


def test_engine_is_deterministic(engine: ScenarioEngine) -> None:
    first = engine.baseline(TRIALS)
    second = engine.baseline(TRIALS)
    assert first.eal == second.eal


def test_evaluator_is_cached_per_config(engine: ScenarioEngine) -> None:
    assert engine.evaluator(TRIALS, 42) is engine.evaluator(TRIALS, 42)
    assert engine.evaluator(TRIALS, 42) is not engine.evaluator(TRIALS, 7)


def test_simulate_scenario_has_no_raw_paths(engine: ScenarioEngine) -> None:
    result = engine.simulate_scenario("SCN-CRED-01", (), n_trials=TRIALS)
    payload = result.to_dict()
    assert "losses" not in payload
    assert payload["histogram"]["counts"]
    assert payload["loss_exceedance"]["probability"]


def test_simulate_unknown_scenario_raises(engine: ScenarioEngine) -> None:
    with pytest.raises(KeyError):
        engine.simulate_scenario("NOPE", (), n_trials=TRIALS)


def test_optimize_returns_scored_strategies(engine: ScenarioEngine) -> None:
    result, outcomes = engine.optimize(2_500_000.0, n_trials=TRIALS)
    assert len(outcomes) == 6
    assert outcomes[0].label == "current posture"
    assert result.spend <= 2_500_000.0
    optimizer = next(o for o in outcomes if o.label == "optimizer")
    assert optimizer.risk_reduction >= outcomes[0].risk_reduction


def test_delay_impact_accounts_for_the_window(engine: ScenarioEngine) -> None:
    impact = engine.delay_impact("SCN-CRED-01", ["INV-CTL-MFA-PRIV"], 30, n_trials=TRIALS)
    assert impact.window_years == pytest.approx(30 / 365)
    assert impact.loss_if_delayed == pytest.approx(impact.baseline_eal * 30 / 365)
    assert impact.avoidable_loss >= 0.0
    assert impact.hardened_eal <= impact.baseline_eal


def test_delay_zero_days_is_zero_loss(engine: ScenarioEngine) -> None:
    impact = engine.delay_impact("SCN-CRED-01", ["INV-CTL-MFA-PRIV"], 0, n_trials=TRIALS)
    assert impact.avoidable_loss == pytest.approx(0.0)


def test_delay_rejects_negative_days(engine: ScenarioEngine) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        engine.delay_impact("SCN-CRED-01", [], -1, n_trials=TRIALS)


def test_criticality_change_raises_exposure(engine: ScenarioEngine) -> None:
    impact = engine.criticality_impact(
        OTHER_SCENARIO, {"availability": 5, "confidentiality": 5}, n_trials=TRIALS
    )
    assert impact.eal_delta != 0.0
    assert impact.after["score"] >= impact.before["score"]


def test_criticality_change_on_unknown_scenario_raises(engine: ScenarioEngine) -> None:
    with pytest.raises(KeyError):
        engine.criticality_impact("NOPE", {"availability": 5}, n_trials=TRIALS)


def test_risk_reduction_for_selection(engine: ScenarioEngine) -> None:
    summary = engine.risk_reduction_for(["INV-CTL-WAF"])
    assert summary["risk_reduction"] >= 0.0
    assert 0.0 <= summary["risk_reduction_pct"] <= 1.0


def test_get_engine_is_a_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_engine()
    try:
        assert get_engine() is get_engine()
    finally:
        reset_engine()
