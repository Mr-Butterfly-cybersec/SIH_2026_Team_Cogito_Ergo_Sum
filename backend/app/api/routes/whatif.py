"""What-if endpoints: control rollout, remediation delay, and criticality change."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import EngineDep
from app.api.schemas import (
    CriticalityImpactResponse,
    CriticalityRequest,
    DelayImpactResponse,
    DelayRequest,
    SimulateRequest,
    SimulationResponse,
)
from app.risk.asset_criticality import DIMENSION_MAX, DIMENSION_MIN, DIMENSIONS

router = APIRouter(tags=["what-if"])


def _validate_candidates(engine, controls: list[str]) -> None:
    unknown = [c for c in controls if engine.candidate(c) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown candidates: {sorted(unknown)}")


def _require_scenario(engine, scenario_id: str) -> None:
    if scenario_id not in engine.context.scenarios:
        raise HTTPException(status_code=404, detail=f"scenario not modelled: {scenario_id}")


@router.post("/what-if/scenarios/{scenario_id}/controls", response_model=SimulationResponse)
def what_if_controls(
    scenario_id: str, request: SimulateRequest, engine: EngineDep
) -> SimulationResponse:
    """'What if we deploy these controls?' — re-simulate the scenario hardened."""
    _require_scenario(engine, scenario_id)
    _validate_candidates(engine, request.controls)
    result = engine.simulate_scenario(
        scenario_id, request.controls, n_trials=request.n_trials, seed=request.seed
    )
    return SimulationResponse(**result.to_dict())


@router.post("/what-if/scenarios/{scenario_id}/delay", response_model=DelayImpactResponse)
def what_if_delay(
    scenario_id: str, request: DelayRequest, engine: EngineDep
) -> DelayImpactResponse:
    """'What if remediation is delayed N days?' — the loss exposed by postponing."""
    _require_scenario(engine, scenario_id)
    _validate_candidates(engine, request.controls)
    impact = engine.delay_impact(
        scenario_id,
        request.controls,
        request.days,
        n_trials=request.n_trials,
        seed=request.seed,
    )
    return DelayImpactResponse(**impact.to_dict())


@router.post(
    "/what-if/scenarios/{scenario_id}/criticality", response_model=CriticalityImpactResponse
)
def what_if_criticality(
    scenario_id: str, request: CriticalityRequest, engine: EngineDep
) -> CriticalityImpactResponse:
    """'What if this asset becomes more critical?' — re-materialize and re-simulate."""
    _require_scenario(engine, scenario_id)

    unknown = sorted(set(request.overrides) - set(DIMENSIONS))
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown criticality dimensions: {unknown}")
    out_of_range = {
        dimension: value
        for dimension, value in request.overrides.items()
        if not DIMENSION_MIN <= value <= DIMENSION_MAX
    }
    if out_of_range:
        raise HTTPException(
            status_code=422,
            detail=(
                f"criticality values must be within "
                f"[{DIMENSION_MIN}, {DIMENSION_MAX}]: {out_of_range}"
            ),
        )

    impact = engine.criticality_impact(
        scenario_id, request.overrides, n_trials=request.n_trials, seed=request.seed
    )
    return CriticalityImpactResponse(**impact.to_dict())
