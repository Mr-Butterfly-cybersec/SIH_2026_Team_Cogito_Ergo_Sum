"""Normalization: turn source-specific data into the canonical internal model."""

from app.normalization.taxonomy import (
    CVSS_METRIC_PREFERENCE,
    CVSS_VERSIONS,
    SEVERITY_BANDS,
    severity_from_score,
)
from app.normalization.vulnerabilities import (
    apply_epss,
    apply_kev,
    parse_cvss,
    parse_date,
    parse_datetime,
)

__all__ = [
    "CVSS_METRIC_PREFERENCE",
    "CVSS_VERSIONS",
    "SEVERITY_BANDS",
    "apply_epss",
    "apply_kev",
    "parse_cvss",
    "parse_date",
    "parse_datetime",
    "severity_from_score",
]
