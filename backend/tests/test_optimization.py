"""Candidate construction, evaluation harness, solver constraints, and baselines."""

from __future__ import annotations

import pytest

from app.engine.service import get_engine
from app.optimization.baseline import (
    brute_force,
    cheapest_first,
    cvss_first,
    density_greedy,
    epss_first,
    exact_knapsack,
    random_selection,
)
from app.optimization.candidates import (
    Candidate,
    candidates_by_id,
    candidates_from_context,
)
from app.optimization.context import PlanningContext, load_planning_context
from app.optimization.harness import PortfolioEvaluator
from app.optimization.portfolio import comparison_table, explain_selection
from app.optimization.refine import refine_selection
from app.optimization.solver import overlap_penalty, solve_portfolio, surrogate_value
from app.risk.monte_carlo import SimulationConfig

BUDGET = 2_500_000.0
TRIALS = 2_000


@pytest.fixture(scope="module")
def context() -> PlanningContext:
    return load_planning_context()


@pytest.fixture(scope="module")
def candidates(context: PlanningContext) -> list[Candidate]:
    return candidates_from_context(context)


@pytest.fixture(scope="module")
def evaluator(context: PlanningContext, candidates: list[Candidate]) -> PortfolioEvaluator:
    return PortfolioEvaluator(context, candidates, SimulationConfig(n_trials=TRIALS, seed=42))


def _assert_feasible(
    selection: tuple[str, ...], candidates: list[Candidate], budget: float
) -> None:
    by_id = candidates_by_id(candidates)
    spend = sum(by_id[cid].cost for cid in selection)
    assert spend <= budget + 1e-9, f"over budget: {spend} > {budget}"
    for cid in selection:
        for prerequisite in by_id[cid].prerequisites:
            assert prerequisite in selection, f"{cid} selected without {prerequisite}"


# --- context + candidates ---------------------------------------------------------------


def test_context_materializes_every_catalogue_scenario(context: PlanningContext) -> None:
    assert len(context.catalogue) == 8
    assert len(context.scenarios) == 8
    assert set(context.scenarios) == set(context.catalogue)


def test_candidates_are_built_from_controls_with_headroom(
    context: PlanningContext, candidates: list[Candidate]
) -> None:
    assert len(candidates) == 11
    for candidate in candidates:
        assert candidate.scenarios, "every candidate must protect at least one scenario"
        assert candidate.target_effectiveness > candidate.current_effectiveness
        assert candidate.cost > 0
        assert candidate.annualized_cost == pytest.approx(candidate.cost / 3.0)


def test_prerequisites_reference_real_candidates(candidates: list[Candidate]) -> None:
    by_id = candidates_by_id(candidates)
    for candidate in candidates:
        for prerequisite in candidate.prerequisites:
            assert prerequisite in by_id


def test_overlap_penalty_is_zero_without_shared_scenarios(candidates: list[Candidate]) -> None:
    disjoint = [
        c for c in candidates if c.scenarios and set(c.scenarios).isdisjoint({"SCN-RANSOM-01"})
    ]
    if len(disjoint) >= 2:
        a, b = disjoint[0], disjoint[1]
        assert overlap_penalty(a, b, 1.0, 1.0) >= 0.0
    shared = [c for c in candidates if "SCN-RANSOM-01" in c.scenarios]
    if len(shared) >= 2:
        assert overlap_penalty(shared[0], shared[1], 100.0, 100.0) > 0.0


# --- harness ---------------------------------------------------------------------------


def test_baseline_matches_the_empty_selection(evaluator: PortfolioEvaluator) -> None:
    baseline = evaluator.baseline()
    assert baseline.selection == ()
    assert baseline.eal == evaluator.evaluate(()).eal
    assert baseline.risk_reduction == pytest.approx(0.0)


def test_selecting_controls_reduces_expected_loss(
    evaluator: PortfolioEvaluator, candidates: list[Candidate]
) -> None:
    baseline = evaluator.baseline()
    outcome = evaluator.evaluate((candidates[0].id,))
    assert outcome.eal < baseline.eal
    assert outcome.risk_reduction > 0
    assert outcome.risk_removed_per_rupee is not None


def test_percentiles_are_ordered(evaluator: PortfolioEvaluator) -> None:
    outcome = evaluator.evaluate(())
    assert outcome.eal <= outcome.p90 <= outcome.p95


def test_evaluation_is_reproducible(context: PlanningContext, candidates: list[Candidate]) -> None:
    first = PortfolioEvaluator(context, candidates, SimulationConfig(n_trials=500, seed=11))
    second = PortfolioEvaluator(context, candidates, SimulationConfig(n_trials=500, seed=11))
    selection = (candidates[0].id, candidates[1].id)
    assert first.evaluate(selection).eal == second.evaluate(selection).eal


def test_scenario_outcomes_cover_every_scenario(evaluator: PortfolioEvaluator) -> None:
    outcome = evaluator.evaluate(())
    assert len(outcome.scenarios) == 8
    assert outcome.n_scenarios == 8


# --- solver ----------------------------------------------------------------------------


def test_zero_budget_selects_nothing(candidates: list[Candidate]) -> None:
    result = solve_portfolio(candidates, budget=0.0, marginal_reductions={})
    assert result.selection == ()


def test_large_budget_is_optimal_under_the_surrogate(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    """With a budget that can afford everything, the chosen set must beat every alternative
    under the surrogate — including selecting all candidates (which is *not* optimal, because
    overlapping controls cost value)."""
    total = sum(candidate.cost for candidate in candidates)
    generous = total * 1.1
    marginals = evaluator.marginal_reductions()
    result = solve_portfolio(candidates, budget=generous, marginal_reductions=marginals)

    _assert_feasible(result.selection, candidates, generous)
    assert result.status == "OPTIMAL"
    everything = tuple(sorted(candidate.id for candidate in candidates))
    assert result.surrogate_objective >= surrogate_value(everything, candidates, marginals) - 1e-6


def test_large_budget_selects_all_when_candidates_do_not_overlap() -> None:
    from app.risk.control_effect import ControlCategory

    def make(index: int, scenario: str) -> Candidate:
        return Candidate(
            id=f"C{index}",
            name=f"candidate {index}",
            control_id=f"CTL{index}",
            category=ControlCategory.RESISTIVE,
            cost=100.0,
            current_effectiveness=0.1,
            target_effectiveness=0.8,
            scenarios=(scenario,),
        )

    disjoint = [make(0, "S1"), make(1, "S2"), make(2, "S3")]
    result = solve_portfolio(
        disjoint, budget=1_000.0, marginal_reductions={c.id: 500.0 for c in disjoint}
    )
    assert set(result.selection) == {"C0", "C1", "C2"}


def test_budget_is_respected(candidates: list[Candidate], evaluator: PortfolioEvaluator) -> None:
    result = solve_portfolio(
        candidates, budget=1_000_000.0, marginal_reductions=evaluator.marginal_reductions()
    )
    _assert_feasible(result.selection, candidates, 1_000_000.0)
    assert result.spend <= 1_000_000.0


def test_prerequisites_are_enforced(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    result = solve_portfolio(
        candidates, budget=BUDGET, marginal_reductions=evaluator.marginal_reductions()
    )
    _assert_feasible(result.selection, candidates, BUDGET)
    # the demo has at least one prerequisite relation; make sure the test exercises it
    assert any(candidate.prerequisites for candidate in candidates)


def test_mandatory_candidate_is_always_funded(evaluator: PortfolioEvaluator) -> None:
    from dataclasses import replace

    forced = replace(evaluator.candidates["INV-CTL-EMAIL"], mandatory=True)
    candidates = [forced if c.id == "INV-CTL-EMAIL" else c for c in evaluator.candidates.values()]
    result = solve_portfolio(candidates, budget=BUDGET, marginal_reductions={})
    assert "INV-CTL-EMAIL" in result.selection


def test_mandatory_over_budget_is_infeasible(evaluator: PortfolioEvaluator) -> None:
    from dataclasses import replace

    forced = replace(evaluator.candidates["INV-CTL-SEG"], mandatory=True)
    candidates = [forced if c.id == "INV-CTL-SEG" else c for c in evaluator.candidates.values()]
    result = solve_portfolio(candidates, budget=1000.0, marginal_reductions={})
    assert result.selection == ()
    assert result.status in {"INFEASIBLE", "UNKNOWN"}


def test_solver_is_deterministic(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    marginals = evaluator.marginal_reductions()
    first = solve_portfolio(candidates, budget=BUDGET, marginal_reductions=marginals)
    second = solve_portfolio(candidates, budget=BUDGET, marginal_reductions=marginals)
    assert first.selection == second.selection
    assert first.surrogate_objective == second.surrogate_objective


# --- baselines -------------------------------------------------------------------------


def test_baselines_produce_feasible_portfolios(
    context: PlanningContext, candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    marginals = evaluator.marginal_reductions()
    strategies = {
        "cvss": cvss_first(candidates, context, BUDGET),
        "epss": epss_first(candidates, context, BUDGET),
        "density": density_greedy(candidates, BUDGET, marginals),
        "cheapest": cheapest_first(candidates, BUDGET),
        "random": random_selection(candidates, BUDGET, seed=3),
        "knapsack": exact_knapsack(candidates, BUDGET, marginals),
    }
    for name, selection in strategies.items():
        _assert_feasible(selection, candidates, BUDGET)
        assert selection, f"{name} selected nothing"


def test_optimizer_is_at_least_as_good_as_every_baseline(
    context: PlanningContext, candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    marginals = evaluator.marginal_reductions()
    result = solve_portfolio(candidates, budget=BUDGET, marginal_reductions=marginals)
    best = evaluator.evaluate(result.selection).risk_reduction

    for selection in (
        cvss_first(candidates, context, BUDGET),
        epss_first(candidates, context, BUDGET),
        density_greedy(candidates, BUDGET, marginals),
        cheapest_first(candidates, BUDGET),
        random_selection(candidates, BUDGET, seed=5),
    ):
        assert best >= evaluator.evaluate(selection).risk_reduction - 1e-6


def test_optimizer_beats_cvss_first_spend_for_spend(
    context: PlanningContext, candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    marginals = evaluator.marginal_reductions()
    result = solve_portfolio(candidates, budget=BUDGET, marginal_reductions=marginals)
    optimized = evaluator.evaluate(result.selection)
    naive = evaluator.evaluate(cvss_first(candidates, context, BUDGET))
    assert optimized.risk_reduction >= naive.risk_reduction
    assert optimized.risk_removed_per_rupee is not None


def test_brute_force_finds_the_true_optimum_on_a_small_set(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    subset = candidates[:4]
    exact = brute_force(subset, BUDGET, evaluator)
    assert exact is not None
    _assert_feasible(exact, subset, BUDGET)
    # brute force enumerates the feasible set, so it must beat the density heuristic
    heuristic = density_greedy(subset, BUDGET, evaluator.marginal_reductions())
    assert (
        evaluator.evaluate(exact).risk_reduction
        >= evaluator.evaluate(heuristic).risk_reduction - 1e-9
    )


def test_brute_force_declines_large_instances(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    assert brute_force(candidates, BUDGET, evaluator, max_candidates=4) is None


# --- explanation -----------------------------------------------------------------------


def test_explain_selection_covers_every_selected_item(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    selection = density_greedy(candidates, BUDGET, evaluator.marginal_reductions())
    rows = explain_selection(selection, candidates, evaluator)
    assert {row["candidate_id"] for row in rows} == set(selection)
    for row in rows:
        assert row["chain"]
        assert row["factor"] in {
            "contact_frequency",
            "probability_of_action",
            "resistance_strength",
            "loss_magnitude",
        }
        assert row["scenario_count"] >= 1


def test_comparison_table_reports_reduction(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    baseline = evaluator.baseline()
    outcome = evaluator.evaluate((candidates[0].id,), label="test")
    table = comparison_table([baseline, outcome])
    assert table[0]["label"] == "current posture"
    assert float(table[1]["risk_reduction"]) > 0


# --- refinement against the true objective -----------------------------------------------
def test_refine_never_worsens_the_objective(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    """Refinement is a strict improvement step: it may only lower the simulated EAL."""
    marginals = evaluator.marginal_reductions()
    proposal = solve_portfolio(candidates, budget=BUDGET, marginal_reductions=marginals)
    before = evaluator.evaluate(proposal.selection).eal

    refined = refine_selection(
        proposal.selection,
        candidates,
        budget=BUDGET,
        evaluate_eal=lambda selection: evaluator.evaluate(selection).eal,
    )
    assert evaluator.evaluate(refined).eal <= before + 1e-6


def test_refine_respects_the_budget(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    marginals = evaluator.marginal_reductions()
    proposal = solve_portfolio(candidates, budget=BUDGET, marginal_reductions=marginals)
    refined = refine_selection(
        proposal.selection,
        candidates,
        budget=BUDGET,
        evaluate_eal=lambda selection: evaluator.evaluate(selection).eal,
    )
    assert evaluator.selection_cost(refined) <= BUDGET + 1e-6


def _stub_candidate(
    candidate_id: str, cost: float, prerequisites: tuple[str, ...] = ()
) -> Candidate:
    return Candidate(
        id=candidate_id,
        name=candidate_id,
        control_id=candidate_id,
        category="resistive",
        cost=cost,
        current_effectiveness=0.2,
        target_effectiveness=0.8,
        scenarios=(),
        prerequisites=prerequisites,
    )


def test_refine_crosses_a_prerequisite_valley() -> None:
    """A prerequisite that is worthless alone must still be funded to unlock its successor.

    This is the real failure mode: CSPM is gated behind SIEM, and SIEM's marginal
    contribution is near zero because it overlaps an already-funded control. A search
    that only accepted improvements at each individual step could never cross that
    valley — so the chain is evaluated as one atomic move. Uses a deterministic
    objective so the test measures the search, not Monte Carlo noise.
    """
    gate = _stub_candidate("GATE", 100.0)
    payoff = _stub_candidate("PAYOFF", 100.0, prerequisites=("GATE",))

    landscape = {
        (): 100.0,
        ("GATE",): 100.0,  # worthless on its own — the valley
        ("PAYOFF",): 100.0,  # prerequisite unmet, so no effect
        ("GATE", "PAYOFF"): 40.0,  # the prize, only reachable through GATE
    }

    refined = refine_selection(
        (),
        [gate, payoff],
        budget=200.0,
        evaluate_eal=lambda selection: landscape[tuple(sorted(selection))],
    )
    assert set(refined) == {"GATE", "PAYOFF"}


def test_refine_rejects_a_chain_that_costs_too_much() -> None:
    """The atomic move must still respect the budget."""
    gate = _stub_candidate("GATE", 100.0)
    payoff = _stub_candidate("PAYOFF", 150.0, prerequisites=("GATE",))
    landscape = {(): 100.0, ("GATE",): 100.0}

    refined = refine_selection(
        (),
        [gate, payoff],
        budget=200.0,
        evaluate_eal=lambda selection: landscape.get(tuple(sorted(selection)), 100.0),
    )
    assert refined == ()


def test_refine_keeps_prerequisites_satisfied(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    by_id = candidates_by_id(candidates)
    refined = refine_selection(
        (),
        candidates,
        budget=sum(candidate.cost for candidate in candidates),
        evaluate_eal=lambda selection: evaluator.evaluate(selection).eal,
    )
    for candidate_id in refined:
        for prerequisite in by_id[candidate_id].prerequisites:
            if prerequisite in by_id:
                assert prerequisite in refined


def test_refine_reaches_the_optimum_with_a_sufficient_budget(
    candidates: list[Candidate], evaluator: PortfolioEvaluator
) -> None:
    """Given the whole candidate set affordable and enough trials to resolve the signal,
    refinement must find the full portfolio — the surrogate alone under-selects."""
    refined = refine_selection(
        (),
        candidates,
        budget=sum(candidate.cost for candidate in candidates),
        evaluate_eal=lambda selection: evaluator.evaluate(selection).eal,
    )
    full = tuple(sorted(candidate.id for candidate in candidates))
    assert evaluator.evaluate(refined).risk_reduction >= (
        evaluator.evaluate(full).risk_reduction - 1e-6
    )


def test_engine_optimizer_never_loses_to_a_baseline(
    context: PlanningContext, candidates: list[Candidate]
) -> None:
    """Across budgets, the shipped optimizer must match or beat every baseline it reports."""
    engine = get_engine()
    for budget in (500_000.0, 1_000_000.0, 2_500_000.0, 5_000_000.0, 10_000_000.0):
        _, outcomes = engine.optimize(budget, n_trials=5_000, seed=42)
        by_label = {outcome.label: outcome for outcome in outcomes}
        optimizer = by_label["optimizer"]
        for label, outcome in by_label.items():
            if label in {"current posture", "optimizer"}:
                continue
            assert optimizer.risk_reduction >= outcome.risk_reduction - 1e-6, (
                f"optimizer lost to {label} at budget {budget}"
            )


# --- feasibility: a portfolio must be purchasable ----------------------------------------
def _prerequisite_violations(selection, candidates) -> list[tuple[str, str]]:
    by_id = candidates_by_id(candidates)
    chosen = set(selection)
    return [
        (cid, prerequisite)
        for cid in chosen
        for prerequisite in by_id[cid].prerequisites
        if prerequisite in by_id and prerequisite not in chosen
    ]


def test_refine_never_returns_an_infeasible_selection(candidates: list[Candidate]) -> None:
    """Regression: the swap move once dropped a prerequisite and kept the control needing it.

    Dropping SIEM while CSPM stayed funded produced a portfolio the solver would never
    return, which scored *better than the exact optimum* — the signature of an invalid
    answer masquerading as a good one.
    """
    evaluator = PortfolioEvaluator(
        load_planning_context(), candidates, SimulationConfig(n_trials=2_000, seed=42)
    )
    for budget in (500_000.0, 1_500_000.0, 2_500_000.0, 4_000_000.0, 10_000_000.0):
        refined = refine_selection(
            (),
            candidates,
            budget=budget,
            evaluate_eal=lambda selection: evaluator.evaluate(selection).eal,
        )
        assert not _prerequisite_violations(refined, candidates), (
            f"infeasible selection at budget {budget}: {refined}"
        )


def test_engine_optimizer_never_returns_an_infeasible_selection(
    candidates: list[Candidate],
) -> None:
    """The shipped optimizer must return a purchasable portfolio at every budget."""
    engine = get_engine()
    for budget in (500_000.0, 1_000_000.0, 2_500_000.0, 5_000_000.0, 10_000_000.0):
        result, _ = engine.optimize(budget, n_trials=2_000, seed=42)
        violations = _prerequisite_violations(result.selection, candidates)
        assert not violations, f"budget {budget}: unmet prerequisites {violations}"


def test_optimizer_never_exceeds_the_exact_optimum(candidates: list[Candidate]) -> None:
    """A bound that can be violated is not a bound.

    Brute force enumerates every feasible portfolio, so if the optimizer ever appears to
    beat it, the optimizer is invalid rather than better. This assertion is what caught the
    prerequisite bug in the benchmark.
    """
    evaluator = PortfolioEvaluator(
        load_planning_context(), candidates, SimulationConfig(n_trials=2_000, seed=42)
    )
    engine = get_engine()
    for budget in (1_000_000.0, 2_500_000.0, 5_000_000.0, 10_000_000.0):
        result, _ = engine.optimize(budget, n_trials=2_000, seed=42)
        optimizer = evaluator.evaluate(result.selection).risk_reduction
        optimum = brute_force(candidates, budget, evaluator)
        if optimum is None:
            continue
        best = evaluator.evaluate(optimum).risk_reduction
        assert optimizer <= best + 1e-6, (
            f"optimizer beat the exact optimum at budget {budget} "
            f"({optimizer:.0f} > {best:.0f}) — it must have returned an invalid portfolio"
        )
