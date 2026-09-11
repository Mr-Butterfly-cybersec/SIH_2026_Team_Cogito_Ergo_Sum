"""API v1 tests: catalog, simulation, optimization and what-if endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

TRIALS = 500
SCENARIO = "SCN-CRED-01"
MFA = "INV-CTL-MFA-PRIV"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# --- catalog ----------------------------------------------------------------------------
def test_overview_shape(client: TestClient) -> None:
    body = client.get("/api/v1/overview").json()
    assert body["organization"]["name"]
    assert body["counts"]["assets"] > 0
    assert body["posture"]["baseline_eal"] > 0
    assert body["evidence_mix"]["band"] in {"HIGH", "MEDIUM", "LOW"}
    assert sum(body["criticality_bands"].values()) == body["counts"]["assets"]


def test_list_assets_have_criticality(client: TestClient) -> None:
    assets = client.get("/api/v1/assets").json()
    assert len(assets) > 0
    assert {"score", "band", "dimensions"} <= set(assets[0]["criticality"])
    assert all(asset["criticality"]["band"] for asset in assets)


def test_asset_detail_includes_findings(client: TestClient) -> None:
    asset = next(a for a in client.get("/api/v1/assets").json() if a["finding_count"] > 0)
    detail = client.get(f"/api/v1/assets/{asset['asset_id']}").json()
    assert detail["asset"]["asset_id"] == asset["asset_id"]
    assert len(detail["findings"]) == asset["finding_count"]


def test_unknown_asset_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/assets/NOPE").status_code == 404


def test_findings_carry_public_intelligence(client: TestClient) -> None:
    findings = client.get("/api/v1/findings").json()
    enriched = [f for f in findings if f["cvss_base_score"] is not None]
    assert enriched, "expected at least one finding joined with NVD data"
    assert any(f["cve_id"] for f in enriched)


def test_controls_map_to_fair_factors(client: TestClient) -> None:
    controls = client.get("/api/v1/controls").json()
    assert controls
    factors = {c["factor"]["factor"] for c in controls}
    assert factors <= {
        "contact_frequency",
        "probability_of_action",
        "resistance_strength",
        "loss_magnitude",
    }
    assert all(0.0 <= c["effectiveness"] <= 1.0 for c in controls)


def test_scenarios_carry_baseline_exposure_ranked(client: TestClient) -> None:
    """The dashboard lists scenarios by rupee exposure, so the catalogue must carry it."""
    scenarios = client.get("/api/v1/scenarios").json()
    assert scenarios
    assert all(s["baseline_eal"] is not None for s in scenarios)
    eals = [s["baseline_eal"] for s in scenarios]
    assert eals == sorted(eals, reverse=True)
    assert all(s["baseline_p95"] >= s["baseline_eal"] for s in scenarios)


def test_scenario_spec_exposes_provenance(client: TestClient) -> None:
    spec = client.get(f"/api/v1/scenarios/{SCENARIO}").json()
    contact = spec["frequency"]["contact_frequency"]
    assert {"distribution", "provenance"} <= set(contact)
    assert contact["provenance"]["source_type"]


def test_unmodelled_scenario_spec_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/scenarios/NOPE").status_code == 404


def test_candidates_are_listed(client: TestClient) -> None:
    candidates = client.get("/api/v1/candidates").json()
    assert candidates
    assert all("annualized_cost" in c for c in candidates)


# --- simulation -------------------------------------------------------------------------
def test_simulate_returns_binned_distribution_only(client: TestClient) -> None:
    body = client.post(f"/api/v1/scenarios/{SCENARIO}/simulate", json={"n_trials": TRIALS}).json()
    assert "losses" not in body
    assert len(body["histogram"]["bins"]) == len(body["histogram"]["counts"]) + 1
    assert body["summary"]["eal"] > 0
    assert body["simulation"]["n_trials"] == TRIALS


def test_simulate_is_reproducible(client: TestClient) -> None:
    payload = {"n_trials": TRIALS, "seed": 7}
    first = client.post(f"/api/v1/scenarios/{SCENARIO}/simulate", json=payload).json()
    second = client.post(f"/api/v1/scenarios/{SCENARIO}/simulate", json=payload).json()
    assert first == second


def test_simulate_unknown_scenario_is_404(client: TestClient) -> None:
    resp = client.post("/api/v1/scenarios/NOPE/simulate", json={"n_trials": TRIALS})
    assert resp.status_code == 404


def test_simulate_unknown_candidate_is_422(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/scenarios/{SCENARIO}/simulate",
        json={"n_trials": TRIALS, "controls": ["NOPE"]},
    )
    assert resp.status_code == 422


def test_portfolio_simulate_reports_reduction(client: TestClient) -> None:
    body = client.post(
        "/api/v1/portfolio/simulate", json={"n_trials": TRIALS, "controls": [MFA]}
    ).json()
    assert body["selection"] == [MFA]
    assert body["baseline_eal"] >= body["eal"]
    assert body["risk_reduction"] >= 0.0


def test_risk_reduction_pct_is_a_percentage(client: TestClient) -> None:
    """The API reports percentages (0-100) so the UI never multiplies by 100 twice."""
    body = client.post(
        "/api/v1/portfolio/simulate", json={"n_trials": TRIALS, "controls": [MFA]}
    ).json()
    assert 0.0 <= body["risk_reduction_pct"] <= 100.0


# --- optimization -----------------------------------------------------------------------
def test_optimize_compares_strategies(client: TestClient) -> None:
    body = client.post("/api/v1/optimize", json={"budget": 2_500_000, "n_trials": TRIALS}).json()
    labels = {row["label"] for row in body["comparison"]}
    assert {"current posture", "optimizer", "cvss_first"} <= labels
    assert body["result"]["spend"] <= body["budget"]
    assert body["explanation"]


def test_optimize_rejects_non_positive_budget(client: TestClient) -> None:
    assert client.post("/api/v1/optimize", json={"budget": 0}).status_code == 422


# --- what-if ----------------------------------------------------------------------------
def test_what_if_controls_hardens_scenario(client: TestClient) -> None:
    body = client.post(
        f"/api/v1/what-if/scenarios/{SCENARIO}/controls",
        json={"controls": [MFA], "n_trials": TRIALS},
    ).json()
    assert body["summary"]["eal"] > 0


def test_what_if_delay_reports_avoidable_loss(client: TestClient) -> None:
    body = client.post(
        f"/api/v1/what-if/scenarios/{SCENARIO}/delay",
        json={"controls": [MFA], "days": 30, "n_trials": TRIALS},
    ).json()
    assert body["days"] == 30
    assert body["avoidable_loss"] >= 0.0
    assert "method" in body


def test_what_if_criticality_reports_delta(client: TestClient) -> None:
    body = client.post(
        "/api/v1/what-if/scenarios/SCN-WEBAPP-01/criticality",
        json={"overrides": {"availability": 5}, "n_trials": TRIALS},
    ).json()
    assert body["before"]["score"] != body["after"]["score"] or body["eal_delta"] != 0.0


def test_what_if_rejects_unknown_dimension(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/what-if/scenarios/{SCENARIO}/criticality",
        json={"overrides": {"nonsense": 3}, "n_trials": TRIALS},
    )
    assert resp.status_code == 422


def test_what_if_rejects_out_of_range_value(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/what-if/scenarios/{SCENARIO}/criticality",
        json={"overrides": {"availability": 99}, "n_trials": TRIALS},
    )
    assert resp.status_code == 422
