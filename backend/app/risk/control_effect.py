"""Control effectiveness: evidence → bounded effectiveness → FAIR factor effect.

A control is described by evidence (coverage, configuration strength, policy compliance,
recent incident signal, verification age), never a bare yes/no. Each control category maps
to the FAIR factor it actually moves:

    Avoidance  → Contact Frequency ↓
    Deterrent  → Probability of Action ↓
    Resistive  → Resistance Strength ↑   (Vulnerability is recomputed from it)
    Responsive → Loss Magnitude ↓

Note: combining several independent controls multiplicatively is a first-order
approximation and overstates reduction when controls overlap. Prefer applying controls and
re-simulating (see docs/methodology.md).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.risk.distributions import BetaPert, Constant, Lognormal, Poisson
from app.risk.frequency import FrequencyModel
from app.risk.magnitude import MagnitudeModel

# Evidence weights (sum = 1.0).
EVIDENCE_WEIGHTS: dict[str, float] = {
    "coverage": 0.45,
    "configuration_strength": 0.30,
    "policy_compliance": 0.25,
}
INCIDENT_PENALTY_WEIGHT = 0.25
STALENESS_THRESHOLD_DAYS = 90
STALENESS_WINDOW_DAYS = 180
STALENESS_MAX_PENALTY = 0.15
RESISTANCE_SHIFT_MAX = 45.0  # percentile points at full effectiveness


class ControlCategory(StrEnum):
    AVOIDANCE = "avoidance"
    DETERRENT = "deterrent"
    RESISTIVE = "resistive"
    RESPONSIVE = "responsive"


class Factor(StrEnum):
    CONTACT_FREQUENCY = "contact_frequency"
    PROBABILITY_OF_ACTION = "probability_of_action"
    RESISTANCE_STRENGTH = "resistance_strength"
    LOSS_MAGNITUDE = "loss_magnitude"


CATEGORY_FACTOR: dict[ControlCategory, Factor] = {
    ControlCategory.AVOIDANCE: Factor.CONTACT_FREQUENCY,
    ControlCategory.DETERRENT: Factor.PROBABILITY_OF_ACTION,
    ControlCategory.RESISTIVE: Factor.RESISTANCE_STRENGTH,
    ControlCategory.RESPONSIVE: Factor.LOSS_MAGNITUDE,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ControlEvidence:
    coverage: float = 0.0
    configuration_strength: float = 0.0
    policy_compliance: float = 1.0
    recent_incident_signal: float = 0.0
    verification_age_days: int | None = None

    def __post_init__(self) -> None:
        for name in EVIDENCE_WEIGHTS:
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1], got {value}")
        if not 0.0 <= self.recent_incident_signal <= 1.0:
            raise ValueError("recent_incident_signal must be within [0, 1]")

    @property
    def base_score(self) -> float:
        return sum(EVIDENCE_WEIGHTS[name] * getattr(self, name) for name in EVIDENCE_WEIGHTS)

    @property
    def incident_penalty(self) -> float:
        return INCIDENT_PENALTY_WEIGHT * self.recent_incident_signal

    @property
    def staleness_penalty(self) -> float:
        """A control that has not been verified recently is trusted less."""
        if self.verification_age_days is None:
            return 0.0
        overdue = max(0, self.verification_age_days - STALENESS_THRESHOLD_DAYS)
        return STALENESS_MAX_PENALTY * min(1.0, overdue / STALENESS_WINDOW_DAYS)

    def effectiveness(self) -> float:
        """Bounded effectiveness in [0, 1]."""
        score = self.base_score * (1.0 - self.incident_penalty) - self.staleness_penalty
        return _clamp(score)

    def to_dict(self) -> dict[str, float | int | None]:
        return {
            "coverage": self.coverage,
            "configuration_strength": self.configuration_strength,
            "policy_compliance": self.policy_compliance,
            "recent_incident_signal": self.recent_incident_signal,
            "verification_age_days": self.verification_age_days,
            "effectiveness": round(self.effectiveness(), 4),
        }


@dataclass(frozen=True)
class FactorEffect:
    factor: Factor
    multiplier: float = 1.0
    shift: float = 0.0

    def describe(self) -> str:
        if self.shift:
            return f"{self.factor.value} += {self.shift:.1f} percentile points"
        return f"{self.factor.value} ×= {self.multiplier:.3f}"


def factor_effect(category: ControlCategory, effectiveness: float) -> FactorEffect:
    """Translate a control and its effectiveness into the FAIR factor it moves."""
    eff = _clamp(effectiveness)
    if category is ControlCategory.RESISTIVE:
        return FactorEffect(
            factor=Factor.RESISTANCE_STRENGTH, multiplier=1.0, shift=eff * RESISTANCE_SHIFT_MAX
        )
    return FactorEffect(factor=CATEGORY_FACTOR[category], multiplier=1.0 - eff, shift=0.0)


@dataclass(frozen=True)
class ControlApplication:
    control_id: str
    category: ControlCategory
    effectiveness: float


def _cap(value: float, cap: float | None) -> float:
    return value if cap is None else min(value, cap)


def scale_distribution(dist: object, multiplier: float, cap: float | None = None) -> object:
    """Scale a distribution's values (0 multiplier collapses it to zero)."""
    if multiplier == 1.0:
        return dist
    if multiplier <= 0.0:
        return Constant(0.0)
    if isinstance(dist, BetaPert):
        return BetaPert(
            _cap(dist.minimum * multiplier, cap),
            _cap(dist.mode * multiplier, cap),
            _cap(dist.maximum * multiplier, cap),
            dist.weight,
        )
    if isinstance(dist, Constant):
        return Constant(_cap(dist.value * multiplier, cap))
    if isinstance(dist, Lognormal):
        return Lognormal(dist.mu + math.log(multiplier), dist.sigma)
    if isinstance(dist, Poisson):
        return Poisson(dist.rate * multiplier)
    raise TypeError(f"cannot scale distribution of type {type(dist).__name__}")


def shift_distribution(dist: object, delta: float, cap: float | None = None) -> object:
    """Shift a distribution's values by a constant."""
    if delta == 0.0:
        return dist
    if isinstance(dist, BetaPert):
        return BetaPert(
            _cap(dist.minimum + delta, cap),
            _cap(dist.mode + delta, cap),
            _cap(dist.maximum + delta, cap),
            dist.weight,
        )
    if isinstance(dist, Constant):
        return Constant(_cap(dist.value + delta, cap))
    raise TypeError(f"cannot shift distribution of type {type(dist).__name__}")


def apply_control_effects(
    *,
    frequency: FrequencyModel,
    magnitude: MagnitudeModel,
    applications: Sequence[ControlApplication],
) -> tuple[FrequencyModel, MagnitudeModel]:
    """Return new frequency/magnitude models with the given controls applied."""
    contact_multiplier = 1.0
    action_multiplier = 1.0
    loss_multiplier = 1.0
    resistance_shift = 0.0

    for application in applications:
        eff = _clamp(application.effectiveness)
        if application.category is ControlCategory.AVOIDANCE:
            contact_multiplier *= 1.0 - eff
        elif application.category is ControlCategory.DETERRENT:
            action_multiplier *= 1.0 - eff
        elif application.category is ControlCategory.RESPONSIVE:
            loss_multiplier *= 1.0 - eff
        elif application.category is ControlCategory.RESISTIVE:
            resistance_shift += eff * RESISTANCE_SHIFT_MAX

    hardened_frequency = FrequencyModel(
        contact_frequency=scale_distribution(frequency.contact_frequency, contact_multiplier),
        probability_of_action=scale_distribution(
            frequency.probability_of_action, action_multiplier, cap=1.0
        ),
        threat_capability=frequency.threat_capability,
        resistance_strength=shift_distribution(
            frequency.resistance_strength, resistance_shift, cap=100.0
        ),
    )
    hardened_magnitude = MagnitudeModel(
        primary={
            name: scale_distribution(dist, loss_multiplier)
            for name, dist in magnitude.primary.items()
        },
        secondary={
            name: scale_distribution(dist, loss_multiplier)
            for name, dist in magnitude.secondary.items()
        },
        secondary_loss_event_frequency=magnitude.secondary_loss_event_frequency,
    )
    return hardened_frequency, hardened_magnitude
