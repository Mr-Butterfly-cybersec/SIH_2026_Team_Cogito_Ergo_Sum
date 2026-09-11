"""CVSS fallback, severity bands, and NVD item parsing."""

from __future__ import annotations

from datetime import date, datetime

from app.normalization.taxonomy import pick_cvss, severity_from_score
from app.normalization.vulnerabilities import (
    extract_affected_cpe,
    extract_cwes,
    nvd_item_to_record,
    parse_cvss,
    parse_date,
    parse_datetime,
)
from tests.helpers import load_fixture


def test_severity_bands() -> None:
    assert severity_from_score(10.0) == "CRITICAL"
    assert severity_from_score(9.0) == "CRITICAL"
    assert severity_from_score(8.9) == "HIGH"
    assert severity_from_score(7.0) == "HIGH"
    assert severity_from_score(6.9) == "MEDIUM"
    assert severity_from_score(4.0) == "MEDIUM"
    assert severity_from_score(3.9) == "LOW"
    assert severity_from_score(0.1) == "LOW"
    assert severity_from_score(0.0) == "NONE"


def test_severity_is_version_aware_for_v2() -> None:
    # CVSS v2 has no Critical rating
    assert severity_from_score(9.3, "2.0") == "HIGH"
    assert severity_from_score(9.3, "3.1") == "CRITICAL"
    assert severity_from_score(0.0, "2.0") == "LOW"


def test_cvss_prefers_v4_over_v31() -> None:
    payload = load_fixture("nvd_cve_44228.json")
    item = payload["vulnerabilities"][0]["cve"]
    item["metrics"]["cvssMetricV40"] = [
        {
            "source": "nvd@nist.gov",
            "type": "Primary",
            "cvssData": {
                "version": "4.0",
                "baseScore": 9.3,
                "baseSeverity": "CRITICAL",
                "vectorString": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H",
            },
        }
    ]
    cvss = parse_cvss(item["metrics"])
    assert cvss is not None
    assert cvss.version == "4.0"
    assert cvss.base_score == 9.3


def test_v2_without_base_severity_is_rated_from_score() -> None:
    metrics = {
        "cvssMetricV2": [
            {"source": "x", "type": "Primary", "cvssData": {"version": "2.0", "baseScore": 9.3}}
        ]
    }
    cvss = parse_cvss(metrics)
    assert cvss is not None
    assert cvss.version == "2.0"
    assert cvss.severity == "HIGH"


def test_primary_metric_preferred_over_secondary() -> None:
    metrics = {
        "cvssMetricV31": [
            {
                "source": "vendor",
                "type": "Secondary",
                "cvssData": {"version": "3.1", "baseScore": 5.0, "baseSeverity": "MEDIUM"},
            },
            {
                "source": "nvd@nist.gov",
                "type": "Primary",
                "cvssData": {"version": "3.1", "baseScore": 9.8, "baseSeverity": "CRITICAL"},
            },
        ]
    }
    cvss = parse_cvss(metrics)
    assert cvss is not None and cvss.base_score == 9.8


def test_parse_cvss_edge_cases() -> None:
    assert parse_cvss(None) is None
    assert parse_cvss({}) is None
    assert pick_cvss({}) is None
    assert (
        parse_cvss({"cvssMetricV31": [{"type": "Primary", "cvssData": {"version": "3.1"}}]}) is None
    )


def test_cwes_filter_placeholders(nvd_payload) -> None:
    item = nvd_payload["vulnerabilities"][0]["cve"]
    assert extract_cwes(item) == ["CWE-400", "CWE-502"]


def test_cpe_extraction_walks_nested_nodes() -> None:
    item = {
        "configurations": [
            {
                "nodes": [
                    {
                        "cpeMatch": [
                            {"vulnerable": True, "criteria": "cpe:2.3:o:a:b:2"},
                            {"vulnerable": False, "criteria": "cpe:2.3:o:skip:me"},
                        ],
                        "children": [
                            {"cpeMatch": [{"vulnerable": True, "criteria": "cpe:2.3:a:x:y:1"}]}
                        ],
                    }
                ]
            }
        ]
    }
    assert extract_affected_cpe(item) == ["cpe:2.3:a:x:y:1", "cpe:2.3:o:a:b:2"]


def test_nvd_item_to_record_full(nvd_payload) -> None:
    item = nvd_payload["vulnerabilities"][0]["cve"]
    record = nvd_item_to_record(item)
    assert record.cve_id == "CVE-2021-44228"
    assert record.status == "Analyzed"
    assert record.published is not None and record.published.year == 2021
    assert record.references == ["https://logging.apache.org/log4j/2.x/security.html"]
    assert record.affected_cpe == ["cpe:2.3:a:apache:log4j:*:*:*:*:*:*:*:*"]
    assert record.provenance[0].source_type.value == "PUBLIC_DATA"


def test_parse_datetime_and_date_helpers() -> None:
    parsed = parse_datetime("2021-12-10T10:15:09Z")
    assert parsed is not None and parsed.year == 2021 and parsed.tzinfo is not None
    assert parse_datetime("2021-12-10T10:15:09.143") == datetime(2021, 12, 10, 10, 15, 9, 143000)
    assert parse_datetime("not-a-date") is None
    assert parse_date("2026-09-10T00:00:00Z") == date(2026, 9, 10)
    assert parse_date(None) is None
