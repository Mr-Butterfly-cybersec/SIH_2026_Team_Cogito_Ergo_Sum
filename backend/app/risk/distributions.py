"""Probability distributions for the quantitative risk model.

Pure and deterministic given a NumPy ``Generator``. No I/O and no provenance here —
provenance is attached at the scenario layer.

Beta-PERT is built from the Beta distribution because SciPy ships no ``pert``.

For a three-point estimate (minimum ``a``, most-likely ``b``, maximum ``c``) with
weight ``λ`` (classic PERT uses ``λ = 4``):

    mean      μ   = (a + λb + c) / (λ + 2)
    alpha         = 1 + λ(b − a) / (c − a)
    beta          = 1 + λ(c − b) / (c − a)
    variance      = (μ − a)(c − μ) / (λ + 3)
    sample        = a + (c − a) · Beta(alpha, beta)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

DEFAULT_PERT_WEIGHT = 4.0

# Standard normal quantile for the 90th percentile, used by the p50/p90 helper.
_Z90 = 1.2815515655446004


@runtime_checkable
class Distribution(Protocol):
    """Anything that can draw samples."""

    @property
    def mean(self) -> float: ...

    @property
    def variance(self) -> float: ...

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray: ...


@dataclass(frozen=True)
class BetaPert:
    """Bounded three-point (min / most-likely / max) distribution."""

    minimum: float
    mode: float
    maximum: float
    weight: float = DEFAULT_PERT_WEIGHT

    def __post_init__(self) -> None:
        if not (self.minimum <= self.mode <= self.maximum):
            raise ValueError("require minimum <= mode <= maximum")
        if self.weight <= 0:
            raise ValueError("weight must be positive")

    @property
    def _range(self) -> float:
        return self.maximum - self.minimum

    @property
    def is_degenerate(self) -> bool:
        return self._range == 0

    @property
    def mean(self) -> float:
        if self.is_degenerate:
            return float(self.minimum)
        return (self.minimum + self.weight * self.mode + self.maximum) / (self.weight + 2)

    @property
    def alpha(self) -> float:
        return 1.0 + self.weight * (self.mode - self.minimum) / self._range

    @property
    def beta(self) -> float:
        return 1.0 + self.weight * (self.maximum - self.mode) / self._range

    @property
    def variance(self) -> float:
        if self.is_degenerate:
            return 0.0
        mu = self.mean
        return (mu - self.minimum) * (self.maximum - mu) / (self.weight + 3)

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        if self.is_degenerate:
            return np.full(size, float(self.minimum))
        return self.minimum + self._range * rng.beta(self.alpha, self.beta, size)


@dataclass(frozen=True)
class Lognormal:
    """Lognormal with parameters on the log scale (``mu``, ``sigma``).

    Use :meth:`from_median_p90` when working from expert percentile estimates.
    """

    mu: float
    sigma: float

    def __post_init__(self) -> None:
        if self.sigma <= 0:
            raise ValueError("sigma must be positive")

    @classmethod
    def from_median_p90(cls, median: float, p90: float) -> Lognormal:
        if median <= 0 or p90 <= median:
            raise ValueError("require 0 < median < p90")
        mu = math.log(median)
        sigma = (math.log(p90) - mu) / _Z90
        return cls(mu=mu, sigma=sigma)

    @property
    def mean(self) -> float:
        return math.exp(self.mu + self.sigma**2 / 2)

    @property
    def variance(self) -> float:
        s2 = self.sigma**2
        return (math.exp(s2) - 1) * math.exp(2 * self.mu + s2)

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        return rng.lognormal(self.mu, self.sigma, size)


@dataclass(frozen=True)
class Constant:
    """A fixed value — used for known costs or fully determined parameters."""

    value: float

    @property
    def mean(self) -> float:
        return float(self.value)

    @property
    def variance(self) -> float:
        return 0.0

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        return np.full(size, float(self.value))


@dataclass(frozen=True)
class Poisson:
    """Poisson count process — e.g. the rate of independent contacts per year."""

    rate: float

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError("rate must be non-negative")

    @property
    def mean(self) -> float:
        return float(self.rate)

    @property
    def variance(self) -> float:
        return float(self.rate)

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        return rng.poisson(self.rate, size)


DistributionSpec = BetaPert | Lognormal | Constant | Poisson


def sample(spec: DistributionSpec, rng: np.random.Generator, size: int) -> np.ndarray:
    """Draw ``size`` samples from any supported distribution."""
    return spec.sample(rng, size)
