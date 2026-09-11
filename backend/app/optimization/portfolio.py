"""Portfolio explanation and strategy comparison."""

from __future__ import annotations

from app.optimization.candidates import Candidate, candidates_by_id
from app.optimization.harness import PortfolioEvaluator, PortfolioOutcome
from app.risk.control_effect import factor_effect


def explain_selection(
    selection: tuple[str, ...] | list[str],
    candidates: list[Candidate],
    evaluator: PortfolioEvaluator,
) -> list[dict[str, object]]:
    """Per-item explanation chain: control → factor → scenarios → ₹ removed → cost."""
    by_id = candidates_by_id(candidates)
    marginals = evaluator.marginal_reductions()
    rows: list[dict[str, object]] = []

    for candidate_id in selection:
        candidate = by_id.get(candidate_id)
        if candidate is None:
            continue
        effect = factor_effect(candidate.category, candidate.target_effectiveness)
        reduction = marginals.get(candidate_id, 0.0)
        rows.append(
            {
                "candidate_id": candidate_id,
                "control_id": candidate.control_id,
                "name": candidate.name,
                "category": candidate.category.value,
                "factor": effect.factor.value,
                "factor_effect": effect.describe(),
                "scenarios": list(candidate.scenarios),
                "scenario_count": len(candidate.scenarios),
                "standalone_reduction": round(reduction, 2),
                "cost": candidate.cost,
                "annualized_cost": round(candidate.annualized_cost, 2),
                "risk_removed_per_rupee": (
                    round(reduction / candidate.cost, 4) if candidate.cost else None
                ),
                "prerequisites": [
                    by_id[p].name if p in by_id else p for p in candidate.prerequisites
                ],
                "implementation_days": candidate.implementation_days,
                "operational_impact": candidate.operational_impact,
                "chain": [
                    f"{candidate.control_id} ({candidate.category.value}) moves "
                    f"{effect.factor.value}: {effect.describe()}",
                    f"affects {len(candidate.scenarios)} scenario(s): "
                    f"{', '.join(candidate.scenarios) if candidate.scenarios else 'none'}",
                    f"standalone modelled annual risk removed ≈ {reduction:,.0f}",
                    f"cost {candidate.cost:,.0f} (annualized {candidate.annualized_cost:,.0f})",
                ],
            }
        )
    return sorted(rows, key=lambda row: float(row["standalone_reduction"]), reverse=True)  # type: ignore[arg-type]


def comparison_table(outcomes: list[PortfolioOutcome]) -> list[dict[str, object]]:
    """Compact, tabular view of several portfolios evaluated on the same footing."""
    table: list[dict[str, object]] = []
    for outcome in outcomes:
        table.append(
            {
                "label": outcome.label,
                "selected": len(outcome.selection),
                "spend": round(outcome.spend, 2),
                "eal": round(outcome.eal, 2),
                "risk_reduction": round(outcome.risk_reduction, 2),
                "risk_reduction_pct": (
                    round(outcome.risk_reduction_pct * 100, 2)
                    if outcome.risk_reduction_pct is not None
                    else None
                ),
                "rosi": round(outcome.rosi, 3) if outcome.rosi is not None else None,
                "risk_removed_per_rupee": (
                    round(outcome.risk_removed_per_rupee, 3)
                    if outcome.risk_removed_per_rupee is not None
                    else None
                ),
            }
        )
    return table


def best_outcome(outcomes: list[PortfolioOutcome]) -> PortfolioOutcome:
    return max(outcomes, key=lambda outcome: outcome.risk_reduction)
