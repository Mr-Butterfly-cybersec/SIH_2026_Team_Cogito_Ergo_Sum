"""Provenance and data-confidence for every numeric parameter.

Rule: nothing synthetic is ever presented as measured fact. Every parameter carries a
source type, and the mix of sources behind a result determines its confidence band.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

MODEL_VERSION = "0.1.0"


class SourceType(StrEnum):
    PUBLIC_DATA = "PUBLIC_DATA"
    OBSERVED_TELEMETRY = "OBSERVED_TELEMETRY"
    USER_INPUT = "USER_INPUT"
    MODEL_ESTIMATE = "MODEL_ESTIMATE"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


class ConfidenceBand(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# How much a source is trusted when it contributes to a figure (0-1).
SOURCE_CREDIBILITY: dict[SourceType, float] = {
    SourceType.PUBLIC_DATA: 0.90,
    SourceType.OBSERVED_TELEMETRY: 0.85,
    SourceType.USER_INPUT: 0.60,
    SourceType.MODEL_ESTIMATE: 0.40,
    SourceType.SYNTHETIC_DEMO: 0.15,
}

_BAND_THRESHOLDS = ((0.75, ConfidenceBand.HIGH), (0.50, ConfidenceBand.MEDIUM))


def confidence_band(score: float) -> ConfidenceBand:
    for threshold, band in _BAND_THRESHOLDS:
        if score >= threshold:
            return band
    return ConfidenceBand.LOW


@dataclass(frozen=True)
class Provenance:
    """Where a single numeric parameter came from."""

    source_type: SourceType
    source: str
    source_date: date | None = None
    confidence: float = 0.5
    assumption_description: str | None = None
    model_version: str = MODEL_VERSION

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")

    def to_dict(self) -> dict[str, object]:
        return {
            "source_type": self.source_type.value,
            "source": self.source,
            "source_date": self.source_date.isoformat() if self.source_date else None,
            "confidence": self.confidence,
            "assumption_description": self.assumption_description,
            "model_version": self.model_version,
        }


@dataclass(frozen=True)
class EvidenceMix:
    """The blend of source types behind a result, with a derived confidence band."""

    counts: dict[SourceType, int] = field(default_factory=dict)

    @classmethod
    def from_provenances(cls, items: list[Provenance]) -> EvidenceMix:
        return cls(dict(Counter(p.source_type for p in items)))

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def proportions(self) -> dict[str, float]:
        total = self.total
        if total == 0:
            return {}
        return {source.value: count / total for source, count in self.counts.items()}

    @property
    def confidence_score(self) -> float:
        """Credibility-weighted average across the sources actually present."""
        total = self.total
        if total == 0:
            return 0.0
        weighted = sum(SOURCE_CREDIBILITY[src] * count for src, count in self.counts.items())
        return weighted / total

    @property
    def band(self) -> ConfidenceBand:
        return confidence_band(self.confidence_score)

    def to_dict(self) -> dict[str, object]:
        return {
            "proportions": self.proportions,
            "confidence_score": round(self.confidence_score, 4),
            "band": self.band.value,
            "counts": {src.value: count for src, count in self.counts.items()},
        }
