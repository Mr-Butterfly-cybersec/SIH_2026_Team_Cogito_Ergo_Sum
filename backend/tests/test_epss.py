"""EPSS client: chunking, API parsing, daily CSV parsing."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.ingestion.epss import EpssClient, chunk_cve_ids, parse_epss_csv


def test_chunk_cve_ids_respects_limits() -> None:
    ids = [f"CVE-2021-{i:04d}" for i in range(250)]
    chunks = list(chunk_cve_ids(ids, size=100, max_chars=2000))
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert all(len(",".join(chunk)) <= 2000 for chunk in chunks)
    assert sum(len(chunk) for chunk in chunks) == 250
    assert len(chunks) == 3


def test_chunk_cve_ids_dedupes_and_keeps_order() -> None:
    chunks = list(chunk_cve_ids(["CVE-A", "CVE-B", "CVE-A"]))
    assert chunks == [["CVE-A", "CVE-B"]]


def test_get_scores_parses_response(make_http, epss_payload) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "cve" in request.url.params
        return httpx.Response(200, json=epss_payload)

    scores = EpssClient(client=make_http(handler)).get_scores(["CVE-2021-44228"])
    score = scores["CVE-2021-44228"]
    assert score.epss == pytest.approx(0.99999)
    assert score.percentile == pytest.approx(1.0)
    assert score.score_date == date(2026, 9, 9)


def test_parse_epss_csv_skips_comments_and_header() -> None:
    text = (
        "#model_version:v2025.03.14,score_date:2026-09-10T00:00:00Z\n"
        "cve,epss,percentile\n"
        "CVE-2021-44228,0.99999,1.0\n"
        "CVE-2019-0708,0.97000,0.99000\n"
        "malformed-row\n"
    )
    scores = parse_epss_csv(text)
    assert set(scores) == {"CVE-2021-44228", "CVE-2019-0708"}
    assert scores["CVE-2019-0708"].epss == pytest.approx(0.97)
    assert scores["CVE-2021-44228"].score_date == date(2026, 9, 10)
