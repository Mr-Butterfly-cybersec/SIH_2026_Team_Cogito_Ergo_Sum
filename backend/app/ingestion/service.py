"""Enrichment service: join NVD + EPSS + CISA KEV onto a set of CVE ids.

Sources degrade gracefully — a failing source is recorded in the report and the rest of
the pipeline continues.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from app.ingestion.epss import EpssClient
from app.ingestion.kev import KevClient
from app.ingestion.models import VulnerabilityRecord
from app.ingestion.nvd import NvdClient
from app.normalization.vulnerabilities import apply_epss, apply_kev, empty_record


@dataclass
class EnrichmentReport:
    requested: int = 0
    found_in_nvd: int = 0
    with_cvss: int = 0
    with_epss: int = 0
    with_kev: int = 0
    enriched: int = 0  # has both CVSS and EPSS
    errors: list[str] = field(default_factory=list)

    @property
    def enrichment_ratio(self) -> float:
        if self.requested == 0:
            return 0.0
        return self.enriched / self.requested

    def to_dict(self) -> dict[str, object]:
        payload = {
            "requested": self.requested,
            "found_in_nvd": self.found_in_nvd,
            "with_cvss": self.with_cvss,
            "with_epss": self.with_epss,
            "with_kev": self.with_kev,
            "enriched": self.enriched,
            "enrichment_ratio": round(self.enrichment_ratio, 4),
            "errors": self.errors,
        }
        return payload


def tally_records(records: Iterable[VulnerabilityRecord], report: EnrichmentReport) -> None:
    """Count coverage of a record set into an existing report."""
    for record in records:
        if "NVD" in record.sources:
            report.found_in_nvd += 1
        if record.has_cvss:
            report.with_cvss += 1
        if record.has_epss:
            report.with_epss += 1
        if record.kev:
            report.with_kev += 1
        if record.enriched:
            report.enriched += 1


class EnrichmentService:
    def __init__(
        self,
        *,
        nvd: NvdClient | None = None,
        epss: EpssClient | None = None,
        kev: KevClient | None = None,
    ) -> None:
        self._nvd = nvd or NvdClient()
        self._epss = epss or EpssClient()
        self._kev = kev or KevClient()

    def enrich(
        self, cve_ids: Sequence[str], *, include_kev: bool = True
    ) -> tuple[dict[str, VulnerabilityRecord], EnrichmentReport]:
        ids = list(dict.fromkeys(cve_id for cve_id in cve_ids if cve_id))
        report = EnrichmentReport(requested=len(ids))

        try:
            records = self._nvd.get_cves(ids)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, report the cause
            report.errors.append(f"NVD: {exc}")
            records = {cve_id: empty_record(cve_id) for cve_id in ids}

        try:
            scores = self._epss.get_scores(ids)
            for cve_id, score in scores.items():
                record = records.get(cve_id)
                if record is not None:
                    apply_epss(
                        record,
                        epss=score.epss,
                        percentile=score.percentile,
                        score_date=score.score_date,
                        source="FIRST EPSS API",
                    )
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"EPSS: {exc}")

        if include_kev:
            try:
                catalog, _ = self._kev.fetch_catalog()
                for cve_id in ids:
                    entry = catalog.get(cve_id)
                    record = records.get(cve_id)
                    if entry is not None and record is not None:
                        apply_kev(record, entry)
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"KEV: {exc}")

        tally_records(records.values(), report)
        return records, report

    def close(self) -> None:
        self._nvd.close()
        self._epss.close()
        self._kev.close()


def build_default_service() -> EnrichmentService:
    from app.config import get_settings

    return EnrichmentService(nvd=NvdClient(api_key=get_settings().nvd_api_key))
