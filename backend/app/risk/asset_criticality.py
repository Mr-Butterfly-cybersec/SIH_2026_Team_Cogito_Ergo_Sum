"""Documented, weighted asset criticality model.

Deliberately **not** a naive product of the dimensions — multiplying six 0-5 factors
produces absurd nonlinearity. Instead: a weighted average on a visible 1-5 scale, so a
reviewer can see exactly how a criticality score was reached and adjust a weight.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

DIMENSIONS: tuple[str, ...] = (
    "availability",
    "integrity",
    "confidentiality",
    "regulatory",
    "internet_exposure",
    "dependency_centrality",
)

# Visible, adjustable weights (sum = 1.0).
DIMENSION_WEIGHTS: dict[str, float] = {
    "availability": 0.20,
    "integrity": 0.15,
    "confidentiality": 0.20,
    "regulatory": 0.15,
    "internet_exposure": 0.15,
    "dependency_centrality": 0.15,
}

DIMENSION_MIN = 0
DIMENSION_MAX = 5
SCORE_MIN = 1.0
SCORE_MAX = 5.0


class CriticalityBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


_BAND_THRESHOLDS: tuple[tuple[float, CriticalityBand], ...] = (
    (4.0, CriticalityBand.CRITICAL),
    (3.0, CriticalityBand.HIGH),
    (2.0, CriticalityBand.MEDIUM),
)


def criticality_band(score: float) -> CriticalityBand:
    for threshold, band in _BAND_THRESHOLDS:
        if score >= threshold:
            return band
    return CriticalityBand.LOW


@dataclass(frozen=True)
class CriticalityProfile:
    availability: int = 0
    integrity: int = 0
    confidentiality: int = 0
    regulatory: int = 0
    internet_exposure: int = 0
    dependency_centrality: int = 0

    def __post_init__(self) -> None:
        for dimension in DIMENSIONS:
            value = getattr(self, dimension)
            if not DIMENSION_MIN <= value <= DIMENSION_MAX:
                raise ValueError(
                    f"{dimension} must be within [{DIMENSION_MIN}, {DIMENSION_MAX}], got {value}"
                )

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> CriticalityProfile:
        unknown = set(values) - set(DIMENSIONS)
        if unknown:
            raise ValueError(f"unknown criticality dimensions: {sorted(unknown)}")
        return cls(**values)

    def as_dict(self) -> dict[str, int]:
        return {dimension: getattr(self, dimension) for dimension in DIMENSIONS}

    @property
    def fraction(self) -> float:
        """Weighted fraction of the maximum, in [0, 1]."""
        total_weight = sum(DIMENSION_WEIGHTS.values())
        weighted = sum(
            DIMENSION_WEIGHTS[dimension] * (getattr(self, dimension) / DIMENSION_MAX)
            for dimension in DIMENSIONS
        )
        return weighted / total_weight

    @property
    def score(self) -> float:
        """Criticality on a 1-5 scale."""
        return SCORE_MIN + (SCORE_MAX - SCORE_MIN) * self.fraction

    @property
    def band(self) -> CriticalityBand:
        return criticality_band(self.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": self.as_dict(),
            "score": round(self.score, 4),
            "band": self.band.value,
            "weights": DIMENSION_WEIGHTS,
        }


def profile_from_asset(criticality: dict[str, Any] | None) -> CriticalityProfile:
    """Build a profile from a stored criticality mapping (missing dimensions default to 0)."""
    return CriticalityProfile.from_mapping(criticality or {})


__all__ = [
    "DIMENSION_MAX",
    "DIMENSION_MIN",
    "DIMENSION_WEIGHTS",
    "DIMENSIONS",
    "SCORE_MAX",
    "SCORE_MIN",
    "CriticalityBand",
    "CriticalityProfile",
    "criticality_band",
    "profile_from_asset",
]
