"""Portfolio evaluation harness.

Every candidate portfolio — optimizer or baseline — is scored the same way: apply the
selected controls to each scenario's compiled model, re-run the Monte Carlo engine, and
aggregate the loss distributions. Nothing is ever scored by summing nominal per-control
reductions, because controls overlap.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from app.optimization.candidates import (
    Candidate,
    candidate_id_for,
    candidates_by_id,
)
from app.optimization.context import PlanningContext
from app.risk.control_effect import ControlApplication, apply_control_effects
from app.risk.metrics import (
    risk_reduction,
    risk_reduction_pct,
    risk_removed_per_unit,
    rosi,
)
from app.risk.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_TRIALS,
    ScenarioResult,
    SimulationConfig,
    run_simulation,
    summarize,
)


@dataclass(frozen=True)
class ScenarioOutcome:
    scenario_id: str
    name: str
    eal: float
    p90: float
    p95: float

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "eal": round(self.eal, 2),
            "p90": round(self.p90, 2),
            "p95": round(self.p95, 2),
        }


@dataclass(frozen=True)
class PortfolioOutcome:
    label: str
    selection: tuple[str, ...]
    spend: float
    annualized_cost: float
    baseline_eal: float
    eal: float
    p90: float
    p95: float
    risk_reduction: float
    risk_reduction_pct: float | None
    rosi: float | None
    risk_removed_per_rupee: float | None
    scenarios: tuple[ScenarioOutcome, ...]
    currency: str = "INR"
    n_trials: int = DEFAULT_TRIALS
    seed: int = DEFAULT_SEED
    n_scenarios: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "selection": list(self.selection),
            "spend": round(self.spend, 2),
            "annualized_cost": round(self.annualized_cost, 2),
            "currency": self.currency,
            "baseline_eal": round(self.baseline_eal, 2),
            "eal": round(self.eal, 2),
            "p90": round(self.p90, 2),
            "p95": round(self.p95, 2),
            "risk_reduction": round(self.risk_reduction, 2),
            "risk_reduction_pct": (
                round(self.risk_reduction_pct, 6) if self.risk_reduction_pct is not None else None
            ),
            "rosi": round(self.rosi, 4) if self.rosi is not None else None,
            "risk_removed_per_rupee": (
                round(self.risk_removed_per_rupee, 4)
                if self.risk_removed_per_rupee is not None
                else None
            ),
            "n_scenarios": self.n_scenarios,
            "n_trials": self.n_trials,
            "seed": self.seed,
            "scenarios": [s.to_dict() for s in self.scenarios],
        }


class PortfolioEvaluator:
    """Scores any selection of candidates by re-simulating the affected scenarios."""

    def __init__(
        self,
        context: PlanningContext,
        candidates: list[Candidate],
        config: SimulationConfig | None = None,
    ) -> None:
        self.context = context
        self.candidates = candidates_by_id(candidates)
        self.config = config or SimulationConfig()
        self._raw_cache: dict[
            tuple[str, ...], tuple[float, float, float, tuple[ScenarioOutcome, ...]]
        ] = {}

    # --- public API -----------------------------------------------------------------
    def baseline(self) -> PortfolioOutcome:
        return self._outcome((), "current posture")

    def evaluate(self, selection: tuple[str, ...] | list[str], label: str = "") -> PortfolioOutcome:
        key = tuple(sorted(set(selection) - {""}))
        return self._outcome(key, label or "selection")

    def marginal_reductions(self) -> dict[str, float]:
        """Standalone reduction for each candidate (the additive surrogate)."""
        baseline_eal = self._raw(())[0]
        return {cid: baseline_eal - self._raw((cid,))[0] for cid in self.candidates}

    def selection_cost(self, selection: tuple[str, ...] | list[str]) -> float:
        return sum(candidate.cost for cid in selection if (candidate := self.candidates.get(cid)))

    # --- internals ------------------------------------------------------------------
    def _applications(
        self, scenario_id: str, selection: frozenset[str]
    ) -> list[ControlApplication]:
        applications = []
        for control in self.context.controls.values():
            if scenario_id not in control.protects:
                continue
            candidate = self.candidates.get(candidate_id_for(control.control_id))
            if candidate is not None and candidate.id in selection:
                effectiveness = candidate.target_effectiveness
            else:
                effectiveness = control.effectiveness
            if effectiveness > 0:
                applications.append(
                    ControlApplication(
                        control_id=control.control_id,
                        category=control.category,
                        effectiveness=effectiveness,
                    )
                )
        return applications

    def simulate_scenario(
        self, scenario_id: str, selection: tuple[str, ...] | list[str] = ()
    ) -> ScenarioResult:
        """Simulate one scenario with the given selection applied."""
        compiled = self.context.scenarios[scenario_id]
        selected = frozenset(selection)
        frequency, magnitude = apply_control_effects(
            frequency=compiled.frequency,
            magnitude=compiled.magnitude,
            applications=self._applications(scenario_id, selected),
        )
        hardened = replace(compiled, frequency=frequency, magnitude=magnitude)
        return run_simulation(hardened, self.config)

    def _raw(
        self, selection: tuple[str, ...]
    ) -> tuple[float, float, float, tuple[ScenarioOutcome, ...]]:
        if selection not in self._raw_cache:
            self._raw_cache[selection] = self._simulate(selection)
        return self._raw_cache[selection]

    def _simulate(
        self, selection: tuple[str, ...]
    ) -> tuple[float, float, float, tuple[ScenarioOutcome, ...]]:
        outcomes: list[ScenarioOutcome] = []
        total: np.ndarray | None = None

        for scenario_id, compiled in self.context.scenarios.items():
            result = self.simulate_scenario(scenario_id, selection)
            outcomes.append(
                ScenarioOutcome(
                    scenario_id=scenario_id,
                    name=compiled.name,
                    eal=result.summary.eal,
                    p90=result.summary.p90,
                    p95=result.summary.p95,
                )
            )
            total = result.losses if total is None else total + result.losses

        if total is None:
            return 0.0, 0.0, 0.0, ()
        summary = summarize(total, self.context.currency)
        return summary.eal, summary.p90, summary.p95, tuple(outcomes)

    def _outcome(self, key: tuple[str, ...], label: str) -> PortfolioOutcome:
        eal, p90, p95, scenarios = self._raw(key)
        baseline_eal = self._raw(())[0]
        spend = self.selection_cost(key)
        annualized = spend / 3.0 if spend else 0.0

        return PortfolioOutcome(
            label=label,
            selection=key,
            spend=spend,
            annualized_cost=annualized,
            baseline_eal=baseline_eal,
            eal=eal,
            p90=p90,
            p95=p95,
            risk_reduction=risk_reduction(baseline_eal, eal),
            risk_reduction_pct=risk_reduction_pct(baseline_eal, eal),
            rosi=rosi(baseline_eal, eal, annualized) if annualized else None,
            risk_removed_per_rupee=risk_removed_per_unit(baseline_eal, eal, spend),
            scenarios=scenarios,
            currency=self.context.currency,
            n_trials=self.config.n_trials,
            seed=self.config.seed,
            n_scenarios=len(scenarios),
        )
