"""NVD CVE API 2.0 client.

Rate limits: 5 requests / 30 s anonymous, 50 / 30 s with a free API key. The client
throttles to the applicable interval and retries transient failures.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from typing import Any

from app.ingestion.base import HttpClient
from app.ingestion.models import VulnerabilityRecord
from app.normalization.vulnerabilities import empty_record, nvd_item_to_record

NVD_CVE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_DEFAULT_PAGE_SIZE = 2000
NVD_ANON_MIN_INTERVAL = 30.0 / 5
NVD_KEY_MIN_INTERVAL = 30.0 / 50


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


class NvdClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: HttpClient | None = None,
        transport: Any = None,
        sleep: Any = time.sleep,
        page_size: int = NVD_DEFAULT_PAGE_SIZE,
    ) -> None:
        headers = {"apiKey": api_key} if api_key else {}
        interval = NVD_KEY_MIN_INTERVAL if api_key else NVD_ANON_MIN_INTERVAL
        self._client = client or HttpClient(
            headers=headers, min_interval=interval, transport=transport, sleep=sleep
        )
        if api_key:
            self._client.set_header("apiKey", api_key)
        self._page_size = min(page_size, NVD_DEFAULT_PAGE_SIZE)

    def get_cve(self, cve_id: str) -> VulnerabilityRecord | None:
        """Fetch one CVE. Returns ``None`` when NVD does not know it."""
        data = self._client.get_json(NVD_CVE_URL, params={"cveId": cve_id})
        entries = data.get("vulnerabilities") or []
        if not entries:
            return None
        return nvd_item_to_record(entries[0]["cve"])

    def get_cves(self, cve_ids: Iterable[str]) -> dict[str, VulnerabilityRecord]:
        """Fetch several CVEs (one NVD request each — the API takes a single id)."""
        records: dict[str, VulnerabilityRecord] = {}
        for cve_id in dict.fromkeys(cve_ids):
            record = self.get_cve(cve_id)
            records[cve_id] = record if record is not None else empty_record(cve_id)
        return records

    def iter_modified(self, start: datetime, end: datetime) -> Iterator[VulnerabilityRecord]:
        """Yield every CVE modified in ``[start, end]`` (max 120 days), paginating."""
        start_index = 0
        while True:
            data = self._client.get_json(
                NVD_CVE_URL,
                params={
                    "lastModStartDate": _iso(start),
                    "lastModEndDate": _iso(end),
                    "resultsPerPage": self._page_size,
                    "startIndex": start_index,
                },
            )
            entries = data.get("vulnerabilities") or []
            for entry in entries:
                yield nvd_item_to_record(entry["cve"])
            total = int(data.get("totalResults", 0))
            if not entries:
                break
            start_index += len(entries)
            if start_index >= total:
                break

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NvdClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def nvd_client_from_settings(api_key: str | None = None, **kwargs: Any) -> NvdClient:
    from app.config import get_settings

    return NvdClient(api_key=api_key or get_settings().nvd_api_key, **kwargs)
