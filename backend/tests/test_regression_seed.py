"""Reproducibility regression: a frozen scenario + seed reproduces identical outputs."""

from app.risk.demo import EXAMPLE
from app.risk.schemas import load_scenario, simulate

N_TRIALS = 50_000
SEED = 42


def test_frozen_scenario_reproduces_tail_metrics() -> None:
    scenario = load_scenario(EXAMPLE)
    first = simulate(scenario, n_trials=N_TRIALS, seed=SEED)
    second = simulate(scenario, n_trials=N_TRIALS, seed=SEED)

    assert first.to_dict()["summary"] == second.to_dict()["summary"]
    assert first.to_dict()["frequency"] == second.to_dict()["frequency"]
    assert first.to_dict()["loss_exceedance"] == second.to_dict()["loss_exceedance"]


def test_simulation_records_provenance_of_the_run() -> None:
    result = simulate(load_scenario(EXAMPLE), n_trials=2_000, seed=SEED)
    payload = result.to_dict()

    assert result.model_version
    assert "numpy" in result.library_versions
    assert payload["simulation"]["n_trials"] == 2_000
    assert payload["simulation"]["seed"] == SEED
    # every displayed figure is traceable to the evidence mix
    assert payload["evidence_mix"]["band"] in {"HIGH", "MEDIUM", "LOW"}
    assert payload["scenario_id"] == "SCN-RANSOM-01"
