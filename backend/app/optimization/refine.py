"""Local refinement of a candidate portfolio against the *true* objective.

CP-SAT optimizes a **surrogate**: standalone marginal reductions minus pairwise-overlap
penalties. That surrogate is deliberately conservative about overlap, and because it is only
an approximation it can *under-select* — concluding that the next control is not worth
funding when, measured by re-simulation, it plainly is.

So the surrogate is used only to *propose*, never to decide. This module takes that
proposal and improves it directly against the re-simulated objective with two moves:

- **add** — fund one more affordable control if it lowers the simulated EAL;
- **swap** — drop one control and fund another in its place, if the exchange is
  affordable and lowers the simulated EAL.

Both moves respect the budget and prerequisites, and both are judged only by
``evaluate_eal`` — the same re-simulation the baselines are scored with. The result is
therefore never worse than the proposal, and never worse than the greedy baseline's own
local search.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import combinations as _combinations

from app.optimization.candidates import Candidate, candidates_by_id

MAX_STEPS = 400
TOLERANCE = 1e-9


def _cost(selection: tuple[str, ...], by_id: dict[str, Candidate]) -> float:
    return sum(by_id[cid].cost for cid in selection if cid in by_id)


def _closure(
    candidate_id: str, selection: tuple[str, ...], by_id: dict[str, Candidate]
) -> tuple[str, ...] | None:
    """The candidate plus every transitively-unmet prerequisite.

    Prerequisites must be funded together, and a prerequisite can be worthless on its
    own — CSPM is gated behind SIEM, but SIEM's *marginal* contribution is near zero
    because it overlaps an already-funded control. A move that only accepted
    improvements at each individual step could never cross that valley. So the chain is
    evaluated as one atomic move and judged on its combined effect.
    """
    pending = [candidate_id]
    needed: set[str] = set()
    while pending:
        current = pending.pop()
        if current in needed:
            continue
        candidate = by_id.get(current)
        if candidate is None:
            return None
        needed.add(current)
        for prerequisite in candidate.prerequisites:
            if prerequisite not in selection:
                if prerequisite not in by_id:
                    return None
                pending.append(prerequisite)
    return tuple(sorted(needed))


def _is_feasible(selection: tuple[str, ...], by_id: dict[str, Candidate]) -> bool:
    """Every selected candidate must have all of its prerequisites selected too.

    This check exists because of a real defect. The swap move drops controls to make room
    for others, and dropping one can silently break a *different* control that stays: drop
    SIEM and CSPM remains funded with an unmet prerequisite. The result is a portfolio the
    solver would never have returned, it overspends nothing and validates nothing, and it
    scored better than the true optimum — which is how the benchmark caught it.

    An infeasible portfolio is not a better portfolio. It is an invalid one.
    """
    chosen = set(selection)
    for candidate_id in chosen:
        candidate = by_id.get(candidate_id)
        if candidate is None:
            return False
        for prerequisite in candidate.prerequisites:
            if prerequisite in by_id and prerequisite not in chosen:
                return False
    return True


def _repair(selection: tuple[str, ...], by_id: dict[str, Candidate]) -> tuple[str, ...]:
    """Drop any candidate whose prerequisites are not satisfied, transitively.

    Used defensively on the incoming selection: the solver returns a feasible model, but
    refinement must not depend on that to stay correct.
    """
    chosen = set(selection)
    changed = True
    while changed:
        changed = False
        for candidate_id in sorted(chosen):
            candidate = by_id.get(candidate_id)
            if candidate is None:
                chosen.discard(candidate_id)
                changed = True
                continue
            for prerequisite in candidate.prerequisites:
                if prerequisite in by_id and prerequisite not in chosen:
                    chosen.discard(candidate_id)
                    changed = True
                    break
    return tuple(sorted(chosen))


def refine_selection(
    initial: tuple[str, ...] | list[str],
    candidates: list[Candidate],
    *,
    budget: float,
    evaluate_eal: Callable[[tuple[str, ...]], float],
    max_steps: int = MAX_STEPS,
) -> tuple[str, ...]:
    """Improve a selection against the re-simulated objective. Returns the best found."""
    by_id = candidates_by_id(candidates)

    mandatory = tuple(sorted(c.id for c in candidates if c.mandatory))
    current = _repair(tuple(sorted(set(initial) | set(mandatory))), by_id)
    if _cost(current, by_id) > budget + TOLERANCE:
        # Infeasible starting point (mandatory controls exceed the budget) — leave it alone.
        return tuple(sorted(set(initial)))

    current_eal = evaluate_eal(current)

    steps = 0
    while steps < max_steps:
        exhausted = False

        # --- move 1: fund one more control, together with any prerequisites it needs ---
        best_add: tuple[tuple[str, ...], float] | None = None
        for candidate in candidates:
            if candidate.id in current:
                continue
            closure = _closure(candidate.id, current, by_id)
            if closure is None:
                continue
            additions = tuple(cid for cid in closure if cid not in current)
            if not additions:
                continue
            if (
                _cost(current, by_id) + sum(by_id[cid].cost for cid in additions)
                > budget + TOLERANCE
            ):
                continue
            steps += 1
            if steps >= max_steps:
                exhausted = True
                break
            proposal = tuple(sorted(current + additions))
            eal = evaluate_eal(proposal)
            if eal < current_eal - TOLERANCE and (best_add is None or eal < best_add[1]):
                best_add = (proposal, eal)

        if best_add is not None:
            current, current_eal = best_add
            continue

        # --- move 2: exchange funded controls for a new chain -------------------------
        best_swap: tuple[tuple[str, ...], float] | None = None
        for dropped_count in (1, 2):
            if dropped_count > len(current):
                break
            for dropped in _combinations(current, dropped_count):
                if any(cid in mandatory for cid in dropped):
                    continue
                reduced = tuple(cid for cid in current if cid not in dropped)
                # Dropping a control can invalidate a control that remains. Without this
                # guard the search proposes portfolios the solver would never return.
                if not _is_feasible(reduced, by_id):
                    continue
                for candidate in candidates:
                    if candidate.id in reduced:
                        continue
                    closure = _closure(candidate.id, reduced, by_id)
                    if closure is None:
                        continue
                    additions = tuple(cid for cid in closure if cid not in reduced)
                    if not additions:
                        continue
                    cost = _cost(reduced, by_id) + sum(by_id[cid].cost for cid in additions)
                    if cost > budget + TOLERANCE:
                        continue
                    steps += 1
                    if steps >= max_steps:
                        exhausted = True
                        break
                    proposal = tuple(sorted(reduced + additions))
                    if not _is_feasible(proposal, by_id):
                        continue
                    eal = evaluate_eal(proposal)
                    if eal < current_eal - TOLERANCE and (best_swap is None or eal < best_swap[1]):
                        best_swap = (proposal, eal)
                if exhausted:
                    break
            if exhausted:
                break

        if best_swap is not None:
            current, current_eal = best_swap
            continue

        # Neither move improved the objective — this is a local optimum.
        break

    return _repair(current, by_id)


__all__ = ["MAX_STEPS", "refine_selection"]
