"""Aggregate scenario loss distributions up the organizational hierarchy.

Scenarios are treated as independent annual-loss streams; aggregating sums the per-trial
losses elementwise, which yields a valid joint sample when the scenarios were simulated
with independent randomness.
"""

from __future__ import annotations

import numpy as np

from app.risk.monte_carlo import LossSummary, ScenarioResult, summarize


def portfolio_losses(results: list[ScenarioResult]) -> np.ndarray:
    """Elementwise sum of scenario loss samples (requires equal trial counts)."""
    if not results:
        return np.zeros(0)
    counts = {r.n_trials for r in results}
    if len(counts) != 1:
        raise ValueError("all scenarios must use the same n_trials to aggregate")
    total = np.zeros(results[0].n_trials)
    for result in results:
        total = total + result.losses
    return total


def portfolio_summary(results: list[ScenarioResult], currency: str = "INR") -> LossSummary:
    """Distribution summary of the aggregated portfolio."""
    return summarize(portfolio_losses(results), currency)


def total_eal(results: list[ScenarioResult]) -> float:
    """Sum of expected annual losses (independent of aggregation method)."""
    return float(sum(r.summary.eal for r in results))
