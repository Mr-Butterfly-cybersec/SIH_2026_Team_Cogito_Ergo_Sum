"""Baseline strategies to benchmark the optimizer against.

All baselines produce *feasible* portfolios: prerequisites are pulled in as needed and
nothing is added that would break the budget. They differ only in how they rank options —
which is exactly the point of the comparison.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable

from app.optimization.candidates import Candidate, candidates_by_id
from app.optimization.context import PlanningContext
from app.optimization.harness import PortfolioEvaluator


class SelectionBuilder:
    """Greedily builds a budget-feasible selection, pulling in prerequisites."""

    def __init__(self, candidates: list[Candidate], budget: float) -> None:
        self.by_id = candidates_by_id(candidates)
        self.budget = budget
        self.chosen: set[str] = set()

    def spend(self) -> float:
        return sum(self.by_id[cid].cost for cid in self.chosen)

    def closure(self, candidate_id: str) -> set[str]:
        needed: set[str] = set()
        stack = [candidate_id]
        while stack:
            current = stack.pop()
            if current in needed or current not in self.by_id:
                continue
            needed.add(current)
            stack.extend(self.by_id[current].prerequisites)
        return needed

    def try_add(self, candidate_id: str) -> bool:
        if candidate_id not in self.by_id:
            return False
        needed = self.closure(candidate_id)
        extra = sum(self.by_id[cid].cost for cid in needed - self.chosen)
        if self.spend() + extra > self.budget:
            return False
        self.chosen |= needed
        return True

    def result(self) -> tuple[str, ...]:
        return tuple(sorted(self.chosen))


def _build(candidates: list[Candidate], budget: float, order: Iterable[str]) -> tuple[str, ...]:
    builder = SelectionBuilder(candidates, budget)
    for candidate in candidates:
        if candidate.mandatory:
            builder.try_add(candidate.id)
    for candidate_id in order:
        builder.try_add(candidate_id)
    return builder.result()


def _cvss_rank(context: PlanningContext, candidate: Candidate) -> float:
    scores = [context.scenario_cvss(sid) or 0.0 for sid in candidate.scenarios]
    return max(scores) if scores else 0.0


def _epss_rank(context: PlanningContext, candidate: Candidate) -> float:
    scores = [context.scenario_epss(sid) or 0.0 for sid in candidate.scenarios]
    return max(scores) if scores else 0.0


def cvss_first(
    candidates: list[Candidate], context: PlanningContext, budget: float
) -> tuple[str, ...]:
    """Patch the highest-CVSS exposures first, ignoring cost and business context."""
    ranked = sorted(candidates, key=lambda c: _cvss_rank(context, c), reverse=True)
    return _build(candidates, budget, [c.id for c in ranked])


def epss_first(
    candidates: list[Candidate], context: PlanningContext, budget: float
) -> tuple[str, ...]:
    """Broaden the most-likely-to-be-exploited exposures first."""
    ranked = sorted(candidates, key=lambda c: _epss_rank(context, c), reverse=True)
    return _build(candidates, budget, [c.id for c in ranked])


def density_greedy(
    candidates: list[Candidate], budget: float, marginal_reductions: dict[str, float]
) -> tuple[str, ...]:
    """Risk reduction per rupee, greedily — the standard knapsack heuristic."""
    ranked = sorted(
        candidates,
        key=lambda c: (marginal_reductions.get(c.id, 0.0) / c.cost) if c.cost else float("inf"),
        reverse=True,
    )
    return _build(candidates, budget, [c.id for c in ranked])


def cheapest_first(candidates: list[Candidate], budget: float) -> tuple[str, ...]:
    ranked = sorted(candidates, key=lambda c: c.cost)
    return _build(candidates, budget, [c.id for c in ranked])


def random_selection(
    candidates: list[Candidate], budget: float, *, seed: int = 0
) -> tuple[str, ...]:
    shuffled = list(candidates)
    random.Random(seed).shuffle(shuffled)
    return _build(candidates, budget, [c.id for c in shuffled])


def exact_knapsack(
    candidates: list[Candidate],
    budget: float,
    marginal_reductions: dict[str, float],
    *,
    step: float = 1_000.0,
) -> tuple[str, ...]:
    """Exact optimum of the *additive* relaxation (dynamic programming over budget).

    Then made feasible by pulling in prerequisites within budget.
    """
    if not candidates:
        return ()
    capacity = int(budget // step)
    best = [0.0] * (capacity + 1)
    take: list[list[str]] = [[] for _ in range(capacity + 1)]

    for candidate in candidates:
        cost_units = int(round(candidate.cost / step))
        gain = marginal_reductions.get(candidate.id, 0.0)
        if cost_units <= 0:
            continue
        for units in range(capacity, cost_units - 1, -1):
            candidate_total = best[units - cost_units] + gain
            if candidate_total > best[units]:
                best[units] = candidate_total
                take[units] = [*take[units - cost_units], candidate.id]

    chosen = take[capacity]
    return _build(candidates, budget, chosen)


def best_by(
    strategies: dict[str, tuple[str, ...]],
    evaluator: PortfolioEvaluator,
    key: Callable[[float], float] | None = None,
) -> str:
    """Name of the strategy with the greatest true (re-simulated) risk reduction."""
    scores = {
        name: evaluator.evaluate(selection).risk_reduction for name, selection in strategies.items()
    }
    return max(scores, key=lambda name: scores[name] if key is None else key(scores[name]))


def brute_force(
    candidates: list[Candidate],
    budget: float,
    evaluator: PortfolioEvaluator,
    *,
    max_candidates: int = 12,
) -> tuple[str, ...] | None:
    """Exact optimum under the *true* re-simulated objective, for small instances only."""
    if len(candidates) > max_candidates:
        return None
    by_id = candidates_by_id(candidates)
    best_selection: tuple[str, ...] = ()
    best_reduction = -1.0

    for mask in range(1 << len(candidates)):
        selection = tuple(
            sorted(candidates[i].id for i in range(len(candidates)) if mask & (1 << i))
        )
        spend = sum(by_id[cid].cost for cid in selection)
        if spend > budget:
            continue
        if any(
            prerequisite not in selection
            for cid in selection
            for prerequisite in by_id[cid].prerequisites
        ):
            continue
        reduction = evaluator.evaluate(selection).risk_reduction
        if reduction > best_reduction:
            best_reduction = reduction
            best_selection = selection

    return best_selection
