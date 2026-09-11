"""Reproducible benchmark: does the optimizer actually beat the naive strategies?

This is the evidence artifact for the project's central claim. It runs a fixed grid of
budgets and seeds through the *same* evaluation harness and records how each strategy
performs, so the comparison is auditable rather than asserted.

Three things make the comparison honest:

1. **Every strategy is scored by re-simulating the Monte Carlo engine** with its selection
   applied. Nothing is summed additively, because controls overlap (submodular risk
   reduction) and additive scoring overstates the benefit.
2. **The same seed and trial count are used for every strategy within a run**, so the
   differences are attributable to the portfolio, not to simulation noise.
3. **Where the candidate set is small enough, brute force computes the true optimum** under
   the re-simulated objective. That gives a bound: we can report how far the CP-SAT portfolio
   is from the best possible answer, not just that it beats the baselines.

Run it with ``make benchmark``; the result is written to ``docs/benchmark.md``.
"""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.engine.service import ScenarioEngine
from app.optimization.baseline import (
    brute_force,
    cheapest_first,
    cvss_first,
    density_greedy,
    epss_first,
    random_selection,
)
from app.optimization.portfolio import best_outcome

DEFAULT_BUDGETS: tuple[float, ...] = (
    500_000.0,
    1_000_000.0,
    2_500_000.0,
    5_000_000.0,
    10_000_000.0,
)
DEFAULT_SEEDS: tuple[int, ...] = (42, 7, 2026)
DEFAULT_TRIALS = 20_000

#: The optimizer may tie the exact optimum but must never exceed it. Only floating-point
#: noise in the re-simulation is an acceptable positive difference.
SOUNDNESS_TOLERANCE = 0.01

STRATEGY_LABELS: dict[str, str] = {
    "optimizer": "Optimizer (CP-SAT)",
    "cvss_first": "Highest-CVSS first",
    "epss_first": "Highest-EPSS first",
    "density_greedy": "Risk-reduction per ₹",
    "cheapest_first": "Cheapest first",
    "random": "Random",
    "brute_force": "Exact optimum (brute force)",
}


@dataclass
class StrategyRow:
    strategy: str
    label: str
    controls: int
    spend: float
    eal: float
    risk_reduction: float
    risk_reduction_pct: float | None
    risk_removed_per_rupee: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BudgetResult:
    budget: float
    seed: int
    n_trials: int
    baseline_eal: float
    rows: list[StrategyRow]
    best_label: str
    optimizer_vs_cvss_points: float | None
    optimizer_gap_to_optimum_points: float | None
    exact_optimum: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget": self.budget,
            "seed": self.seed,
            "n_trials": self.n_trials,
            "baseline_eal": round(self.baseline_eal, 2),
            "best_label": self.best_label,
            "optimizer_vs_cvss_points": self.optimizer_vs_cvss_points,
            "optimizer_gap_to_optimum_points": self.optimizer_gap_to_optimum_points,
            "exact_optimum": self.exact_optimum,
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass
class BenchmarkReport:
    generated_at: str
    organization: str
    currency: str
    candidates: int
    scenarios: int
    trials: int
    seeds: list[int]
    budgets: list[float]
    python: str
    library_versions: dict[str, str]
    results: list[BudgetResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "organization": self.organization,
            "currency": self.currency,
            "candidates": self.candidates,
            "scenarios": self.scenarios,
            "trials": self.trials,
            "seeds": self.seeds,
            "budgets": self.budgets,
            "python": self.python,
            "library_versions": self.library_versions,
            "results": [result.to_dict() for result in self.results],
        }


def _row(label: str, outcome, strategy: str) -> StrategyRow:
    return StrategyRow(
        strategy=strategy,
        label=label,
        controls=len(outcome.selection),
        spend=round(outcome.spend, 2),
        eal=round(outcome.eal, 2),
        risk_reduction=round(outcome.risk_reduction, 2),
        risk_reduction_pct=(
            round(outcome.risk_reduction_pct * 100, 4)
            if outcome.risk_reduction_pct is not None
            else None
        ),
        risk_removed_per_rupee=(
            round(outcome.risk_removed_per_rupee, 4)
            if outcome.risk_removed_per_rupee is not None
            else None
        ),
    )


def run_once(
    engine: ScenarioEngine,
    budget: float,
    *,
    n_trials: int = DEFAULT_TRIALS,
    seed: int = 42,
    include_random: bool = True,
    exact: bool = False,
) -> BudgetResult:
    """Evaluate every strategy for one (budget, seed) on the same harness."""
    evaluator = engine.evaluator(n_trials, seed)
    candidates = engine.candidates
    baseline_eal = evaluator.baseline().eal
    marginals = evaluator.marginal_reductions()

    optimization = engine.optimize(budget, n_trials=n_trials, seed=seed)[0]

    selections: dict[str, tuple[str, ...]] = {
        "optimizer": optimization.selection,
        "cvss_first": cvss_first(candidates, engine.context, budget),
        "epss_first": epss_first(candidates, engine.context, budget),
        "density_greedy": density_greedy(candidates, budget, marginals),
        "cheapest_first": cheapest_first(candidates, budget),
    }
    if include_random:
        selections["random"] = random_selection(candidates, budget, seed=seed)

    rows = [
        _row(STRATEGY_LABELS[name], evaluator.evaluate(selection, label=name), name)
        for name, selection in selections.items()
    ]

    optimum_points: float | None = None
    optimum_absolute: float | None = None
    has_optimum = False
    if exact:
        optimum = brute_force(candidates, budget, evaluator)
        if optimum is not None:
            has_optimum = True
            optimum_row = _row(
                STRATEGY_LABELS["brute_force"],
                evaluator.evaluate(optimum, label="brute_force"),
                "brute_force",
            )
            rows.append(optimum_row)
            optimizer_row = next(r for r in rows if r.strategy == "optimizer")
            optimizer_points = optimizer_row.risk_reduction_pct or 0.0
            # Keep the optimum's own value as well as the gap. Comparing the optimizer
            # against the *gap* is a category error — the gap is already a difference, so
            # that comparison fires on every run.
            optimum_absolute = optimum_row.risk_reduction_pct or 0.0
            optimum_points = optimum_absolute - optimizer_points

    optimizer_row = next(r for r in rows if r.strategy == "optimizer")
    cvss_row = next((r for r in rows if r.strategy == "cvss_first"), None)
    optimizer_points = optimizer_row.risk_reduction_pct or 0.0
    cvss_points = cvss_row.risk_reduction_pct or 0.0 if cvss_row else None
    best = best_outcome([evaluator.evaluate(sel, label=name) for name, sel in selections.items()])

    # Soundness check. Brute force enumerates every feasible portfolio, so nothing can beat
    # it. If the optimizer appears to, the optimizer is not better — it is *invalid*, and the
    # likely cause is an infeasible selection (a prerequisite dropped while the control that
    # needs it stayed). An earlier version of this comparison only required
    # ``gap <= 0.01``, which counted a 4.88-point "win" over the optimum as *optimal* and hid
    # exactly that bug. A bound that can be violated is not a bound.
    if optimum_absolute is not None and optimizer_points > optimum_absolute + SOUNDNESS_TOLERANCE:
        raise AssertionError(
            f"optimizer beat the exact optimum at budget {budget}, seed {seed}: "
            f"{optimizer_points:.2f}% vs {optimum_absolute:.2f}%. Brute force enumerates every "
            f"feasible portfolio, so this means the optimizer returned an infeasible selection "
            f"— check prerequisites."
        )

    return BudgetResult(
        budget=budget,
        seed=seed,
        n_trials=n_trials,
        baseline_eal=baseline_eal,
        rows=rows,
        best_label=best.label,
        optimizer_vs_cvss_points=(
            round(optimizer_points - cvss_points, 4) if cvss_points is not None else None
        ),
        optimizer_gap_to_optimum_points=(
            round(optimum_points, 4) if optimum_points is not None else None
        ),
        exact_optimum=has_optimum,
    )


def run_benchmark(
    engine: ScenarioEngine,
    *,
    budgets: tuple[float, ...] = DEFAULT_BUDGETS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    n_trials: int = DEFAULT_TRIALS,
    exact: bool = True,
) -> BenchmarkReport:
    from app.risk.monte_carlo import library_versions

    results: list[BudgetResult] = []
    for budget in budgets:
        for seed in seeds:
            results.append(run_once(engine, budget, n_trials=n_trials, seed=seed, exact=exact))

    return BenchmarkReport(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        organization=engine.context.organization_name,
        currency=engine.context.currency,
        candidates=len(engine.candidates),
        scenarios=len(engine.context.scenarios),
        trials=n_trials,
        seeds=list(seeds),
        budgets=list(budgets),
        python=platform.python_version(),
        library_versions=library_versions(),
        results=results,
    )


# --- rendering ----------------------------------------------------------------------------
def _inr(value: float) -> str:
    if abs(value) >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"₹{value / 1e5:.1f} L"
    return f"₹{value:,.0f}"


def write_json(report: BenchmarkReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def render_markdown(report: BenchmarkReport) -> str:
    lines: list[str] = [
        "# Benchmark — optimizer vs naive strategies",
        "",
        "**Generated by `make benchmark`.** Do not edit by hand — re-run it.",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Organization: {report.organization}",
        f"- Scenarios modelled: {report.scenarios} · investment candidates: {report.candidates}",
        f"- Monte Carlo trials per evaluation: {report.trials:,} · seeds: {report.seeds}",
        f"- Python {report.python} · "
        + ", ".join(f"{k} {v}" for k, v in sorted(report.library_versions.items())),
        "",
        "Every figure below is **re-simulated** through the same evaluation harness with the "
        "selection applied. Nothing is summed additively, because overlapping controls deliver "
        "diminishing returns (submodular risk reduction).",
        "",
    ]

    by_seed: dict[int, list[BudgetResult]] = {}
    for result in report.results:
        by_seed.setdefault(result.seed, []).append(result)

    for seed, results in by_seed.items():
        lines.append(f"## Seed {seed}")
        lines.append("")
        lines.append(
            "| Budget | Strategy | Controls | Spend | EAL after | Risk removed | ₹ removed / ₹ |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for result in sorted(results, key=lambda r: r.budget):
            for index, row in enumerate(result.rows):
                budget_cell = _inr(result.budget) if index == 0 else ""
                marker = " **←**" if row.strategy == "optimizer" else ""
                removal = (
                    f"{row.risk_reduction_pct:.2f}%"
                    if row.risk_reduction_pct is not None
                    else "n/a"
                )
                ratio = (
                    f"{row.risk_removed_per_rupee:.2f}"
                    if row.risk_removed_per_rupee is not None
                    else "n/a"
                )
                lines.append(
                    f"| {budget_cell} | {row.label}{marker} | {row.controls} | "
                    f"{_inr(row.spend)} | {_inr(row.eal)} | {removal} | {ratio} |"
                )
        lines.append("")

    lines.append("## Headline findings")
    lines.append("")

    gaps = [
        r.optimizer_vs_cvss_points for r in report.results if r.optimizer_vs_cvss_points is not None
    ]
    if gaps:
        wins = sum(1 for gap in gaps if gap > 0.01)
        ties = sum(1 for gap in gaps if -0.01 <= gap <= 0.01)
        losses = sum(1 for gap in gaps if gap < -0.01)
        lines.append(
            f"- Against **highest-CVSS first** (the strategy a real team defaults to): the "
            f"optimizer removed more risk in **{wins} of {len(gaps)}** runs, tied in {ties}, "
            f"and lost in {losses}."
        )
        lines.append(
            f"- Advantage ranges from **{min(gaps):+.2f}** to **{max(gaps):+.2f}** percentage "
            f"points, average **{sum(gaps) / len(gaps):+.2f}**."
        )

        worst = [r for r in report.results if (r.optimizer_vs_cvss_points or 0) < -0.01]
        if worst:
            lines.append(
                f"- **Where it loses:** all {len(worst)} losing runs are at budgets where the "
                f"entire candidate set is affordable ({_inr(max(r.budget for r in worst))} and "
                f"above). Severity-first then funds every control by brute force and edges ahead; "
                f"the optimizer leaves a few controls unfunded instead. The gap is at most "
                f"**{abs(min(gaps)):.2f} percentage points**, but it is a real failure mode of "
                f"the surrogate objective and is stated rather than hidden."
            )
            lines.append(
                "- This finding is exactly why the portfolio is scored by **re-simulation** and "
                "not by the solver's own objective. A benchmark that only reported the wins "
                "would have concealed it."
            )

    optimum_gaps = [r.optimizer_gap_to_optimum_points for r in report.results if r.exact_optimum]
    if optimum_gaps:
        best_gap = max(optimum_gaps)
        optimal = sum(1 for g in optimum_gaps if g <= 0.01)
        lines.append(
            f"- Against the **exact optimum** (brute force over all feasible portfolios, only "
            f"tractable at this candidate count): the CP-SAT portfolio is optimal in "
            f"**{optimal} of {len(optimum_gaps)}** runs, and never more than "
            f"**{best_gap:.2f}** percentage points from the best possible answer."
        )
    lines.append("")

    lines.append("## Reproducing")
    lines.append("")
    lines.append("```bash")
    lines.append("make benchmark          # rewrites this file and docs/benchmark.json")
    lines.append("```")
    lines.append("")
    lines.append(
        "Same seed + same trial count ⇒ identical numbers. Simulations use "
        "`numpy.random.default_rng(seed)` (PCG64) and CP-SAT runs single-threaded with a fixed "
        "random seed."
    )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_BUDGETS",
    "DEFAULT_SEEDS",
    "DEFAULT_TRIALS",
    "STRATEGY_LABELS",
    "BenchmarkReport",
    "BudgetResult",
    "StrategyRow",
    "render_markdown",
    "run_benchmark",
    "run_once",
    "write_json",
]
