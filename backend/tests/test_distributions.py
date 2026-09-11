"""Distribution primitives: closed-form stats and sampling behaviour."""

import numpy as np
import pytest

from app.risk.distributions import BetaPert, Constant, Lognormal, Poisson


def test_beta_pert_closed_form() -> None:
    d = BetaPert(0, 1, 10)
    assert d.mean == pytest.approx((0 + 4 * 1 + 10) / 6)
    assert d.alpha == pytest.approx(1 + 4 * (1 - 0) / (10 - 0))
    assert d.beta == pytest.approx(1 + 4 * (10 - 1) / (10 - 0))
    assert d.variance == pytest.approx((d.mean - 0) * (10 - d.mean) / 7)


def test_beta_pert_symmetric_is_beta_3_3() -> None:
    d = BetaPert(0, 5, 10)
    assert d.alpha == pytest.approx(3.0)
    assert d.beta == pytest.approx(3.0)
    assert d.mean == pytest.approx(5.0)


def test_beta_pert_sampling_matches_theory() -> None:
    d = BetaPert(100, 200, 900)
    rng = np.random.default_rng(0)
    x = d.sample(rng, 400_000)
    assert x.mean() == pytest.approx(d.mean, rel=0.02)
    assert x.var() == pytest.approx(d.variance, rel=0.05)
    assert x.min() >= 100.0
    assert x.max() <= 900.0


def test_beta_pert_sampling_is_reproducible() -> None:
    d = BetaPert(1, 2, 3)
    first = d.sample(np.random.default_rng(7), 5)
    second = d.sample(np.random.default_rng(7), 5)
    np.testing.assert_array_equal(first, second)


def test_beta_pert_degenerate_is_constant() -> None:
    d = BetaPert(5, 5, 5)
    assert d.mean == 5.0
    assert d.variance == 0.0
    assert np.all(d.sample(np.random.default_rng(0), 4) == 5.0)


def test_beta_pert_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        BetaPert(10, 1, 0)
    with pytest.raises(ValueError):
        BetaPert(0, 1, 10, weight=0)


def test_lognormal_from_median_p90() -> None:
    d = Lognormal.from_median_p90(1_000_000, 5_000_000)
    x = d.sample(np.random.default_rng(1), 400_000)
    assert float(np.median(x)) == pytest.approx(1_000_000, rel=0.02)
    assert float(np.percentile(x, 90)) == pytest.approx(5_000_000, rel=0.02)


def test_lognormal_rejects_invalid_percentiles() -> None:
    with pytest.raises(ValueError):
        Lognormal.from_median_p90(100, 50)


def test_constant_samples_are_fixed() -> None:
    assert Constant(3.0).sample(np.random.default_rng(0), 3).tolist() == [3.0, 3.0, 3.0]
    assert Constant(3.0).variance == 0.0


def test_poisson_stats_and_validation() -> None:
    assert Poisson(4.0).mean == 4.0
    assert Poisson(4.0).variance == 4.0
    with pytest.raises(ValueError):
        Poisson(-1)
