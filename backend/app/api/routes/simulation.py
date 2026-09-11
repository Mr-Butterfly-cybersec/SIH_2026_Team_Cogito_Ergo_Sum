"""Simulation endpoints: run the Monte Carlo engine on one scenario or a whole portfolio."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import EngineDep
from app.api.schemas import (
    PortfolioOutcomeModel,
    SimulateRequest,
    SimulationResponse,
)

router = APIRouter(tags=["simulation"])


@router.post("/scenarios/{scenario_id}/simulate", response_model=SimulationResponse)
def simulate_scenario(
    scenario_id: str, request: SimulateRequest, engine: EngineDep
) -> SimulationResponse:
    """Simulate one scenario, optionally with investment candidates applied."""
    if scenario_id not in engine.context.scenarios:
        raise HTTPException(status_code=404, detail=f"scenario not modelled: {scenario_id}")

    unknown = [c for c in request.controls if engine.candidate(c) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown candidates: {sorted(unknown)}")

    result = engine.simulate_scenario(
        scenario_id, request.controls, n_trials=request.n_trials, seed=request.seed
    )
    return SimulationResponse(**result.to_dict())


@router.post("/portfolio/simulate", response_model=PortfolioOutcomeModel)
def simulate_portfolio(request: SimulateRequest, engine: EngineDep) -> PortfolioOutcomeModel:
    """Simulate the whole modelled estate with a selection applied (re-simulated, not summed)."""
    unknown = [c for c in request.controls if engine.candidate(c) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown candidates: {sorted(unknown)}")

    outcome = engine.outcome(
        request.controls, label="selection", n_trials=request.n_trials, seed=request.seed
    )
    return PortfolioOutcomeModel.from_outcome(outcome)
