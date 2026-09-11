"""Decision metrics over risk distributions.

These are decision metrics, not accounting standards. Formulas are defined explicitly
so results are auditable.

**Guarantee: every function here returns a finite number or ``None``, never ``inf`` or
``nan``.** A denormal baseline (say ``3e-302``) or a near-zero cost can otherwise overflow
a ratio, and ``Infinity`` is not valid JSON — it would corrupt the whole response body for
any strict client. Since ``None`` is already the documented "undefined" answer, an
overflow resolves to ``None`` rather than a value no consumer can parse.
"""

from __future__ import annotations

import math


def _finite(value: float) -> float | None:
    """Return the value only if it is finite, else ``None`` (the documented undefined)."""
    return value if math.isfinite(value) else None


def risk_reduction(eal_before: float, eal_after: float) -> float:
    """Absolute reduction in expected annual loss."""
    return eal_before - eal_after


def risk_reduction_pct(eal_before: float, eal_after: float) -> float | None:
    """Reduction as a fraction of the baseline. ``None`` when the baseline is zero."""
    if eal_before <= 0:
        return None
    return _finite((eal_before - eal_after) / eal_before)


def rosi(eal_before: float, eal_after: float, annualized_cost: float) -> float | None:
    """ROSI-like return: (risk reduction − cost) / cost.

    Returns ``None`` when ``annualized_cost`` is zero (undefined).
    """
    if annualized_cost <= 0:
        return None
    return _finite((risk_reduction(eal_before, eal_after) - annualized_cost) / annualized_cost)


def risk_removed_per_unit(eal_before: float, eal_after: float, cost: float) -> float | None:
    """Rupees of modeled annual risk removed per rupee spent."""
    if cost <= 0:
        return None
    return _finite(risk_reduction(eal_before, eal_after) / cost)


def annualize(one_time_cost: float, years: float, recurring_cost: float = 0.0) -> float:
    """Spread a one-time cost over ``years`` and add any recurring annual cost."""
    if years <= 0:
        raise ValueError("years must be positive")
    return one_time_cost / years + recurring_cost
