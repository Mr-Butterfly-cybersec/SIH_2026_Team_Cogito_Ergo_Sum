"""Ingestion job entrypoint.

uv run python -m app.jobs.ingest                 # enrich the example finding set
uv run python -m app.jobs.ingest --limit 5       # only the first 5 CVEs
uv run python -m app.jobs.ingest --offline       # summarise what is already stored
uv run python -m app.jobs.ingest --skip-attack   # skip the ~51 MB ATT&CK bundle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.ingestion.csv_adapter import CsvAdapter
from app.ingestion.service import EnrichmentReport, build_default_service, tally_records
from app.ingestion.store import (
    ATTACK_FILE,
    VulnerabilityStore,
    ensure_dirs,
    save_attack_catalog,
)

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "ingestion" / "examples"
DEFAULT_FINDINGS = EXAMPLES_DIR / "findings.csv"


def _cve_ids(findings_path: Path, limit: int | None) -> list[str]:
    findings = CsvAdapter(findings_path=findings_path).fetch_findings()
    ids = [f.cve_id for f in findings if f.cve_id]
    ordered = list(dict.fromkeys(ids))
    return ordered[:limit] if limit else ordered


def _print_report(report: EnrichmentReport, stored: int) -> None:
    print("Ingestion report")
    print("-" * 44)
    print(f"  requested CVEs          {report.requested:>6}")
    print(f"  found in NVD            {report.found_in_nvd:>6}")
    print(f"  with CVSS               {report.with_cvss:>6}")
    print(f"  with EPSS               {report.with_epss:>6}")
    print(f"  in CISA KEV             {report.with_kev:>6}")
    print(f"  fully enriched (C+E)    {report.enriched:>6}")
    print(f"  enrichment ratio        {report.enrichment_ratio * 100:>5.1f}%")
    print(f"  records stored          {stored:>6}")
    for error in report.errors:
        print(f"  ! {error}")


def _summarise_store(store: VulnerabilityStore) -> EnrichmentReport:
    records = store.load()
    report = EnrichmentReport(requested=len(records))
    tally_records(records.values(), report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ingest and enrich public vulnerability intelligence."
    )
    parser.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS)
    parser.add_argument("--limit", type=int, default=None, help="only process the first N CVEs")
    parser.add_argument("--offline", action="store_true", help="do not hit the network")
    parser.add_argument("--skip-attack", action="store_true", help="skip the ATT&CK bundle")
    args = parser.parse_args(argv)

    ensure_dirs()
    store = VulnerabilityStore()

    if args.offline:
        report = _summarise_store(store)
        _print_report(report, len(store.load()))
        return 0

    cve_ids = _cve_ids(args.findings, args.limit)
    if not cve_ids:
        print(f"No CVE ids found in {args.findings}")
        return 1

    service = build_default_service()
    try:
        records, report = service.enrich(cve_ids)
    finally:
        service.close()

    store.save(records.values())
    _print_report(report, len(records))

    if not args.skip_attack:
        from app.ingestion.mitre import MitreAttackClient

        client = MitreAttackClient()
        try:
            catalog = client.fetch_enterprise()
        finally:
            client.close()
        save_attack_catalog(catalog)
        print(
            f"  ATT&CK  version {catalog.version}  "
            f"{catalog.technique_count} techniques, {len(catalog.mitigations)} mitigations"
        )
        print(f"  saved to {ATTACK_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
