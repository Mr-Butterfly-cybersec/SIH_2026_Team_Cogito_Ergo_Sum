"""CISA KEV catalog parsing."""

from __future__ import annotations

from datetime import date

import httpx

from app.ingestion.kev import KevClient, parse_kev_catalog


def test_parse_kev_catalog(kev_payload) -> None:
    entries, released = parse_kev_catalog(kev_payload)
    assert released == date(2026, 9, 9)
    assert set(entries) == {"CVE-2021-44228", "CVE-2019-0708"}

    log4shell = entries["CVE-2021-44228"]
    assert log4shell.known_ransomware is True
    assert log4shell.date_added == date(2021, 12, 10)
    assert log4shell.due_date == date(2021, 12, 24)
    assert log4shell.cwes == ["CWE-502", "CWE-400"]

    bluekeep = entries["CVE-2019-0708"]
    assert bluekeep.known_ransomware is False


def test_fetch_catalog(make_http, kev_payload) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "known_exploited_vulnerabilities" in str(request.url)
        return httpx.Response(200, json=kev_payload)

    entries, _ = KevClient(client=make_http(handler)).fetch_catalog()
    assert "CVE-2021-44228" in entries
