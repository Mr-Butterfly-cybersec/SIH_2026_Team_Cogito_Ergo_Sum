"""FAIR magnitude side: Primary and Secondary Loss Magnitude.

Loss Magnitude = Primary Loss Magnitude + Secondary Loss Magnitude
Secondary loss only occurs after a primary loss, with probability SLEF.

per-event loss = PLM + 1{Secondary occurs} · SLM
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.risk.distributions import Distribution

PRIMARY_COMPONENTS = (
    "incident_response",
    "downtime",
    "recovery",
    "fraud_theft",
    "data_restoration",
)

SECONDARY_COMPONENTS = (
    "notification_legal",
    "regulatory",
    "customer_impact",
    "reputational",
)


def _sum_components(
    components: dict[str, Distribution], rng: np.random.Generator, size: int
) -> np.ndarray:
    total = np.zeros(size)
    for distribution in components.values():
        total = total + np.clip(distribution.sample(rng, size), 0.0, None)
    return total


@dataclass(frozen=True)
class MagnitudeModel:
    primary: dict[str, Distribution]
    secondary: dict[str, Distribution]
    secondary_loss_event_frequency: Distribution

    def sample_plm(self, rng: np.random.Generator, size: int) -> np.ndarray:
        return _sum_components(self.primary, rng, size)

    def sample_slm(self, rng: np.random.Generator, size: int) -> np.ndarray:
        return _sum_components(self.secondary, rng, size)

    def sample_slef(self, rng: np.random.Generator, size: int) -> np.ndarray:
        return np.clip(self.secondary_loss_event_frequency.sample(rng, size), 0.0, 1.0)

    def sample_event_losses(self, rng: np.random.Generator, size: int) -> np.ndarray:
        """Draw ``size`` independent per-event loss magnitudes."""
        if size == 0:
            return np.zeros(0)
        plm = self.sample_plm(rng, size)
        secondary_occurs = rng.random(size) < self.sample_slef(rng, size)
        slm = self.sample_slm(rng, size) * secondary_occurs
        return plm + slm
