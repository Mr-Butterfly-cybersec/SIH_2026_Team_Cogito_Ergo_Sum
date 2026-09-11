"""Budget-constrained portfolio selection with OR-Tools CP-SAT.

Risk reduction is **submodular** — controls overlap, so two controls covering the same
scenario deliver less than the sum of their standalone reductions. CP-SAT therefore
optimizes a *surrogate*: standalone marginal reductions with pairwise-overlap penalties
linearized via AND variables. The chosen portfolio is then scored for real by the
evaluation harness (see ``harness.py``), and so are the baselines, so everything is
compared on the same footing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.optimization.candidates import Candidate, candidates_by_id

MONEY_SCALE = 100  # keep CP-SAT coefficients integral
DEFAULT_TIME_LIMIT = 10.0


@dataclass(frozen=True)
class OptimizationResult:
    selection: tuple[str, ...]
    status: str
    surrogate_objective: float
    spend: float
    solver: str = "cp-sat"

    def to_dict(self) -> dict[str, object]:
        return {
            "selection": list(self.selection),
            "status": self.status,
            "surrogate_objective": round(self.surrogate_objective, 2),
            "spend": round(self.spend, 2),
            "solver": self.solver,
        }


def overlap_penalty(a: Candidate, b: Candidate, reduction_a: float, reduction_b: float) -> float:
    """How much of the smaller standalone reduction is double-counted by choosing both."""
    scenarios_a, scenarios_b = set(a.scenarios), set(b.scenarios)
    if not scenarios_a or not scenarios_b:
        return 0.0
    shared = scenarios_a & scenarios_b
    if not shared:
        return 0.0
    share = len(shared) / max(len(scenarios_a), len(scenarios_b))
    return min(reduction_a, reduction_b) * share


def surrogate_value(
    selection: tuple[str, ...] | list[str],
    candidates: list[Candidate],
    marginal_reductions: dict[str, float],
) -> float:
    """Value of a selection under the surrogate objective (reductions minus overlaps)."""
    by_id = candidates_by_id(candidates)
    chosen = [cid for cid in selection if cid in by_id]
    value = sum(marginal_reductions.get(cid, 0.0) for cid in chosen)
    for i, first in enumerate(chosen):
        for second in chosen[i + 1 :]:
            value -= overlap_penalty(
                by_id[first],
                by_id[second],
                marginal_reductions.get(first, 0.0),
                marginal_reductions.get(second, 0.0),
            )
    return value


def solve_portfolio(
    candidates: list[Candidate],
    *,
    budget: float,
    marginal_reductions: dict[str, float],
    time_limit: float = DEFAULT_TIME_LIMIT,
    seed: int = 42,
) -> OptimizationResult:
    if not candidates:
        return OptimizationResult((), "EMPTY", 0.0, 0.0)

    by_id = candidates_by_id(candidates)
    model = cp_model.CpModel()
    x = {candidate.id: model.new_bool_var(f"x_{candidate.id}") for candidate in candidates}

    # --- budget ---------------------------------------------------------------------
    model.add(
        sum(round(candidate.cost * MONEY_SCALE) * x[candidate.id] for candidate in candidates)
        <= round(budget * MONEY_SCALE)
    )

    # --- mandatory and prerequisites ------------------------------------------------
    for candidate in candidates:
        if candidate.mandatory:
            model.add(x[candidate.id] == 1)
        for prerequisite in candidate.prerequisites:
            if prerequisite in by_id:
                model.add_implication(x[candidate.id], x[prerequisite])

    # --- objective: standalone reductions minus pairwise overlap --------------------
    objective: list[cp_model.LinearExpr] = [
        round(marginal_reductions.get(candidate.id, 0.0) * MONEY_SCALE) * x[candidate.id]
        for candidate in candidates
    ]
    for i, a in enumerate(candidates):
        for b in candidates[i + 1 :]:
            penalty = overlap_penalty(
                a, b, marginal_reductions.get(a.id, 0.0), marginal_reductions.get(b.id, 0.0)
            )
            if penalty <= 0:
                continue
            both = model.new_bool_var(f"z_{a.id}_{b.id}")
            model.add_min_equality(both, [x[a.id], x[b.id]])
            objective.append(-round(penalty * MONEY_SCALE) * both)
    model.maximize(sum(objective))

    # --- solve deterministically ----------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return OptimizationResult((), status_name, 0.0, 0.0)

    selection = tuple(
        sorted(candidate.id for candidate in candidates if solver.value(x[candidate.id]) == 1)
    )
    spend = sum(by_id[cid].cost for cid in selection)
    return OptimizationResult(
        selection=selection,
        status=status_name,
        surrogate_objective=solver.objective_value / MONEY_SCALE,
        spend=spend,
    )
