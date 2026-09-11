"""Decision metrics."""

import pytest

from app.risk.metrics import (
    annualize,
    risk_reduction,
    risk_reduction_pct,
    risk_removed_per_unit,
    rosi,
)


def test_risk_reduction() -> None:
    assert risk_reduction(1000.0, 400.0) == 600.0
    assert risk_reduction_pct(1000.0, 400.0) == pytest.approx(0.6)
    assert risk_reduction_pct(0.0, 0.0) is None


def test_rosi() -> None:
    assert rosi(1000.0, 400.0, 200.0) == pytest.approx((600.0 - 200.0) / 200.0)
    assert rosi(1000.0, 400.0, 0.0) is None


def test_risk_removed_per_unit() -> None:
    assert risk_removed_per_unit(1000.0, 400.0, 200.0) == pytest.approx(3.0)
    assert risk_removed_per_unit(1000.0, 400.0, 0.0) is None


def test_annualize() -> None:
    assert annualize(1000.0, 2) == pytest.approx(500.0)
    assert annualize(1000.0, 2, recurring_cost=100.0) == pytest.approx(600.0)
    with pytest.raises(ValueError):
        annualize(1000.0, 0)
