"""Normalization taxonomy: CVSS severity bands and version fallback.

NVD's CVSS v4.0 coverage is sparse, so we always fall back
``v4.0 → v3.1 → v3.0 → v2.0`` and record which version was used.
"""

from __future__ import annotations

from typing import Any

# (metric key in NVD's `metrics` object, CVSS version)
CVSS_METRIC_PREFERENCE: tuple[tuple[str, str], ...] = (
    ("cvssMetricV40", "4.0"),
    ("cvssMetricV31", "3.1"),
    ("cvssMetricV30", "3.0"),
    ("cvssMetricV2", "2.0"),
)

# (minimum score, rating) — identical bands for CVSS v3.x and v4.0
SEVERITY_BANDS: tuple[tuple[float, str], ...] = (
    (9.0, "CRITICAL"),
    (7.0, "HIGH"),
    (4.0, "MEDIUM"),
    (0.1, "LOW"),
    (0.0, "NONE"),
)

# CVSS v2 has no Critical rating and a different Low/Medium/High split.
CVSS_V2_SEVERITY_BANDS: tuple[tuple[float, str], ...] = (
    (7.0, "HIGH"),
    (4.0, "MEDIUM"),
    (0.0, "LOW"),
)

CVSS_VERSIONS = tuple(version for _, version in CVSS_METRIC_PREFERENCE)


def severity_from_score(score: float, version: str | None = None) -> str:
    """Map a CVSS base score to its rating band for the given CVSS version."""
    if version == "2.0":
        for threshold, rating in CVSS_V2_SEVERITY_BANDS:
            if score >= threshold:
                return rating
        return "LOW"
    for threshold, rating in SEVERITY_BANDS:
        if score >= threshold:
            return rating
    return "NONE"


def pick_cvss(metrics: dict[str, Any] | None) -> tuple[str, dict[str, Any]] | None:
    """Return ``(version, metric_entry)`` using the version-preference order.

    Prefers NVD's own "Primary" analysis over vendor-provided "Secondary" scores.
    """
    if not metrics:
        return None
    for key, version in CVSS_METRIC_PREFERENCE:
        entries = metrics.get(key)
        if not entries:
            continue
        primary = next((e for e in entries if e.get("type") == "Primary"), entries[0])
        return version, primary
    return None


def attack_technique_id(external_id: str | None) -> str | None:
    """Normalize an ATT&CK external id like ``T1190`` (pass-through with validation)."""
    if not external_id:
        return None
    candidate = external_id.strip().upper()
    if len(candidate) >= 5 and candidate[0] == "T" and candidate[1:].split(".")[0].isdigit():
        return candidate
    return None
