"""NVD client: parsing, rate-limit headers, pagination, retries."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.ingestion.nvd import NvdClient
from tests.helpers import nvd_item


def test_get_cve_parses_and_uses_v31_fallback(make_http, nvd_payload) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["cveId"] == "CVE-2021-44228"
        return httpx.Response(200, json=nvd_payload)

    record = NvdClient(client=make_http(handler)).get_cve("CVE-2021-44228")
    assert record is not None
    assert record.cvss is not None
    assert record.cvss.version == "3.1"
    assert record.cvss.base_score == 10.0
    assert record.cvss.severity == "CRITICAL"
    assert record.description is not None and record.description.startswith("Apache Log4j2")
    assert "NVD" in record.sources
    assert record.enriched is False  # no EPSS yet


def test_api_key_is_sent_as_header(make_http) -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["apiKey"] = request.headers.get("apiKey")
        return httpx.Response(200, json={"vulnerabilities": []})

    assert (
        NvdClient(api_key="secret-key", client=make_http(handler)).get_cve("CVE-0000-0000") is None
    )
    assert seen["apiKey"] == "secret-key"


def test_missing_cve_returns_none(make_http) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"vulnerabilities": []})

    assert NvdClient(client=make_http(handler)).get_cve("CVE-0000-0000") is None


def test_get_cves_returns_placeholder_for_unknown(make_http) -> None:
    payload = {"vulnerabilities": [nvd_item("CVE-2024-0001")]}

    def handler(request: httpx.Request) -> httpx.Response:
        requested = request.url.params["cveId"]
        if requested == "CVE-2024-0001":
            return httpx.Response(200, json=payload)
        return httpx.Response(200, json={"vulnerabilities": []})

    records = NvdClient(client=make_http(handler)).get_cves(["CVE-2024-0001", "CVE-9999-9999"])
    assert records["CVE-2024-0001"].cvss is not None
    assert records["CVE-9999-9999"].cvss is None
    assert records["CVE-9999-9999"].sources == []


def test_iter_modified_paginates(make_http) -> None:
    pages = {
        0: [nvd_item("CVE-2024-0001"), nvd_item("CVE-2024-0002")],
        2: [nvd_item("CVE-2024-0003")],
    }
    seen_params: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        seen_params.append(params)
        start = int(params["startIndex"])
        if start not in pages:
            return httpx.Response(200, json={"vulnerabilities": [], "totalResults": 3})
        return httpx.Response(
            200,
            json={"vulnerabilities": pages[start], "totalResults": 3, "resultsPerPage": 2},
        )

    client = NvdClient(client=make_http(handler), page_size=2)
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    ids = [record.cve_id for record in client.iter_modified(start, end)]

    assert ids == ["CVE-2024-0001", "CVE-2024-0002", "CVE-2024-0003"]
    assert "lastModStartDate" in seen_params[0]
    assert seen_params[0]["resultsPerPage"] == "2"
    assert len(seen_params) == 2


def test_retries_transient_failure_then_succeeds(make_http) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"vulnerabilities": []})

    client = NvdClient(client=make_http(handler, max_retries=2))
    assert client.get_cve("CVE-0000-0000") is None
    assert calls["count"] == 2
