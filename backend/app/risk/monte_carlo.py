"""Monte Carlo simulation of a compiled risk scenario.

Produces a full annual-loss distribution: EAL, percentiles, VaR/CVaR, a loss-exceedance
curve and a histogram. Reproducible from ``(scenario, seed, n_trials)``.

Method: sample the frequency side to get Loss Event Frequency per trial, draw the number
of loss events as ``Poisson(LEF)``, then sum independently drawn per-event loss
magnitudes. This is the standard Poisson-thinning view of "each threat event becomes a
loss with probability = Vulnerability".
"""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version

import numpy as np

from app.risk.frequency import FrequencyModel
from app.risk.magnitude import MagnitudeModel
from app.risk.provenance import MODEL_VERSION, EvidenceMix, Provenance

DEFAULT_TRIALS = 10_000
DEFAULT_SEED = 42
DEFAULT_EXCEEDANCE_POINTS = 200
DEFAULT_HISTOGRAM_BINS = 60
_LIBRARIES = ("numpy", "scipy")


@dataclass(frozen=True)
class SimulationConfig:
    n_trials: int = DEFAULT_TRIALS
    seed: int = DEFAULT_SEED
    exceedance_points: int = DEFAULT_EXCEEDANCE_POINTS
    histogram_bins: int = DEFAULT_HISTOGRAM_BINS

    def __post_init__(self) -> None:
        if self.n_trials <= 0:
            raise ValueError("n_trials must be positive")


@dataclass(frozen=True)
class CompiledScenario:
    """A scenario compiled from declarative specs into sampler-ready models."""

    id: str
    name: str
    currency: str
    frequency: FrequencyModel
    magnitude: MagnitudeModel
    provenances: list[Provenance] = field(default_factory=list)
    asset_id: str | None = None
    business_service: str | None = None
    cve_ids: tuple[str, ...] = ()
    attack_techniques: tuple[str, ...] = ()


@dataclass(frozen=True)
class LossSummary:
    eal: float
    median: float
    p50: float
    p90: float
    p95: float
    p99: float
    var_95: float
    cvar_95: float
    minimum: float
    maximum: float
    currency: str = "INR"

    def to_dict(self) -> dict[str, float | str]:
        return {
            "currency": self.currency,
            "eal": round(self.eal, 2),
            "median": round(self.median, 2),
            "p50": round(self.p50, 2),
            "p90": round(self.p90, 2),
            "p95": round(self.p95, 2),
            "p99": round(self.p99, 2),
            "var_95": round(self.var_95, 2),
            "cvar_95": round(self.cvar_95, 2),
            "min": round(self.minimum, 2),
            "max": round(self.maximum, 2),
        }


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    scenario_name: str
    currency: str
    summary: LossSummary
    mean_tef: float
    vulnerability: float
    mean_lef: float
    n_trials: int
    seed: int
    model_version: str
    evidence_mix: EvidenceMix
    histogram: dict[str, list[float]]
    loss_exceedance: dict[str, list[float]]
    library_versions: dict[str, str]
    asset_id: str | None = None
    business_service: str | None = None
    losses: np.ndarray = field(default_factory=lambda: np.zeros(0), repr=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "asset_id": self.asset_id,
            "business_service": self.business_service,
            "summary": self.summary.to_dict(),
            "frequency": {
                "mean_tef": round(self.mean_tef, 4),
                "vulnerability": round(self.vulnerability, 6),
                "mean_lef": round(self.mean_lef, 6),
            },
            "simulation": {
                "n_trials": self.n_trials,
                "seed": self.seed,
                "model_version": self.model_version,
                "library_versions": self.library_versions,
            },
            "evidence_mix": self.evidence_mix.to_dict(),
            "histogram": self.histogram,
            "loss_exceedance": self.loss_exceedance,
        }


def summarize(losses: np.ndarray, currency: str = "INR") -> LossSummary:
    """Summarise an annual-loss sample."""
    if losses.size == 0:
        raise ValueError("cannot summarise an empty sample")
    p50, p90, p95, p99 = (float(v) for v in np.percentile(losses, [50, 90, 95, 99]))
    tail = losses[losses >= p95]
    # CVaR is the mean of losses at or above VaR, so CVaR >= VaR must hold by definition.
    # When many tail values are identical the floating-point mean can land a rounding step
    # *below* p95, which would report an incoherent (CVaR < VaR) pair. The invariant is
    # mathematical, so it is enforced rather than merely tested for.
    cvar_95 = max(float(tail.mean()) if tail.size else p95, p95)
    return LossSummary(
        eal=float(losses.mean()),
        median=p50,
        p50=p50,
        p90=p90,
        p95=p95,
        p99=p99,
        var_95=p95,
        cvar_95=cvar_95,
        minimum=float(losses.min()),
        maximum=float(losses.max()),
        currency=currency,
    )


def loss_exceedance(
    losses: np.ndarray, points: int = DEFAULT_EXCEEDANCE_POINTS
) -> dict[str, list[float]]:
    """``P(Loss > x)`` — the loss-exceedance curve, downsampled for the UI."""
    ordered = np.sort(losses)
    n = ordered.size
    exceedance = 1.0 - np.arange(1, n + 1) / n
    if n > points > 0:
        idx = np.unique(np.linspace(0, n - 1, points).astype(int))
        ordered, exceedance = ordered[idx], exceedance[idx]
    return {"loss": [float(v) for v in ordered], "probability": [float(v) for v in exceedance]}


def histogram(losses: np.ndarray, bins: int = DEFAULT_HISTOGRAM_BINS) -> dict[str, list[float]]:
    counts, edges = np.histogram(losses, bins=bins)
    return {"bins": [float(v) for v in edges], "counts": [int(v) for v in counts]}


def library_versions() -> dict[str, str]:
    out = {"python": platform.python_version()}
    for name in _LIBRARIES:
        try:
            out[name] = version(name)
        except PackageNotFoundError:  # pragma: no cover - dependency always present
            continue
    return out


def run_simulation(
    scenario: CompiledScenario, config: SimulationConfig | None = None
) -> ScenarioResult:
    """Run the Monte Carlo simulation for a compiled scenario."""
    config = config or SimulationConfig()
    rng = np.random.default_rng(config.seed)

    frequency = scenario.frequency.sample(rng, config.n_trials)
    events = rng.poisson(frequency.lef)
    total_events = int(events.sum())

    per_event = scenario.magnitude.sample_event_losses(rng, total_events)
    if total_events == 0:
        losses = np.zeros(config.n_trials)
    else:
        trial_index = np.repeat(np.arange(config.n_trials), events)
        losses = np.bincount(trial_index, weights=per_event, minlength=config.n_trials)

    return ScenarioResult(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        asset_id=scenario.asset_id,
        business_service=scenario.business_service,
        currency=scenario.currency,
        summary=summarize(losses, scenario.currency),
        mean_tef=float(frequency.tef.mean()),
        vulnerability=frequency.vulnerability,
        mean_lef=float(frequency.lef.mean()),
        n_trials=config.n_trials,
        seed=config.seed,
        model_version=MODEL_VERSION,
        evidence_mix=EvidenceMix.from_provenances(scenario.provenances),
        histogram=histogram(losses, config.histogram_bins),
        loss_exceedance=loss_exceedance(losses, config.exceedance_points),
        library_versions=library_versions(),
        losses=losses,
    )
