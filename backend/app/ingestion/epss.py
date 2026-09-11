"""FIRST EPSS client.

The lookup API is for individual CVEs only — bulk work uses the daily gzip CSV.
"""

from __future__ import annotations

import gzip
import re
import time
from collections.abc import Iterable, Iterator, Sequence
from typing import Any

from app.ingestion.base import HttpClient
from app.ingestion.models import EpssScore
from app.normalization.vulnerabilities import parse_date

EPSS_API_URL = "https://api.first.org/data/v1/epss"
EPSS_CSV_URL = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"
EPSS_CHUNK_SIZE = 100
EPSS_MAX_QUERY_CHARS = 2000

_SCORE_DATE_RE = re.compile(r"score_date:([0-9T:\-Z]+)")


def chunk_cve_ids(
    cve_ids: Iterable[str], size: int = EPSS_CHUNK_SIZE, max_chars: int = EPSS_MAX_QUERY_CHARS
) -> Iterator[list[str]]:
    """Split ids so each query stays within EPSS's 2,000-character limit."""
    batch: list[str] = []
    length = 0
    for cve_id in dict.fromkeys(cve_ids):
        extra = len(cve_id) + (1 if batch else 0)
        if batch and (len(batch) >= size or length + extra > max_chars):
            yield batch
            batch, length = [], 0
            extra = len(cve_id)
        batch.append(cve_id)
        length += extra
    if batch:
        yield batch


def parse_epss_csv(text: str) -> dict[str, EpssScore]:
    """Parse the daily EPSS CSV (``cve,epss,percentile`` with ``#`` comments)."""
    score_date = None
    match = _SCORE_DATE_RE.search(text)
    if match:
        score_date = parse_date(match.group(1))

    scores: dict[str, EpssScore] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3 or parts[0].lower() == "cve":
            continue
        try:
            scores[parts[0]] = EpssScore(
                cve_id=parts[0],
                epss=float(parts[1]),
                percentile=float(parts[2]),
                score_date=score_date,
            )
        except ValueError:
            continue
    return scores


class EpssClient:
    def __init__(
        self, *, client: HttpClient | None = None, transport: Any = None, sleep: Any = time.sleep
    ) -> None:
        self._client = client or HttpClient(transport=transport, sleep=sleep)

    def get_scores(self, cve_ids: Sequence[str]) -> dict[str, EpssScore]:
        """Look up scores for specific CVEs (chunked to respect the query limit)."""
        scores: dict[str, EpssScore] = {}
        for chunk in chunk_cve_ids(cve_ids):
            data = self._client.get_json(EPSS_API_URL, params={"cve": ",".join(chunk)})
            for row in data.get("data", []) or []:
                scores[row["cve"]] = EpssScore(
                    cve_id=row["cve"],
                    epss=float(row["epss"]),
                    percentile=float(row["percentile"]),
                    score_date=parse_date(row.get("date")),
                )
        return scores

    def fetch_current(self) -> dict[str, EpssScore]:
        """Download and parse the full daily CSV (decompressed)."""
        payload = gzip.decompress(self._client.get_bytes(EPSS_CSV_URL))
        return parse_epss_csv(payload.decode("utf-8", "replace"))

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> EpssClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
