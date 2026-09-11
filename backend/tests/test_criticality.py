"""Weighted asset criticality model."""

from __future__ import annotations

import pytest

from app.risk.asset_criticality import (
    DIMENSION_WEIGHTS,
    DIMENSIONS,
    CriticalityBand,
    CriticalityProfile,
    criticality_band,
)


def test_weights_sum_to_one() -> None:
    assert sum(DIMENSION_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(DIMENSION_WEIGHTS) == set(DIMENSIONS)


def test_empty_profile_is_the_minimum() -> None:
    profile = CriticalityProfile()
    assert profile.score == pytest.approx(1.0)
    assert profile.band is CriticalityBand.LOW


def test_max_profile_is_the_maximum() -> None:
    profile = CriticalityProfile(**dict.fromkeys(DIMENSIONS, 5))
    assert profile.score == pytest.approx(5.0)
    assert profile.band is CriticalityBand.CRITICAL


def test_score_is_monotonic_in_every_dimension() -> None:
    baseline = CriticalityProfile(**dict.fromkeys(DIMENSIONS, 2))
    for dimension in DIMENSIONS:
        raised = CriticalityProfile(**{**dict.fromkeys(DIMENSIONS, 2), dimension: 5})
        assert raised.score > baseline.score, dimension


def test_bands() -> None:
    assert criticality_band(4.2) is CriticalityBand.CRITICAL
    assert criticality_band(3.4) is CriticalityBand.HIGH
    assert criticality_band(2.1) is CriticalityBand.MEDIUM
    assert criticality_band(1.2) is CriticalityBand.LOW


def test_rejects_out_of_range_and_unknown_dimensions() -> None:
    with pytest.raises(ValueError):
        CriticalityProfile(availability=6)
    with pytest.raises(ValueError):
        CriticalityProfile(regulatory=-1)
    with pytest.raises(ValueError):
        CriticalityProfile.from_mapping({"nonsense": 3})


def test_to_dict_exposes_the_weights() -> None:
    payload = CriticalityProfile(availability=5).to_dict()
    assert payload["dimensions"]["availability"] == 5
    assert payload["weights"] == DIMENSION_WEIGHTS
    assert payload["band"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
