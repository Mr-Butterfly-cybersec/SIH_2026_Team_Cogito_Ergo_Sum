"""Compliance API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

TRIALS = 500


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_report_shape(client: TestClient) -> None:
    body = client.get("/api/v1/compliance", params={"n_trials": TRIALS}).json()
    assert body["organization"]
    assert body["catalog_version"]
    assert 0.0 <= body["overall_coverage"] <= 1.0
    assert len(body["frameworks"]) == 7
    assert body["top_gaps"]


def test_frameworks_registry(client: TestClient) -> None:
    frameworks = client.get("/api/v1/compliance/frameworks").json()
    assert {f["id"] for f in frameworks} == {
        "nist_csf",
        "cis_v8",
        "iso_27001",
        "iso_42001",
        "rbi_2023",
        "sebi_cscrf",
        "dpdp_2023",
    }
    assert all(f["version"] and f["publisher"] for f in frameworks)
    indian = [f for f in frameworks if f["kind"] == "regulation"]
    assert {f["id"] for f in indian} == {"rbi_2023", "sebi_cscrf", "dpdp_2023"}


def test_single_framework_coverage(client: TestClient) -> None:
    body = client.get("/api/v1/compliance/frameworks/nist_csf", params={"n_trials": TRIALS}).json()
    assert body["framework"]["short_name"] == "NIST CSF 2.0"
    assert body["requirements"]
    assert body["counts"]["requirements"] == len(body["requirements"])
    assert body["functions"]


def test_unknown_framework_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/compliance/frameworks/nope").status_code == 404


def test_requirement_coverage_carries_references_and_inputs(client: TestClient) -> None:
    body = client.get("/api/v1/compliance/frameworks/cis_v8", params={"n_trials": TRIALS}).json()
    row = next(r for r in body["requirements"] if r["controls"])
    assert row["references"], "a mapped requirement must cite framework clauses"
    assert row["status"] in {"COVERED", "PARTIAL", "GAP"}
    for control in row["controls"]:
        assert 0.0 <= control["effectiveness"] <= 1.0


def test_requirements_endpoint_exposes_the_ontology(client: TestClient) -> None:
    requirements = client.get("/api/v1/compliance/requirements").json()
    assert len(requirements) >= 20
    row = next(r for r in requirements if r["id"] == "REQ-IDENTITY-MFA")
    assert set(row["references"]) >= {"nist_csf", "cis_v8", "iso_27001", "rbi_2023"}
    assert row["function"] == "Protect"


def test_requirements_can_be_filtered_by_framework(client: TestClient) -> None:
    all_rows = client.get("/api/v1/compliance/requirements").json()
    cis_rows = client.get("/api/v1/compliance/requirements?framework_id=cis_v8").json()
    assert 0 < len(cis_rows) < len(all_rows)
    assert all("cis_v8" in r["references"] for r in cis_rows)


def test_requirements_unknown_framework_is_404(client: TestClient) -> None:
    resp = client.get("/api/v1/compliance/requirements?framework_id=nope")
    assert resp.status_code == 404


def test_gaps_are_ranked_and_priced(client: TestClient) -> None:
    gaps = client.get("/api/v1/compliance/gaps", params={"n_trials": TRIALS, "limit": 5}).json()
    assert gaps
    exposures = [g["exposure"] for g in gaps]
    assert exposures == sorted(exposures, reverse=True)
    assert all(g["status"] != "COVERED" for g in gaps)
    assert any(g["exposure"] > 0 for g in gaps)


def test_gaps_can_be_scoped_to_a_framework(client: TestClient) -> None:
    gaps = client.get(
        "/api/v1/compliance/gaps",
        params={"framework_id": "rbi_2023", "n_trials": TRIALS, "limit": 50},
    ).json()
    assert gaps
    assert all(g["status"] != "COVERED" for g in gaps)
    # References are framework-native, so an RBI-scoped gap cites RBI thematic areas.
    assert all(g["references"] for g in gaps)
    assert all(
        all("A." not in clause and "." not in clause for clause in g["references"]) for g in gaps
    )


def test_gaps_unknown_framework_is_404(client: TestClient) -> None:
    resp = client.get("/api/v1/compliance/gaps?framework_id=nope")
    assert resp.status_code == 404


def test_gaps_can_be_filtered_by_function(client: TestClient) -> None:
    gaps = client.get(
        "/api/v1/compliance/gaps",
        params={"function": "recover", "n_trials": TRIALS, "limit": 50},
    ).json()
    assert all(g["function"] == "Recover" for g in gaps)
