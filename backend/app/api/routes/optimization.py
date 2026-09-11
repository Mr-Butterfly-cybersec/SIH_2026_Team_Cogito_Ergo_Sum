"""Budget optimization endpoint: recommend a portfolio and compare it to the baselines."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import EngineDep
from app.api.schemas import (
    OptimizationResponse,
    OptimizationResultModel,
    OptimizeRequest,
    PortfolioOutcomeModel,
)
from app.optimization.portfolio import best_outcome, explain_selection

router = APIRouter(tags=["optimization"])


@router.post("/optimize", response_model=OptimizationResponse)
def optimize(request: OptimizeRequest, engine: EngineDep) -> OptimizationResponse:
    """Solve the budget-constrained portfolio problem and score it against the baselines.

    The solver optimizes a surrogate objective; the portfolio and every baseline are then
    scored by re-running the Monte Carlo engine, so the comparison is on true modelled risk
    reduction — never on summed nominal reductions.
    """
    result, outcomes = engine.optimize(request.budget, n_trials=request.n_trials, seed=request.seed)
    evaluator = engine.evaluator(request.n_trials, request.seed)
    explanation = explain_selection(result.selection, engine.candidates, evaluator)

    return OptimizationResponse(
        budget=request.budget,
        currency=engine.context.currency,
        result=OptimizationResultModel(**result.to_dict()),
        comparison=[PortfolioOutcomeModel.from_outcome(o) for o in outcomes],
        best_strategy=best_outcome(outcomes).label,
        explanation=explanation,
    )
