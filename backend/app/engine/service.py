"""Scenario engine: decision-level analysis over the planning context.

This is the service layer the API talks to. It composes the risk core (scenarios,
Monte Carlo) with the optimizer (candidates, CP-SAT, harness) and adds what-if analysis:

* **control rollout** — apply a set of investment candidates and measure the shift;
* **remediation delay** — the loss exposed by leaving the current posture in place for a
  window instead of hardening now;
* **criticality change** — an asset becomes more important, so its scenarios are
  re-materialized at the new criticality and re-simulated.

Everything is computed from committed inputs, so the engine runs offline and every number
is reproducible from ``(selection, n_trials, seed)``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.compliance.coverage import ComplianceReport, build_report
from app.optimization.baseline import (
    cheapest_first,
    cvss_first,
    density_greedy,
    epss_first,
)
from app.optimization.candidates import Candidate, candidates_from_context
from app.optimization.context import PlanningContext, load_planning_context
from app.optimization.harness import PortfolioEvaluator, PortfolioOutcome, ScenarioOutcome
from app.optimization.refine import refine_selection
from app.optimization.solver import OptimizationResult, solve_portfolio
from app.risk.asset_criticality import profile_from_asset
from app.risk.metrics import risk_reduction, risk_reduction_pct
from app.risk.monte_carlo import (
    DEFAULT_SEED,
    DEFAULT_TRIALS,
    ScenarioResult,
    SimulationConfig,
    run_simulation,
)
from app.risk.scenario_factory import AssetContext, materialize_scenario
from app.seed.org_demo import load_snapshot
from app.seed.schema import SeedSnapshot

DAYS_PER_YEAR = 365.0

BASELINE_LABEL = "current posture"


@dataclass(frozen=True)
class DelayImpact:
    """The loss exposed by postponing remediation for a window."""

    scenario_id: str
    days: int
    window_years: float
    selection: tuple[str, ...]
    loss_if_delayed: float
    loss_if_remediated_now: float
    avoidable_loss: float
    baseline_eal: float
    hardened_eal: float
    currency: str

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "days": self.days,
            "window_years": round(self.window_years, 6),
            "selection": list(self.selection),
            "loss_if_delayed": round(self.loss_if_delayed, 2),
            "loss_if_remediated_now": round(self.loss_if_remediated_now, 2),
            "avoidable_loss": round(self.avoidable_loss, 2),
            "baseline_eal": round(self.baseline_eal, 2),
            "hardened_eal": round(self.hardened_eal, 2),
            "currency": self.currency,
            "method": (
                "Annual loss rate of each posture accrued over the delay window "
                "(days/365); the difference is the modelled avoidable loss."
            ),
        }


@dataclass(frozen=True)
class CriticalityImpact:
    """The effect of an asset becoming more (or less) business-critical."""

    scenario_id: str
    asset_id: str
    before: dict[str, object]
    after: dict[str, object]
    eal_before: float
    eal_after: float
    eal_delta: float
    p95_before: float
    p95_after: float
    currency: str

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "asset_id": self.asset_id,
            "before": self.before,
            "after": self.after,
            "eal_before": round(self.eal_before, 2),
            "eal_after": round(self.eal_after, 2),
            "eal_delta": round(self.eal_delta, 2),
            "p95_before": round(self.p95_before, 2),
            "p95_after": round(self.p95_after, 2),
            "currency": self.currency,
        }


class ScenarioEngine:
    """Decision-level analysis service over one planning context."""

    def __init__(self, context: PlanningContext) -> None:
        self.context = context
        self.candidates = candidates_from_context(context)
        self._snapshot = load_snapshot()
        self._evaluators: dict[tuple[int, int], PortfolioEvaluator] = {}
        self._compliance_cache: dict[tuple[int, int], ComplianceReport] = {}

    # --- evaluation -----------------------------------------------------------------
    @property
    def snapshot(self) -> SeedSnapshot:
        """The committed demo organization snapshot backing the context."""
        return self._snapshot

    def evaluator(
        self, n_trials: int = DEFAULT_TRIALS, seed: int = DEFAULT_SEED
    ) -> PortfolioEvaluator:
        """A cached evaluator per (trials, seed) so repeated requests reuse simulations."""
        key = (n_trials, seed)
        if key not in self._evaluators:
            self._evaluators[key] = PortfolioEvaluator(
                self.context,
                self.candidates,
                SimulationConfig(n_trials=n_trials, seed=seed),
            )
        return self._evaluators[key]

    def baseline(
        self, n_trials: int = DEFAULT_TRIALS, seed: int = DEFAULT_SEED
    ) -> PortfolioOutcome:
        return self.evaluator(n_trials, seed).baseline()

    def baseline_scenario_exposure(
        self, n_trials: int = DEFAULT_TRIALS, seed: int = DEFAULT_SEED
    ) -> dict[str, ScenarioOutcome]:
        """Per-scenario baseline exposure, taken from one cached portfolio simulation."""
        return {outcome.scenario_id: outcome for outcome in self.baseline(n_trials, seed).scenarios}

    def outcome(
        self,
        selection: tuple[str, ...] | list[str],
        *,
        label: str = "selection",
        n_trials: int = DEFAULT_TRIALS,
        seed: int = DEFAULT_SEED,
    ) -> PortfolioOutcome:
        return self.evaluator(n_trials, seed).evaluate(selection, label=label)

    def candidate(self, candidate_id: str) -> Candidate | None:
        for candidate in self.candidates:
            if candidate.id == candidate_id:
                return candidate
        return None

    # --- optimization ---------------------------------------------------------------
    def optimize(
        self,
        budget: float,
        *,
        n_trials: int = DEFAULT_TRIALS,
        seed: int = DEFAULT_SEED,
    ) -> tuple[OptimizationResult, list[PortfolioOutcome]]:
        """Solve the portfolio problem, then score it and the baselines by re-simulation."""
        evaluator = self.evaluator(n_trials, seed)
        marginals = evaluator.marginal_reductions()
        result = solve_portfolio(self.candidates, budget=budget, marginal_reductions=marginals)

        # CP-SAT optimizes a surrogate and can under-select; polish the proposal against
        # the true re-simulated objective before anything is claimed about it.
        refined = refine_selection(
            result.selection,
            self.candidates,
            budget=budget,
            evaluate_eal=lambda selection: evaluator.evaluate(selection).eal,
        )
        result = replace(result, selection=refined, spend=evaluator.selection_cost(refined))

        strategies: dict[str, tuple[str, ...]] = {
            "optimizer": result.selection,
            "cvss_first": cvss_first(self.candidates, self.context, budget),
            "epss_first": epss_first(self.candidates, self.context, budget),
            "density_greedy": density_greedy(self.candidates, budget, marginals),
            "cheapest_first": cheapest_first(self.candidates, budget),
        }
        outcomes = [evaluator.baseline()]
        outcomes.extend(
            evaluator.evaluate(selection, label=name) for name, selection in strategies.items()
        )
        return result, outcomes

    # --- simulation -----------------------------------------------------------------
    def simulate_scenario(
        self,
        scenario_id: str,
        selection: tuple[str, ...] | list[str] = (),
        *,
        n_trials: int = DEFAULT_TRIALS,
        seed: int = DEFAULT_SEED,
    ) -> ScenarioResult:
        if scenario_id not in self.context.scenarios:
            raise KeyError(scenario_id)
        return self.evaluator(n_trials, seed).simulate_scenario(scenario_id, selection)

    # --- what-if: remediation delay -------------------------------------------------
    def delay_impact(
        self,
        scenario_id: str,
        selection: tuple[str, ...] | list[str],
        days: int,
        *,
        n_trials: int = DEFAULT_TRIALS,
        seed: int = DEFAULT_SEED,
    ) -> DelayImpact:
        if days < 0:
            raise ValueError("days must be non-negative")
        evaluator = self.evaluator(n_trials, seed)
        baseline_eal = evaluator.evaluate((), BASELINE_LABEL).eal
        hardened_eal = evaluator.evaluate(selection, "hardened").eal

        window_years = days / DAYS_PER_YEAR
        loss_if_delayed = baseline_eal * window_years
        loss_if_remediated_now = hardened_eal * window_years

        return DelayImpact(
            scenario_id=scenario_id,
            days=days,
            window_years=window_years,
            selection=tuple(sorted(set(selection))),
            loss_if_delayed=loss_if_delayed,
            loss_if_remediated_now=loss_if_remediated_now,
            avoidable_loss=loss_if_delayed - loss_if_remediated_now,
            baseline_eal=baseline_eal,
            hardened_eal=hardened_eal,
            currency=self.context.currency,
        )

    # --- what-if: criticality change ------------------------------------------------
    def criticality_impact(
        self,
        scenario_id: str,
        overrides: dict[str, int],
        *,
        n_trials: int = DEFAULT_TRIALS,
        seed: int = DEFAULT_SEED,
    ) -> CriticalityImpact:
        entry = self.context.catalogue.get(scenario_id)
        if entry is None or entry.asset_id is None:
            raise KeyError(scenario_id)

        seed_asset = next(
            (asset for asset in self._snapshot.assets if asset.asset_id == entry.asset_id), None
        )
        if seed_asset is None:
            raise KeyError(entry.asset_id)

        current = profile_from_asset(seed_asset.criticality)
        merged = {**seed_asset.criticality, **overrides}
        updated = profile_from_asset(merged)

        spec = materialize_scenario(
            scenario_id=entry.id,
            name=entry.name,
            description=entry.description,
            asset=self._asset_context(entry.asset_id, merged),
            findings=self.context.findings_by_asset.get(entry.asset_id, []),
            currency=self.context.currency,
            attack_techniques=entry.attack_techniques,
            cve_ids=entry.cve_ids,
        )
        config = SimulationConfig(n_trials=n_trials, seed=seed)
        after = run_simulation(spec.compile(), config)
        before = self.simulate_scenario(scenario_id, (), n_trials=n_trials, seed=seed)

        return CriticalityImpact(
            scenario_id=scenario_id,
            asset_id=entry.asset_id,
            before=current.to_dict(),
            after=updated.to_dict(),
            eal_before=before.summary.eal,
            eal_after=after.summary.eal,
            eal_delta=after.summary.eal - before.summary.eal,
            p95_before=before.summary.p95,
            p95_after=after.summary.p95,
            currency=self.context.currency,
        )

    # --- helpers --------------------------------------------------------------------
    def _asset_context(self, asset_id: str, criticality: dict[str, int]) -> AssetContext:
        base = self.context.assets[asset_id]
        profile = profile_from_asset(criticality)
        return replace(
            base,
            criticality_score=profile.score,
            criticality_band=profile.band.value,
        )

    def risk_reduction_for(self, selection: tuple[str, ...] | list[str]) -> dict[str, float]:
        """Absolute and relative reduction of a selection against the current posture."""
        evaluator = self.evaluator()
        baseline_eal = evaluator.baseline().eal
        outcome = evaluator.evaluate(selection)
        return {
            "baseline_eal": baseline_eal,
            "selection_eal": outcome.eal,
            "risk_reduction": risk_reduction(baseline_eal, outcome.eal),
            "risk_reduction_pct": risk_reduction_pct(baseline_eal, outcome.eal) or 0.0,
        }

    # --- compliance -----------------------------------------------------------------
    def compliance_report(
        self, n_trials: int = DEFAULT_TRIALS, seed: int = DEFAULT_SEED
    ) -> ComplianceReport:
        """Framework coverage computed from real controls, with gaps priced in rupees.

        Exposure comes from the cached baseline simulation, so a gap's rupee figure is the
        same number the rest of the platform uses.
        """
        key = (n_trials, seed)
        if key not in self._compliance_cache:
            exposure = {
                outcome.scenario_id: outcome.eal
                for outcome in self.baseline(n_trials, seed).scenarios
            }
            self._compliance_cache[key] = build_report(self.context, exposure)
        return self._compliance_cache[key]


_ENGINE: ScenarioEngine | None = None


def get_engine() -> ScenarioEngine:
    """Process-wide engine singleton.

    The context is built from committed inputs, so caching it is safe and keeps the
    evaluators' simulation memo warm across requests.
    """
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ScenarioEngine(load_planning_context())
    return _ENGINE


def reset_engine() -> None:
    """Drop the cached engine (used by tests)."""
    global _ENGINE
    _ENGINE = None


__all__ = [
    "BASELINE_LABEL",
    "CriticalityImpact",
    "DelayImpact",
    "ScenarioEngine",
    "get_engine",
    "reset_engine",
]
