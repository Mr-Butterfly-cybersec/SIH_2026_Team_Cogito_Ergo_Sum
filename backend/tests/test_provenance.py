"""Provenance and data-confidence."""

from datetime import date

import pytest

from app.risk.provenance import (
    ConfidenceBand,
    EvidenceMix,
    Provenance,
    SourceType,
    confidence_band,
)


def test_evidence_mix_proportions_and_band() -> None:
    provenances = [Provenance(SourceType.PUBLIC_DATA, "nvd")] * 4 + [
        Provenance(SourceType.SYNTHETIC_DEMO, "demo")
    ]
    mix = EvidenceMix.from_provenances(provenances)
    assert mix.total == 5
    assert sum(mix.proportions.values()) == pytest.approx(1.0)
    assert mix.proportions["PUBLIC_DATA"] == pytest.approx(0.8)
    # (0.90*4 + 0.15*1) / 5 = 0.75 -> HIGH
    assert mix.band is ConfidenceBand.HIGH


def test_confidence_bands() -> None:
    assert confidence_band(0.90) is ConfidenceBand.HIGH
    assert confidence_band(0.75) is ConfidenceBand.HIGH
    assert confidence_band(0.60) is ConfidenceBand.MEDIUM
    assert confidence_band(0.49) is ConfidenceBand.LOW


def test_empty_mix_is_low() -> None:
    mix = EvidenceMix.from_provenances([])
    assert mix.total == 0
    assert mix.confidence_score == 0.0
    assert mix.band is ConfidenceBand.LOW


def test_synthetic_heavy_mix_is_low() -> None:
    provenances = [Provenance(SourceType.SYNTHETIC_DEMO, "demo")] * 9 + [
        Provenance(SourceType.PUBLIC_DATA, "nvd")
    ]
    mix = EvidenceMix.from_provenances(provenances)
    assert mix.band is ConfidenceBand.LOW


def test_provenance_validation_and_serialisation() -> None:
    with pytest.raises(ValueError):
        Provenance(SourceType.USER_INPUT, "x", confidence=1.5)
    payload = Provenance(
        SourceType.PUBLIC_DATA, "NVD", source_date=date(2026, 9, 10), confidence=0.9
    ).to_dict()
    assert payload["source_type"] == "PUBLIC_DATA"
    assert payload["source_date"] == "2026-09-10"
