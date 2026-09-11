"""Quantitative risk core: distributions, FAIR models, Monte Carlo, provenance."""

from app.risk.aggregation import portfolio_losses, portfolio_summary, total_eal
from app.risk.distributions import BetaPert, Constant, Lognormal, Poisson
from app.risk.frequency import FrequencyModel, FrequencySample
from app.risk.magnitude import MagnitudeModel
from app.risk.metrics import (
    annualize,
    risk_reduction,
    risk_removed_per_unit,
    rosi,
)
from app.risk.monte_carlo import (
    CompiledScenario,
    LossSummary,
    ScenarioResult,
    SimulationConfig,
    run_simulation,
    summarize,
)
from app.risk.provenance import (
    MODEL_VERSION,
    ConfidenceBand,
    EvidenceMix,
    Provenance,
    SourceType,
)
from app.risk.schemas import ScenarioSpec, load_scenario, simulate

__all__ = [
    "MODEL_VERSION",
    "BetaPert",
    "CompiledScenario",
    "ConfidenceBand",
    "Constant",
    "EvidenceMix",
    "FrequencyModel",
    "FrequencySample",
    "Lognormal",
    "LossSummary",
    "MagnitudeModel",
    "Poisson",
    "Provenance",
    "ScenarioResult",
    "ScenarioSpec",
    "SimulationConfig",
    "SourceType",
    "annualize",
    "load_scenario",
    "portfolio_losses",
    "portfolio_summary",
    "risk_reduction",
    "risk_removed_per_unit",
    "rosi",
    "run_simulation",
    "simulate",
    "summarize",
    "total_eal",
]
