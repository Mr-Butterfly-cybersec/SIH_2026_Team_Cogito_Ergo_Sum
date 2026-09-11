"""Framework coverage and gap analysis.

Coverage is computed from the **real** controls in the planning context, using their
measured effectiveness — not from a checklist somebody ticked. Each canonical requirement
resolves to:

* **coverage** in ``[0, 1]`` — the combined effectiveness of the controls contributing to it;
* **status** — ``COVERED`` / ``PARTIAL`` / ``GAP``;
* **exposure** — the modelled annual loss sitting in the scenarios those controls protect;
* **closable_by** — the investment candidates that would raise those controls to target.

The exposure column is the point of the whole exercise: it turns a compliance gap into a
rupee figure, so the gap can compete for budget against every other risk on the same terms.

Combining controls assumes their failures are independent, i.e.
``coverage = 1 - Π(1 - effectiveness_i)``. This is a first-order approximation and is
labelled as such in the UI, consistent with the note in ``app.risk.control_effect``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.compliance.catalog import (
    REQUIREMENTS,
    CanonicalRequirement,
    SecurityFunction,
)
from app.compliance.frameworks import CATALOG_VERSION, FRAMEWORKS, Framework
from app.compliance.mapping import (
    controls_for_requirement,
    unmapped_controls,
    unmapped_requirements,
)
from app.optimization.candidates import candidate_id_for
from app.optimization.context import PlanningContext

COVERED_THRESHOLD = 0.70
PARTIAL_THRESHOLD = 0.35


class CoverageStatus(StrEnum):
    COVERED = "COVERED"
    PARTIAL = "PARTIAL"
    GAP = "GAP"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def combined_coverage(effectiveness: list[float]) -> float:
    """Probability at least one control is effective, assuming independence."""
    remaining = 1.0
    for value in effectiveness:
        remaining *= 1.0 - max(0.0, min(1.0, value))
    return 1.0 - remaining


def status_for(coverage: float, controlled: bool) -> CoverageStatus:
    if not controlled:
        return CoverageStatus.GAP
    if coverage >= COVERED_THRESHOLD:
        return CoverageStatus.COVERED
    if coverage >= PARTIAL_THRESHOLD:
        return CoverageStatus.PARTIAL
    return CoverageStatus.GAP


@dataclass(frozen=True)
class ControlContribution:
    control_id: str
    name: str
    effectiveness: float
    category: str

    def to_dict(self) -> dict[str, object]:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "effectiveness": round(self.effectiveness, 4),
            "category": self.category,
        }


@dataclass(frozen=True)
class RequirementCoverage:
    requirement: CanonicalRequirement
    references: tuple[str, ...]
    coverage: float
    status: CoverageStatus
    contributions: tuple[ControlContribution, ...]
    scenarios: tuple[str, ...]
    exposure: float
    closable_by: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.requirement.id,
            "name": self.requirement.name,
            "objective": self.requirement.objective,
            "function": self.requirement.function.value,
            "categories": [c.value for c in self.requirement.categories],
            "references": list(self.references),
            "coverage": round(self.coverage, 4),
            "status": self.status.value,
            "controls": [c.to_dict() for c in self.contributions],
            "scenarios": list(self.scenarios),
            "exposure": round(self.exposure, 2),
            "closable_by": list(self.closable_by),
            "note": self.requirement.note,
        }


@dataclass(frozen=True)
class FunctionCoverage:
    function: SecurityFunction
    coverage: float
    requirements: int
    gaps: int

    def to_dict(self) -> dict[str, object]:
        return {
            "function": self.function.value,
            "coverage": round(self.coverage, 4),
            "requirements": self.requirements,
            "gaps": self.gaps,
        }


@dataclass(frozen=True)
class FrameworkCoverage:
    framework: Framework
    requirements: tuple[RequirementCoverage, ...]
    coverage: float
    covered: int
    partial: int
    gaps: int
    gap_exposure: float
    functions: tuple[FunctionCoverage, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "framework": self.framework.to_dict(),
            "coverage": round(self.coverage, 4),
            "counts": {
                "covered": self.covered,
                "partial": self.partial,
                "gaps": self.gaps,
                "requirements": len(self.requirements),
            },
            "gap_exposure": round(self.gap_exposure, 2),
            "functions": [f.to_dict() for f in self.functions],
            "requirements": [r.to_dict() for r in self.requirements],
        }


@dataclass(frozen=True)
class ComplianceReport:
    organization: str
    currency: str
    catalog_version: str
    overall_coverage: float
    frameworks: tuple[FrameworkCoverage, ...]
    top_gaps: tuple[RequirementCoverage, ...]
    unmapped_controls: tuple[str, ...]
    unmapped_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "organization": self.organization,
            "currency": self.currency,
            "catalog_version": self.catalog_version,
            "overall_coverage": round(self.overall_coverage, 4),
            "frameworks": [f.to_dict() for f in self.frameworks],
            "top_gaps": [g.to_dict() for g in self.top_gaps],
            "unmapped_controls": list(self.unmapped_controls),
            "unmapped_requirements": list(self.unmapped_requirements),
        }


def _requirement_coverage(
    context: PlanningContext,
    requirement: CanonicalRequirement,
    framework_id: str,
    exposure_by_scenario: dict[str, float],
    candidate_ids: frozenset[str],
) -> RequirementCoverage:
    mapped = controls_for_requirement(requirement.id)
    contributions: list[ControlContribution] = []
    scenarios: set[str] = set()
    closable: list[str] = []

    for control_id in mapped:
        control = context.controls.get(control_id)
        if control is None:
            continue
        contributions.append(
            ControlContribution(
                control_id=control.control_id,
                name=control.name,
                effectiveness=control.effectiveness,
                category=control.category.value,
            )
        )
        scenarios.update(control.protects)
        candidate_id = candidate_id_for(control_id)
        if candidate_id in candidate_ids:
            closable.append(candidate_id)

    effectiveness = [c.effectiveness for c in contributions]
    coverage = combined_coverage(effectiveness) if effectiveness else 0.0
    ordered_scenarios = tuple(sorted(scenarios))

    return RequirementCoverage(
        requirement=requirement,
        references=requirement.reference_for(framework_id),
        coverage=coverage,
        status=status_for(coverage, bool(contributions)),
        contributions=tuple(contributions),
        scenarios=ordered_scenarios,
        exposure=sum(exposure_by_scenario.get(sid, 0.0) for sid in ordered_scenarios),
        closable_by=tuple(sorted(set(closable))),
    )


def _function_rollup(rows: list[RequirementCoverage]) -> tuple[FunctionCoverage, ...]:
    grouped: dict[SecurityFunction, list[RequirementCoverage]] = {}
    for row in rows:
        grouped.setdefault(row.requirement.function, []).append(row)

    out: list[FunctionCoverage] = []
    for function in SecurityFunction:
        members = grouped.get(function)
        if not members:
            continue
        out.append(
            FunctionCoverage(
                function=function,
                coverage=sum(m.coverage for m in members) / len(members),
                requirements=len(members),
                gaps=sum(1 for m in members if m.status is CoverageStatus.GAP),
            )
        )
    return tuple(out)


def build_report(
    context: PlanningContext,
    exposure_by_scenario: dict[str, float],
    *,
    catalog_version: str = CATALOG_VERSION,
    top_gap_limit: int = 8,
) -> ComplianceReport:
    """Compute coverage for every framework from the organization's real controls."""
    candidate_ids = frozenset(candidate_id_for(control_id) for control_id in context.controls)

    all_rows: dict[str, RequirementCoverage] = {}
    frameworks: list[FrameworkCoverage] = []

    for framework in FRAMEWORKS:
        rows: list[RequirementCoverage] = []
        for requirement in REQUIREMENTS:
            if not requirement.reference_for(framework.id):
                continue
            row = _requirement_coverage(
                context, requirement, framework.id, exposure_by_scenario, candidate_ids
            )
            rows.append(row)
            all_rows[requirement.id] = row

        if not rows:
            continue

        gaps = [r for r in rows if r.status is CoverageStatus.GAP]
        frameworks.append(
            FrameworkCoverage(
                framework=framework,
                requirements=tuple(rows),
                coverage=sum(r.coverage for r in rows) / len(rows),
                covered=sum(1 for r in rows if r.status is CoverageStatus.COVERED),
                partial=sum(1 for r in rows if r.status is CoverageStatus.PARTIAL),
                gaps=len(gaps),
                gap_exposure=sum(r.exposure for r in gaps),
                functions=_function_rollup(rows),
            )
        )

    top_gaps = tuple(
        sorted(
            (r for r in all_rows.values() if r.status is not CoverageStatus.COVERED),
            key=lambda r: (r.exposure, 1.0 - r.coverage),
            reverse=True,
        )[:top_gap_limit]
    )

    return ComplianceReport(
        organization=context.organization_name,
        currency=context.currency,
        catalog_version=catalog_version,
        overall_coverage=(
            sum(r.coverage for r in all_rows.values()) / len(all_rows) if all_rows else 0.0
        ),
        frameworks=tuple(frameworks),
        top_gaps=top_gaps,
        unmapped_controls=unmapped_controls(list(context.controls)),
        unmapped_requirements=unmapped_requirements(),
    )


__all__ = [
    "COVERED_THRESHOLD",
    "PARTIAL_THRESHOLD",
    "ComplianceReport",
    "ControlContribution",
    "CoverageStatus",
    "FrameworkCoverage",
    "FunctionCoverage",
    "RequirementCoverage",
    "build_report",
    "combined_coverage",
    "status_for",
]
