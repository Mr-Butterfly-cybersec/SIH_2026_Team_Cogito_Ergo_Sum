"""End-to-end enrichment with mocked sources."""

from __future__ import annotations

from typing import Any

import httpx

from app.ingestion.epss import EpssClient
from app.ingestion.kev import KevClient
from app.ingestion.nvd import NvdClient
from app.ingestion.service import EnrichmentService


def _handler(
    nvd_payload: dict[str, Any],
    epss_payload: dict[str, Any],
    kev_payload: dict[str, Any],
    nvd_status: int = 200,
):
    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "services.nvd.nist.gov" in url:
            if nvd_status != 200:
                return httpx.Response(nvd_status, json={"error": "boom"})
            return httpx.Response(200, json=nvd_payload)
        if "api.first.org" in url:
            return httpx.Response(200, json=epss_payload)
        if "cisa.gov" in url:
            return httpx.Response(200, json=kev_payload)
        return httpx.Response(404, json={})

    return handle


def _service(make_http, handler) -> EnrichmentService:
    return EnrichmentService(
        nvd=NvdClient(client=make_http(handler)),
        epss=EpssClient(client=make_http(handler)),
        kev=KevClient(client=make_http(handler)),
    )


def test_enrichment_joins_all_three_sources(
    make_http, nvd_payload, epss_payload, kev_payload
) -> None:
    service = _service(make_http, _handler(nvd_payload, epss_payload, kev_payload))
    records, report = service.enrich(["CVE-2021-44228"])

    record = records["CVE-2021-44228"]
    assert record.enriched is True
    assert record.kev is True
    assert record.kev_ransomware is True
    assert record.cvss is not None and record.cvss.base_score == 10.0
    assert record.epss is not None and record.epss > 0.99
    assert set(record.sources) == {"NVD", "EPSS", "CISA-KEV"}
    assert len(record.provenance) == 3

    assert report.requested == 1
    assert report.enriched == 1
    assert report.enrichment_ratio == 1.0
    assert report.with_kev == 1
    assert report.errors == []


def test_graceful_degradation_when_nvd_fails(make_http, epss_payload, kev_payload) -> None:
    handler = _handler({}, epss_payload, kev_payload, nvd_status=500)
    service = EnrichmentService(
        nvd=NvdClient(client=make_http(handler, max_retries=0)),
        epss=EpssClient(client=make_http(handler)),
        kev=KevClient(client=make_http(handler)),
    )
    records, report = service.enrich(["CVE-2021-44228"])

    assert report.errors and report.errors[0].startswith("NVD:")
    record = records["CVE-2021-44228"]
    assert record.cvss is None
    assert record.epss is not None  # EPSS still applied
    assert report.enriched == 0
    assert report.enrichment_ratio == 0.0


def test_kev_can_be_skipped(make_http, nvd_payload, epss_payload, kev_payload) -> None:
    service = _service(make_http, _handler(nvd_payload, epss_payload, kev_payload))
    records, report = service.enrich(["CVE-2021-44228"], include_kev=False)
    assert records["CVE-2021-44228"].kev is False
    assert report.with_kev == 0
    assert report.enriched == 1
