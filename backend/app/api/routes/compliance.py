"""Compliance endpoints: one internal ontology mapped to seven frameworks.

Coverage is computed from the organization's real controls and their measured
effectiveness, and every gap carries the rupee exposure of the scenarios it relates to —
so a compliance gap can compete for budget on the same terms as any other risk.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import EngineDep
from app.api.schemas import (
    ComplianceReportModel,
    FrameworkCoverageModel,
    FrameworkModel,
    RequirementCoverageModel,
    RequirementModel,
)
from app.compliance import (
    FRAMEWORKS,
    REQUIREMENTS_BY_ID,
    get_framework,
    requirements_for_framework,
)
from app.compliance.coverage import CoverageStatus
from app.compliance.mapping import controls_for_requirement
from app.risk.monte_carlo import DEFAULT_SEED, DEFAULT_TRIALS

router = APIRouter(tags=["compliance"])


@router.get("/compliance", response_model=ComplianceReportModel)
def compliance_report(
    engine: EngineDep,
    n_trials: int = Query(default=DEFAULT_TRIALS, ge=100, le=500_000),
    seed: int = Query(default=DEFAULT_SEED, ge=0),
) -> ComplianceReportModel:
    """Coverage against every framework, plus the gaps ranked by modelled rupee exposure."""
    return ComplianceReportModel(**engine.compliance_report(n_trials, seed).to_dict())


@router.get("/compliance/frameworks", response_model=list[FrameworkModel])
def list_frameworks() -> list[FrameworkModel]:
    """The framework registry, with the version each mapping was transcribed from."""
    return [FrameworkModel(**framework.to_dict()) for framework in FRAMEWORKS]


@router.get("/compliance/frameworks/{framework_id}", response_model=FrameworkCoverageModel)
def framework_coverage(
    framework_id: str,
    engine: EngineDep,
    n_trials: int = Query(default=DEFAULT_TRIALS, ge=100, le=500_000),
    seed: int = Query(default=DEFAULT_SEED, ge=0),
) -> FrameworkCoverageModel:
    """Coverage against a single framework."""
    report = engine.compliance_report(n_trials, seed)
    for entry in report.frameworks:
        if entry.framework.id == framework_id:
            return FrameworkCoverageModel(**entry.to_dict())
    raise HTTPException(status_code=404, detail=f"unknown framework: {framework_id}")


@router.get("/compliance/requirements", response_model=list[RequirementModel])
def list_requirements(framework_id: str | None = None) -> list[RequirementModel]:
    """The internal ontology — each canonical requirement and all of its framework refs."""
    requirements = (
        requirements_for_framework(framework_id)
        if framework_id
        else tuple(REQUIREMENTS_BY_ID.values())
    )
    if framework_id and not requirements:
        raise HTTPException(status_code=404, detail=f"unknown framework: {framework_id}")
    return [
        RequirementModel(
            **requirement.to_dict(),
            controls=list(controls_for_requirement(requirement.id)),
        )
        for requirement in requirements
    ]


@router.get("/compliance/gaps", response_model=list[RequirementCoverageModel])
def list_gaps(
    engine: EngineDep,
    limit: int = Query(default=10, ge=1, le=100),
    framework_id: str | None = None,
    function: str | None = None,
    n_trials: int = Query(default=DEFAULT_TRIALS, ge=100, le=500_000),
    seed: int = Query(default=DEFAULT_SEED, ge=0),
) -> list[RequirementCoverageModel]:
    """Gaps and partial coverage, ranked by the rupee exposure they relate to."""
    report = engine.compliance_report(n_trials, seed)

    if framework_id is not None:
        if get_framework(framework_id) is None:
            raise HTTPException(status_code=404, detail=f"unknown framework: {framework_id}")
        entry = next(f for f in report.frameworks if f.framework.id == framework_id)
        rows = [r for r in entry.requirements if r.status is not CoverageStatus.COVERED]
    else:
        rows = [r for r in report.top_gaps]

    if function is not None:
        rows = [r for r in rows if r.requirement.function.value.lower() == function.lower()]

    rows = sorted(rows, key=lambda r: (r.exposure, 1.0 - r.coverage), reverse=True)
    return [RequirementCoverageModel(**row.to_dict()) for row in rows[:limit]]
