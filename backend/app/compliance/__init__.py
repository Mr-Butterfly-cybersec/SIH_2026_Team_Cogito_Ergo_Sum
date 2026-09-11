"""Framework mapping: one internal control ontology, many frameworks.

Curated and versioned — no LLM-generated regulatory mappings.
"""

from app.compliance.catalog import (
    FUNCTIONS,
    REQUIREMENTS,
    REQUIREMENTS_BY_ID,
    CanonicalRequirement,
    SecurityFunction,
    get_requirement,
    requirements_for_framework,
)
from app.compliance.coverage import (
    COVERED_THRESHOLD,
    PARTIAL_THRESHOLD,
    ComplianceReport,
    ControlContribution,
    CoverageStatus,
    FrameworkCoverage,
    FunctionCoverage,
    RequirementCoverage,
    build_report,
    combined_coverage,
    status_for,
)
from app.compliance.frameworks import (
    CATALOG_VERSION,
    FRAMEWORKS,
    FRAMEWORKS_BY_ID,
    INDIAN_REGULATORS,
    Framework,
    FrameworkKind,
    get_framework,
)
from app.compliance.mapping import (
    CONTROL_REQUIREMENTS,
    REQUIREMENT_CONTROLS,
    controls_for_requirement,
    requirements_for_control,
    unmapped_controls,
    unmapped_requirements,
)

__all__ = [
    "CATALOG_VERSION",
    "CONTROL_REQUIREMENTS",
    "COVERED_THRESHOLD",
    "ComplianceReport",
    "ControlContribution",
    "CoverageStatus",
    "FRAMEWORKS",
    "FRAMEWORKS_BY_ID",
    "FUNCTIONS",
    "Framework",
    "FrameworkCoverage",
    "FrameworkKind",
    "FunctionCoverage",
    "INDIAN_REGULATORS",
    "PARTIAL_THRESHOLD",
    "REQUIREMENTS",
    "REQUIREMENTS_BY_ID",
    "REQUIREMENT_CONTROLS",
    "CanonicalRequirement",
    "RequirementCoverage",
    "SecurityFunction",
    "build_report",
    "combined_coverage",
    "controls_for_requirement",
    "get_framework",
    "get_requirement",
    "requirements_for_control",
    "requirements_for_framework",
    "status_for",
    "unmapped_controls",
    "unmapped_requirements",
]
