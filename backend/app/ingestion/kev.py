"""CISA Known Exploited Vulnerabilities (KEV) client.

Public domain (CC0). The catalog is a confirmed-exploitation subset — absence is not
evidence of safety.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

from app.ingestion.base import HttpClient
from app.ingestion.models import KevEntry
from app.normalization.vulnerabilities import parse_date

KEV_JSON_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def parse_kev_catalog(payload: dict[str, Any]) -> tuple[dict[str, KevEntry], date | None]:
    entries: dict[str, KevEntry] = {}
    for item in payload.get("vulnerabilities", []) or []:
        cve_id = item.get("cveID")
        if not cve_id:
            continue
        entries[cve_id] = KevEntry(
            cve_id=cve_id,
            vendor_project=item.get("vendorProject"),
            product=item.get("product"),
            vulnerability_name=item.get("vulnerabilityName"),
            date_added=parse_date(item.get("dateAdded")),
            due_date=parse_date(item.get("dueDate")),
            known_ransomware=str(item.get("knownRansomwareCampaignUse", "")).lower() == "known",
            required_action=item.get("requiredAction"),
            cwes=item.get("cwes") or [],
        )
    return entries, parse_date(payload.get("dateReleased"))


class KevClient:
    def __init__(
        self, *, client: HttpClient | None = None, transport: Any = None, sleep: Any = time.sleep
    ) -> None:
        self._client = client or HttpClient(transport=transport, sleep=sleep)

    def fetch_catalog(self) -> tuple[dict[str, KevEntry], date | None]:
        return parse_kev_catalog(self._client.get_json(KEV_JSON_URL))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> KevClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
