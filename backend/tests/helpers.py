"""Test helpers (offline). Kept out of conftest so tests can import them directly."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from app.ingestion.base import HttpClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_http(handler: Callable[[httpx.Request], httpx.Response], **kwargs: Any) -> HttpClient:
    """An HttpClient backed by a mock transport that never sleeps."""
    return HttpClient(
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
        min_interval=0.0,
        **kwargs,
    )


def nvd_item(cve_id: str, base_score: float = 9.8) -> dict[str, Any]:
    """Minimal NVD vulnerability element for pagination tests."""
    return {
        "cve": {
            "id": cve_id,
            "published": "2024-01-01T00:00:00.000",
            "lastModified": "2024-01-02T00:00:00.000",
            "vulnStatus": "Analyzed",
            "descriptions": [{"lang": "en", "value": f"Description for {cve_id}"}],
            "metrics": {
                "cvssMetricV31": [
                    {
                        "source": "nvd@nist.gov",
                        "type": "Primary",
                        "cvssData": {
                            "version": "3.1",
                            "baseScore": base_score,
                            "baseSeverity": "CRITICAL",
                        },
                    }
                ]
            },
        }
    }
