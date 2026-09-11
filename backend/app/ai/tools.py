"""Read-only tools exposing the deterministic engine to the AI layer.

**The LLM is never the system of record for a number.** Every tool here delegates to
:class:`~app.engine.service.ScenarioEngine`, which in turn runs the auditable risk core. The
model's only job is to choose a tool and turn its result into prose.

Each tool returns a plain JSON-serialisable ``dict`` so the same payload can be (a) fed back
to the model as a tool result and (b) shown to a human as grounded evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.compliance.coverage import CoverageStatus
from app.engine.service import ScenarioEngine
from app.optimization.portfolio import best_outcome

DEFAULT_BUDGET = 2_500_000.0


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        """OpenAI-compatible function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


def _money(value: float) -> float:
    return round(value, 2)


# --- tool implementations ---------------------------------------------------------------
def _get_posture(engine: ScenarioEngine, **_ignored: Any) -> dict[str, Any]:
    baseline = engine.baseline()
    return {
        "organization": engine.context.organization_name,
        "currency": engine.context.currency,
        "expected_annual_loss": _money(baseline.eal),
        "p90": _money(baseline.p90),
        "p95": _money(baseline.p95),
        "scenarios_modelled": baseline.n_scenarios,
        "controls_in_place": len(engine.context.controls),
        "n_trials": baseline.n_trials,
        "seed": baseline.seed,
        "note": (
            "Aggregate of independent scenario distributions; the portfolio tail assumes "
            "scenario losses are additive."
        ),
    }


def _get_top_risks(engine: ScenarioEngine, limit: int = 5, **_ignored: Any) -> dict[str, Any]:
    baseline = engine.baseline()
    ranked = sorted(baseline.scenarios, key=lambda s: s.eal, reverse=True)[: max(1, limit)]

    exposure: list[dict[str, Any]] = []
    for outcome in ranked:
        entry = engine.context.catalogue.get(outcome.scenario_id)
        asset = engine.context.assets.get(entry.asset_id) if entry and entry.asset_id else None
        weakest = sorted(
            (
                control
                for control in engine.context.controls.values()
                if outcome.scenario_id in control.protects
            ),
            key=lambda c: c.effectiveness,
        )[:2]
        exposure.append(
            {
                "scenario_id": outcome.scenario_id,
                "name": outcome.name,
                "asset": asset.name if asset else None,
                "criticality_band": asset.criticality_band if asset else None,
                "expected_annual_loss": _money(outcome.eal),
                "p90": _money(outcome.p90),
                "p95": _money(outcome.p95),
                "max_cvss": engine.context.scenario_cvss(outcome.scenario_id),
                "max_epss": engine.context.scenario_epss(outcome.scenario_id),
                "cve_ids": list(entry.cve_ids) if entry else [],
                "weakest_controls": [
                    {
                        "control_id": control.control_id,
                        "name": control.name,
                        "effectiveness": round(control.effectiveness, 4),
                    }
                    for control in weakest
                ],
            }
        )

    return {
        "currency": engine.context.currency,
        "baseline_eal": _money(baseline.eal),
        "risks": exposure,
    }


def _optimize_budget(
    engine: ScenarioEngine, budget: float = DEFAULT_BUDGET, **_ignored: Any
) -> dict[str, Any]:
    result, outcomes = engine.optimize(float(budget))
    best = best_outcome(outcomes)
    optimizer = next((o for o in outcomes if o.label == "optimizer"), None)
    naive = next((o for o in outcomes if o.label == "cvss_first"), None)

    return {
        "currency": engine.context.currency,
        "budget": _money(float(budget)),
        "solver_status": result.status,
        "spend": _money(result.spend),
        "recommended_selection": list(result.selection),
        "strategies": [
            {
                "strategy": outcome.label,
                "controls": len(outcome.selection),
                "spend": _money(outcome.spend),
                "eal_after": _money(outcome.eal),
                "risk_reduction": _money(outcome.risk_reduction),
                "risk_reduction_pct": (
                    round(outcome.risk_reduction_pct * 100, 2)
                    if outcome.risk_reduction_pct is not None
                    else None
                ),
                "risk_removed_per_rupee": (
                    round(outcome.risk_removed_per_rupee, 3)
                    if outcome.risk_removed_per_rupee is not None
                    else None
                ),
            }
            for outcome in outcomes
        ],
        "best_strategy": best.label,
        "optimizer_vs_cvss_first_points": (
            round(
                (optimizer.risk_reduction_pct or 0.0) * 100
                - (naive.risk_reduction_pct or 0.0) * 100,
                2,
            )
            if optimizer and naive
            else None
        ),
        "method": (
            "CP-SAT optimizes a surrogate objective; the portfolio and every baseline are then "
            "scored by re-running the Monte Carlo engine, so overlapping controls are never "
            "summed."
        ),
    }


def _explain_control(engine: ScenarioEngine, control_id: str, **_ignored: Any) -> dict[str, Any]:
    control = engine.context.controls.get(control_id)
    if control is None:
        return {
            "error": f"unknown control: {control_id}",
            "known_controls": sorted(engine.context.controls),
        }

    from app.risk.control_effect import factor_effect

    effect = factor_effect(control.category, control.effectiveness)
    candidate_id = f"INV-{control_id}"
    candidate = next((c for c in engine.candidates if c.id == candidate_id), None)

    scenario_detail = []
    for scenario_id in control.protects:
        entry = engine.context.catalogue.get(scenario_id)
        outcome = next(
            (s for s in engine.baseline().scenarios if s.scenario_id == scenario_id), None
        )
        scenario_detail.append(
            {
                "scenario_id": scenario_id,
                "name": entry.name if entry else scenario_id,
                "expected_annual_loss": _money(outcome.eal) if outcome else None,
            }
        )

    return {
        "control_id": control_id,
        "name": control.name,
        "category": control.category.value,
        "effectiveness": round(control.effectiveness, 4),
        "faire_factor": effect.factor.value,
        "faire_effect": effect.describe(),
        "evidence": control.evidence,
        "protects": scenario_detail,
        "cost": _money(control.cost),
        "upgrade_candidate": (
            {
                "candidate_id": candidate.id,
                "current_effectiveness": round(candidate.current_effectiveness, 4),
                "target_effectiveness": candidate.target_effectiveness,
                "cost": _money(candidate.cost),
                "implementation_days": candidate.implementation_days,
                "operational_impact": candidate.operational_impact,
            }
            if candidate
            else None
        ),
    }


def _simulate_delay(
    engine: ScenarioEngine,
    scenario_id: str,
    days: int = 30,
    controls: list[str] | None = None,
    **_ignored: Any,
) -> dict[str, Any]:
    if scenario_id not in engine.context.scenarios:
        return {
            "error": f"unknown scenario: {scenario_id}",
            "known_scenarios": sorted(engine.context.scenarios),
        }
    selection = [c for c in (controls or [])]
    unknown = [c for c in selection if engine.candidate(c) is None]
    if unknown:
        return {"error": f"unknown candidates: {unknown}"}

    impact = engine.delay_impact(scenario_id, selection, int(days))
    return {
        "scenario_id": impact.scenario_id,
        "days": impact.days,
        "window_years": round(impact.window_years, 6),
        "currency": impact.currency,
        "baseline_annual_loss": _money(impact.baseline_eal),
        "hardened_annual_loss": _money(impact.hardened_eal),
        "loss_if_delayed": _money(impact.loss_if_delayed),
        "loss_if_remediated_now": _money(impact.loss_if_remediated_now),
        "avoidable_loss": _money(impact.avoidable_loss),
        "method": impact.to_dict()["method"],
    }


def _get_framework_mapping(
    engine: ScenarioEngine, framework_id: str | None = None, **_ignored: Any
) -> dict[str, Any]:
    report = engine.compliance_report()

    frameworks = []
    for entry in report.frameworks:
        if framework_id and entry.framework.id != framework_id:
            continue
        gaps = [r for r in entry.requirements if r.status is CoverageStatus.GAP]
        frameworks.append(
            {
                "framework": entry.framework.short_name,
                "version": entry.framework.version,
                "kind": entry.framework.kind.value,
                "coverage": round(entry.coverage, 4),
                "covered": entry.covered,
                "partial": entry.partial,
                "gaps": entry.gaps,
                "gap_exposure": _money(entry.gap_exposure),
                "worst_gaps": [
                    {
                        "requirement": row.requirement.name,
                        "references": list(row.references),
                        "exposure": _money(row.exposure),
                    }
                    for row in sorted(gaps, key=lambda r: r.exposure, reverse=True)[:3]
                ],
            }
        )

    if framework_id and not frameworks:
        return {
            "error": f"unknown framework: {framework_id}",
            "known_frameworks": sorted(f.framework.id for f in report.frameworks),
        }

    return {
        "catalog_version": report.catalog_version,
        "overall_coverage": round(report.overall_coverage, 4),
        "frameworks": frameworks,
        "unmapped_requirements": list(report.unmapped_requirements),
        "method": (
            "Coverage is computed from the measured effectiveness of controls actually in "
            "place, not from self-declared compliance."
        ),
    }


TOOL_SPECS: tuple[tuple[str, str, dict[str, Any], Callable[..., dict[str, Any]]], ...] = (
    (
        "get_posture",
        "Current aggregate cyber-risk posture: expected annual loss, P90 and P95, how many "
        "scenarios and controls are modelled. Use for questions about overall risk or exposure.",
        {"type": "object", "properties": {}, "required": []},
        _get_posture,
    ),
    (
        "get_top_risks",
        "Rank the modelled risk scenarios by expected annual loss, with the asset, its "
        "criticality band, the attached CVSS/EPSS evidence and the weakest controls. Use for "
        "'what is our biggest risk', 'which asset contributes most', 'where is the exposure'.",
        {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "How many risks to return (1-20).",
                    "default": 5,
                }
            },
            "required": [],
        },
        _get_top_risks,
    ),
    (
        "optimize_budget",
        "Solve for the security investment portfolio that removes the most modelled risk "
        "within a budget, and compare it with naive baselines. Use for 'what can we do with "
        "Rs 25 lakh', 'where should the budget go', 'is X better than Y'.",
        {
            "type": "object",
            "properties": {
                "budget": {
                    "type": "number",
                    "description": "Total security budget in the organization currency (INR).",
                }
            },
            "required": ["budget"],
        },
        _optimize_budget,
    ),
    (
        "explain_control",
        "Explain one control: its measured effectiveness, the FAIR factor it moves, the "
        "scenarios it protects, its cost, and what upgrading it would involve. Use for 'why is "
        "MFA recommended', 'what does this control do'.",
        {
            "type": "object",
            "properties": {
                "control_id": {
                    "type": "string",
                    "description": "Control id, e.g. CTL-MFA-PRIV.",
                }
            },
            "required": ["control_id"],
        },
        _explain_control,
    ),
    (
        "simulate_delay",
        "Model the financial cost of delaying remediation of a scenario by a number of days. "
        "Use for 'what happens if we delay patching for 30 days', 'cost of waiting'.",
        {
            "type": "object",
            "properties": {
                "scenario_id": {"type": "string", "description": "Scenario id, e.g. SCN-CRED-01."},
                "days": {"type": "integer", "description": "Delay in days.", "default": 30},
                "controls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional investment candidate ids to apply regardless.",
                },
            },
            "required": ["scenario_id"],
        },
        _simulate_delay,
    ),
    (
        "get_framework_mapping",
        "Framework and regulatory alignment: coverage against NIST CSF 2.0, CIS v8.1, "
        "ISO 27001, RBI and SEBI CSCRF, with the worst gaps priced in rupees. Use for "
        "compliance, audit and regulatory questions.",
        {
            "type": "object",
            "properties": {
                "framework_id": {
                    "type": "string",
                    "description": "Optional: nist_csf, cis_v8, iso_27001, rbi_2023, sebi_cscrf.",
                }
            },
            "required": [],
        },
        _get_framework_mapping,
    ),
)


def build_tools(engine: ScenarioEngine) -> list[Tool]:
    return [
        Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=lambda _engine=engine, _fn=handler, **kwargs: _fn(_engine, **kwargs),
        )
        for name, description, parameters, handler in TOOL_SPECS
    ]


def tool_schemas(tools: list[Tool]) -> list[dict[str, Any]]:
    return [tool.schema() for tool in tools]


__all__ = ["DEFAULT_BUDGET", "TOOL_SPECS", "Tool", "build_tools", "tool_schemas"]
