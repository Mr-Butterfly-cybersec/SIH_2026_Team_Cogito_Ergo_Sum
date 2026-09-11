"""Turn NVD CVE API items into normalized vulnerability records."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

from app.ingestion.models import CvssScore, KevEntry, VulnerabilityRecord
from app.normalization.taxonomy import pick_cvss, severity_from_score
from app.risk.provenance import Provenance, SourceType
from app.risk.schemas import ProvenanceModel

_CWE_PREFIX = "CWE-"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def english_description(item: dict[str, Any]) -> str | None:
    for description in item.get("descriptions", []) or []:
        if description.get("lang") == "en":
            return description.get("value")
    return None


def parse_cvss(metrics: dict[str, Any] | None) -> CvssScore | None:
    """Parse the best available CVSS block (v4.0 → v3.1 → v3.0 → v2.0)."""
    picked = pick_cvss(metrics)
    if picked is None:
        return None
    version, entry = picked
    data = entry.get("cvssData") or {}
    raw_score = data.get("baseScore")
    if raw_score is None:
        return None
    score = float(raw_score)
    severity = (data.get("baseSeverity") or severity_from_score(score, version)).upper()
    return CvssScore(
        version=version,
        base_score=score,
        severity=severity,
        vector=data.get("vectorString"),
        source=entry.get("source"),
        metric_type=entry.get("type"),
        exploitability_score=entry.get("exploitabilityScore"),
        impact_score=entry.get("impactScore"),
    )


def extract_cwes(item: dict[str, Any]) -> list[str]:
    found: set[str] = set()
    for weakness in item.get("weaknesses", []) or []:
        for description in weakness.get("description", []) or []:
            value = str(description.get("value", ""))
            if value.startswith(_CWE_PREFIX) and value[len(_CWE_PREFIX) :].isdigit():
                found.add(value.upper())
    return sorted(found)


def _walk_cpe_nodes(nodes: list[dict[str, Any]]) -> Iterator[str]:
    for node in nodes:
        for match in node.get("cpeMatch", []) or []:
            if match.get("vulnerable"):
                criteria = match.get("criteria")
                if criteria:
                    yield criteria
        yield from _walk_cpe_nodes(node.get("children", []) or [])


def extract_affected_cpe(item: dict[str, Any]) -> list[str]:
    criteria: set[str] = set()
    for configuration in item.get("configurations", []) or []:
        criteria.update(_walk_cpe_nodes(configuration.get("nodes", []) or []))
    return sorted(criteria)


def extract_references(item: dict[str, Any]) -> list[str]:
    return sorted({ref["url"] for ref in item.get("references", []) or [] if ref.get("url")})


def nvd_provenance(source: str = "NVD CVE API 2.0") -> ProvenanceModel:
    return ProvenanceModel(
        source_type=SourceType.PUBLIC_DATA,
        source=source,
        confidence=0.85,
        assumption_description="Official NIST National Vulnerability Database record.",
    )


def nvd_item_to_record(
    item: dict[str, Any], provenance: ProvenanceModel | None = None
) -> VulnerabilityRecord:
    """Convert a single ``vulnerabilities[i]`` element to a normalized record."""
    return VulnerabilityRecord(
        cve_id=item.get("id", ""),
        description=english_description(item),
        published=parse_datetime(item.get("published")),
        last_modified=parse_datetime(item.get("lastModified")),
        status=item.get("vulnStatus"),
        cvss=parse_cvss(item.get("metrics")),
        cwes=extract_cwes(item),
        affected_cpe=extract_affected_cpe(item),
        references=extract_references(item),
        sources=["NVD"],
        provenance=[provenance or nvd_provenance()],
    )


def apply_epss(
    record: VulnerabilityRecord,
    *,
    epss: float,
    percentile: float,
    score_date: date | None,
    source: str,
) -> VulnerabilityRecord:
    record.epss = epss
    record.epss_percentile = percentile
    record.epss_date = score_date
    if "EPSS" not in record.sources:
        record.sources.append("EPSS")
    record.provenance.append(
        ProvenanceModel(
            source_type=SourceType.PUBLIC_DATA,
            source=source,
            source_date=score_date,
            confidence=0.8,
            assumption_description="FIRST EPSS exploitation-likelihood estimate (30-day horizon).",
        )
    )
    return record


def apply_kev(record: VulnerabilityRecord, entry: KevEntry) -> VulnerabilityRecord:
    record.kev = True
    record.kev_date_added = entry.date_added
    record.kev_due_date = entry.due_date
    record.kev_ransomware = entry.known_ransomware
    record.kev_required_action = entry.required_action
    if "CISA-KEV" not in record.sources:
        record.sources.append("CISA-KEV")
    record.provenance.append(
        ProvenanceModel(
            source_type=SourceType.PUBLIC_DATA,
            source="CISA Known Exploited Vulnerabilities catalog",
            source_date=entry.date_added,
            confidence=0.9,
            assumption_description="Listed as exploited in the wild (CC0).",
        )
    )
    return record


def empty_record(cve_id: str) -> VulnerabilityRecord:
    """A placeholder so a CVE missing from NVD is still representable."""
    return VulnerabilityRecord(
        cve_id=cve_id,
        sources=[],
        provenance=[
            ProvenanceModel(
                source_type=SourceType.PUBLIC_DATA,
                source="NVD CVE API 2.0",
                confidence=0.2,
                assumption_description="CVE not found in NVD at ingestion time.",
            )
        ],
    )


def provenance_from(source_type: SourceType, source: str, **kwargs: Any) -> ProvenanceModel:
    """Small helper mirroring :class:`Provenance` for callers that need one."""
    provenance = Provenance(source_type=source_type, source=source, **kwargs)
    return ProvenanceModel(**provenance.to_dict())
