"""Telemetry adapter interface plus a small HTTP client with retry and throttling.

Every source (NVD, EPSS, KEV, ATT&CK, CSV, synthetic, Wazuh) implements
:class:`TelemetryAdapter` and emits the normalized records from ``models.py``.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx

from app.ingestion.models import (
    AssetRecord,
    ControlRecord,
    EventRecord,
    FindingRecord,
)

DEFAULT_USER_AGENT = "SIH26105-CRQ-Platform/0.1 (+https://sih.gov.in/sih2026PS)"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class TelemetryAdapter:
    """Common interface for every telemetry source.

    Subclasses override only the fetch methods they actually support, so this is a plain
    base class rather than an ABC (there are no methods every source must implement).
    """

    name: str = "adapter"

    def fetch_assets(self) -> list[AssetRecord]:
        return []

    def fetch_findings(self) -> list[FindingRecord]:
        return []

    def fetch_controls(self) -> list[ControlRecord]:
        return []

    def fetch_events(self) -> list[EventRecord]:
        return []


class HttpClient:
    """Thin ``httpx`` wrapper: throttles requests, retries transient failures.

    ``sleep`` is injectable so tests run without real delays.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        headers: dict[str, str] | None = None,
        min_interval: float = 0.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        user_agent: str = DEFAULT_USER_AGENT,
        backoff_base: float = 1.0,
    ) -> None:
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._sleep = sleep
        self._backoff_base = backoff_base
        self._last_request = 0.0
        self._client = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": user_agent, "Accept": "application/json", **(headers or {})},
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )

    def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request
        remaining = self._min_interval - elapsed
        if remaining > 0:
            self._sleep(remaining)
        self._last_request = time.monotonic()

    def _backoff(self, attempt: int, response: httpx.Response | None = None) -> None:
        delay = self._backoff_base * (2**attempt)
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                with contextlib.suppress(ValueError):
                    delay = max(delay, float(retry_after))
        self._sleep(delay)

    def set_header(self, name: str, value: str) -> None:
        """Set a default header on the underlying client (e.g. an API key)."""
        self._client.headers[name] = value

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                response = self._client.get(url, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    self._backoff(attempt)
                    continue
                raise
            if response.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                self._backoff(attempt, response)
                continue
            response.raise_for_status()
            return response
        raise RuntimeError("unreachable") from last_error

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        return self.get(url, params=params).json()

    def post_json(self, url: str, payload: Any, headers: dict[str, str] | None = None) -> Any:
        """POST a JSON body and decode the JSON response, with the same retry policy."""
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                response = self._client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    self._backoff(attempt)
                    continue
                raise
            if response.status_code in RETRYABLE_STATUS and attempt < self._max_retries:
                self._backoff(attempt, response)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("unreachable") from last_error

    def get_bytes(self, url: str, params: dict[str, Any] | None = None) -> bytes:
        return self.get(url, params=params).content

    def stream_lines(self, url: str) -> Iterator[str]:
        self._throttle()
        with self._client.stream("GET", url) as response:
            response.raise_for_status()
            yield from response.iter_lines()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
