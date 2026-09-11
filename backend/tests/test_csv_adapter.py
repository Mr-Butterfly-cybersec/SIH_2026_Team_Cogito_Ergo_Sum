"""CSV adapter and the ingest job entrypoint."""

from __future__ import annotations

from app.ingestion.csv_adapter import CsvAdapter
from app.jobs.ingest import DEFAULT_FINDINGS, _cve_ids, main


def test_example_findings_load() -> None:
    findings = CsvAdapter(findings_path=DEFAULT_FINDINGS).fetch_findings()
    assert len(findings) == 18
    assert findings[0].cve_id == "CVE-2021-44228"
    assert findings[0].asset_id == "AST-ADM-WEB-01"
    assert findings[0].source == "vulnerability_mgmt"
    assert all(f.cve_id and f.asset_id for f in findings)


def test_missing_file_returns_empty(tmp_path) -> None:
    assert CsvAdapter(findings_path=tmp_path / "nope.csv").fetch_findings() == []
    assert CsvAdapter().fetch_assets() == []


def test_assets_and_controls_parsing(tmp_path) -> None:
    assets_csv = tmp_path / "assets.csv"
    assets_csv.write_text(
        "asset_id,name,category,internet_exposed,rto_hours\n"
        "AST-1,Admissions portal,internet_facing,true,8\n"
        "AST-2,HR database,internal,no,24\n",
        encoding="utf-8",
    )
    controls_csv = tmp_path / "controls.csv"
    controls_csv.write_text(
        "control_id,name,category,coverage,applies_to_assets\n"
        "CTL-MFA,MFA for privileged identities,resistive,0.4,AST-1;AST-2\n",
        encoding="utf-8",
    )

    assets = CsvAdapter(assets_path=assets_csv).fetch_assets()
    assert [a.asset_id for a in assets] == ["AST-1", "AST-2"]
    assert assets[0].internet_exposed is True
    assert assets[0].rto_hours == 8.0

    controls = CsvAdapter(controls_path=controls_csv).fetch_controls()
    assert controls[0].control_id == "CTL-MFA"
    assert controls[0].coverage == 0.4
    assert controls[0].applies_to_assets == ["AST-1", "AST-2"]


def test_cve_ids_dedupes_and_limits() -> None:
    ids = _cve_ids(DEFAULT_FINDINGS, None)
    assert len(ids) == len(set(ids)) == 18
    assert _cve_ids(DEFAULT_FINDINGS, 3) == ids[:3]


def test_main_returns_one_when_no_cves(tmp_path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("finding_id,asset_id,cve_id\n", encoding="utf-8")
    assert main(["--findings", str(empty)]) == 1


def test_main_offline_succeeds() -> None:
    assert main(["--offline"]) == 0
