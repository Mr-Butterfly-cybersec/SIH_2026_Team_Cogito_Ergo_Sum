"""Run the investment optimizer end to end against the demo organization.

uv run python -m app.optimization.demo
uv run python -m app.optimization.demo --budget 2500000 --trials 20000
"""

from __future__ import annotations

import argparse
import sys

from app.optimization.baseline import (
    cheapest_first,
    cvss_first,
    density_greedy,
    epss_first,
    exact_knapsack,
)
from app.optimization.candidates import candidates_from_context
from app.optimization.context import load_planning_context
from app.optimization.harness import PortfolioEvaluator
from app.optimization.portfolio import comparison_table, explain_selection
from app.optimization.solver import solve_portfolio
from app.risk.monte_carlo import DEFAULT_SEED, SimulationConfig

DEFAULT_BUDGET = 2_500_000.0


def _inr(value: float) -> str:
    return f"₹{value:,.0f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optimize the security investment portfolio.")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET)
    parser.add_argument("--trials", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    context = load_planning_context()
    candidates = candidates_from_context(context)
    evaluator = PortfolioEvaluator(
        context, candidates, SimulationConfig(n_trials=args.trials, seed=args.seed)
    )

    baseline = evaluator.baseline()
    marginals = evaluator.marginal_reductions()

    optimization = solve_portfolio(candidates, budget=args.budget, marginal_reductions=marginals)

    strategies: dict[str, tuple[str, ...]] = {
        "Optimizer (CP-SAT)": optimization.selection,
        "CVSS-first": cvss_first(candidates, context, args.budget),
        "EPSS-first": epss_first(candidates, context, args.budget),
        "Density-greedy (RR/₹)": density_greedy(candidates, args.budget, marginals),
        "Cheapest-first": cheapest_first(candidates, args.budget),
        "Exact knapsack (additive)": exact_knapsack(candidates, args.budget, marginals),
    }

    outcomes = [baseline]
    outcomes.extend(
        evaluator.evaluate(selection, label=name) for name, selection in strategies.items()
    )

    print(f"\n{context.organization_name}")
    print(
        f"Budget {_inr(args.budget)}   scenarios {len(context.scenarios)}   "
        f"candidates {len(candidates)}   trials {args.trials}   seed {args.seed}"
    )
    print("=" * 92)
    header = f"{'strategy':<28}{'sel':>4}{'spend':>14}{'EAL':>14}{'reduction':>11}{'₹/₹':>8}"
    print(header)
    print("-" * 92)
    for row in comparison_table(outcomes):
        reduction = f"{row['risk_reduction_pct']:.1f}%" if row["risk_reduction_pct"] else "n/a"
        per_rupee = (
            f"{row['risk_removed_per_rupee']:.2f}" if row["risk_removed_per_rupee"] else "n/a"
        )
        print(
            f"{row['label']:<28}{row['selected']:>4}{_inr(row['spend']):>14}"
            f"{_inr(row['eal']):>14}{reduction:>11}{per_rupee:>8}"
        )
    print("=" * 92)
    print(
        f"baseline EAL {_inr(baseline.eal)}   P90 {_inr(baseline.p90)}   P95 {_inr(baseline.p95)}"
    )

    print("\nOptimizer portfolio — why each item is funded")
    print("-" * 92)
    for item in explain_selection(optimization.selection, candidates, evaluator):
        print(f"\n  {item['control_id']}  {item['name']}")
        for step in item["chain"]:  # type: ignore[union-attr]
            print(f"      • {step}")
        if item["operational_impact"]:
            print(f"      • operational impact: {item['operational_impact']}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
