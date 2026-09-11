"""Security-investment optimization: candidates, evaluation harness, solver, baselines."""

from app.optimization.baseline import (
    brute_force,
    cheapest_first,
    cvss_first,
    density_greedy,
    epss_first,
    exact_knapsack,
    random_selection,
)
from app.optimization.candidates import (
    Candidate,
    candidates_by_id,
    candidates_from_context,
)
from app.optimization.context import (
    ControlContext,
    PlanningContext,
    ScenarioCatalogueEntry,
    load_planning_context,
)
from app.optimization.harness import (
    PortfolioEvaluator,
    PortfolioOutcome,
    ScenarioOutcome,
)
from app.optimization.portfolio import (
    best_outcome,
    comparison_table,
    explain_selection,
)
from app.optimization.solver import (
    OptimizationResult,
    overlap_penalty,
    solve_portfolio,
    surrogate_value,
)

__all__ = [
    "Candidate",
    "ControlContext",
    "OptimizationResult",
    "PlanningContext",
    "PortfolioEvaluator",
    "PortfolioOutcome",
    "ScenarioCatalogueEntry",
    "ScenarioOutcome",
    "best_outcome",
    "brute_force",
    "candidates_by_id",
    "candidates_from_context",
    "cheapest_first",
    "comparison_table",
    "cvss_first",
    "density_greedy",
    "epss_first",
    "exact_knapsack",
    "explain_selection",
    "load_planning_context",
    "overlap_penalty",
    "random_selection",
    "solve_portfolio",
    "surrogate_value",
]
