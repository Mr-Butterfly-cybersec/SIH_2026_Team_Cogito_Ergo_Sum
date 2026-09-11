"""FAIR frequency side: Threat Event Frequency and Vulnerability.

    TEF          = Contact Frequency × Probability of Action
    Vulnerability = Pr(Threat Capability > Resistance Strength)
    LEF          = TEF × Vulnerability

Probability of Action is part of TEF, not Vulnerability. A failed attack is a threat
event, not a loss event. Vulnerability is derived, never taken as an input.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.risk.distributions import Distribution

PERCENTILE_MIN = 0.0
PERCENTILE_MAX = 100.0


@dataclass(frozen=True)
class FrequencySample:
    """Per-trial frequency-side draws."""

    tef: np.ndarray
    vulnerability: float
    lef: np.ndarray


@dataclass(frozen=True)
class FrequencyModel:
    contact_frequency: Distribution
    probability_of_action: Distribution
    threat_capability: Distribution
    resistance_strength: Distribution

    def sample(self, rng: np.random.Generator, size: int) -> FrequencySample:
        contact = np.clip(self.contact_frequency.sample(rng, size), 0.0, None)
        action = np.clip(self.probability_of_action.sample(rng, size), 0.0, 1.0)
        tef = contact * action

        threat_cap = np.clip(
            self.threat_capability.sample(rng, size), PERCENTILE_MIN, PERCENTILE_MAX
        )
        resistance = np.clip(
            self.resistance_strength.sample(rng, size), PERCENTILE_MIN, PERCENTILE_MAX
        )
        vulnerability = float(np.mean(threat_cap > resistance))

        lef = tef * vulnerability
        return FrequencySample(tef=tef, vulnerability=vulnerability, lef=lef)
