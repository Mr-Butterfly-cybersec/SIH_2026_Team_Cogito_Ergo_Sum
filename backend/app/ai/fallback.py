"""Deterministic answer path — the offline safety net.

When no LLM provider is configured or every provider fails, the platform must still be able
to answer the questions the demo asks. This module maps a question to a tool call by intent
and renders the tool result into prose **in code**.

That matters for more than availability: it is the same tool layer the model uses, so the
numbers are identical, and it demonstrates the architectural claim directly — the intelligence
lives in the engine, and language is just a view over it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.ai.agent import Answer, ToolCall
from app.ai.tools import DEFAULT_BUDGET, Tool

FALLBACK_PROVIDER = "deterministic"
FALLBACK_MODEL = "engine"

_CURRENCY = "₹"

#: Intent patterns, tried in order. First match wins.
_PATTERNS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    (
        r"\b(delay|defer|postpone|wait|patching? late|not patch)\b",
        "simulate_delay",
        {},
    ),
    (
        r"\b(budget|spend|invest|where.*(go|money)|what can we do with|"
        r"lakh|crore|optimis|optimiz|allocat|portfolio)\b",
        "optimize_budget",
        {},
    ),
    (
        r"\b(compliance|framework|nist|cis|iso|rbi|sebi|audit|regulat|cscrf)\b",
        "get_framework_mapping",
        {},
    ),
    (
        r"\b(control|mfa|siem|waf|edr|backup|segmentation|pam|cspm|patch management)\b",
        "explain_control",
        {},
    ),
    (
        r"\b(risk|exposure|loss|asset|biggest|largest|worst|contribut|top)\b",
        "get_top_risks",
        {},
    ),
)


def _extract_budget(question: str) -> float | None:
    """Pull a rupee figure out of a question like 'what can we do with 25 lakh'."""
    lowered = question.lower()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(crore|cr|lakh|lac|l\b|k\b)?", lowered)
    if not match:
        return None
    value = float(match.group(1))
    unit = (match.group(2) or "").strip()
    if unit in {"crore", "cr"}:
        return value * 1e7
    if unit in {"lakh", "lac", "l"}:
        return value * 1e5
    if unit == "k":
        return value * 1e3
    if value >= 1000:
        return value
    return None


def _extract_days(question: str) -> int | None:
    match = re.search(r"(\d+)\s*(day|days|week|weeks|month|months)", question.lower())
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    if unit.startswith("week"):
        return value * 7
    if unit.startswith("month"):
        return value * 30
    return value


def _inr(value: float) -> str:
    if abs(value) >= 1e7:
        return f"{_CURRENCY}{value / 1e7:.2f} Cr"
    if abs(value) >= 1e5:
        return f"{_CURRENCY}{value / 1e5:.1f} L"
    return f"{_CURRENCY}{value:,.0f}"


@dataclass(frozen=True)
class DeterministicMatch:
    tool: str
    arguments: dict[str, Any]


def route(question: str, tools: dict[str, Tool]) -> DeterministicMatch | None:
    """Map a question to a tool call by intent. ``None`` when nothing matches."""
    for pattern, tool_name, base_args in _PATTERNS:
        if tool_name not in tools or not re.search(pattern, question, re.IGNORECASE):
            continue

        arguments = dict(base_args)
        if tool_name == "optimize_budget":
            arguments["budget"] = _extract_budget(question) or DEFAULT_BUDGET
        elif tool_name == "simulate_delay":
            arguments["days"] = _extract_days(question) or 30
            control_id = _pick_control(question, tools)
            arguments["scenario_id"] = _pick_scenario(question, tools, control_id)
            arguments["controls"] = [f"INV-{control_id}"] if control_id else []
        elif tool_name == "explain_control":
            control_id = _pick_control(question, tools)
            if control_id is None:
                continue
            arguments["control_id"] = control_id
        elif tool_name == "get_framework_mapping":
            framework_id = _pick_framework(question)
            if framework_id:
                arguments["framework_id"] = framework_id
        return DeterministicMatch(tool=tool_name, arguments=arguments)
    return None


_FRAMEWORK_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("cscrf", "sebi_cscrf"),
    ("sebi", "sebi_cscrf"),
    ("rbi", "rbi_2023"),
    ("reserve bank", "rbi_2023"),
    ("nist", "nist_csf"),
    ("csf", "nist_csf"),
    ("cis", "cis_v8"),
    ("iso", "iso_27001"),
    ("27001", "iso_27001"),
)


def _pick_framework(question: str) -> str | None:
    lowered = question.lower()
    for keyword, framework_id in _FRAMEWORK_KEYWORDS:
        if keyword in lowered:
            return framework_id
    return None


def _pick_scenario(question: str, tools: dict[str, Tool], control_id: str | None = None) -> str:
    """Choose the scenario an unqualified question is really about.

    An explicit ``SCN-`` id wins. Otherwise, if the question named a control, use the
    largest exposure that control actually protects — so "delay patching" asks about the
    biggest thing patching would fix, not the biggest risk overall.
    """
    match = re.search(r"\bSCN-[A-Z0-9-]+\b", question, re.IGNORECASE)
    if match:
        return match.group(0).upper()

    ranked = (tools["get_top_risks"].handler(limit=50).get("risks")) or []
    if control_id:
        protected = {
            entry["scenario_id"]
            for entry in tools["explain_control"].handler(control_id=control_id).get("protects")
            or []
        }
        for risk in ranked:
            if risk["scenario_id"] in protected:
                return risk["scenario_id"]

    return ranked[0]["scenario_id"] if ranked else "SCN-CRED-01"


def _pick_control(question: str, tools: dict[str, Tool]) -> str | None:
    match = re.search(r"\bCTL-[A-Z0-9-]+\b", question, re.IGNORECASE)
    if match:
        return match.group(0).upper()

    lowered = question.lower()
    keyword_map = (
        ("mfa", "CTL-MFA-PRIV"),
        ("multi-factor", "CTL-MFA-PRIV"),
        ("siem", "CTL-SIEM"),
        ("waf", "CTL-WAF"),
        ("edr", "CTL-EDR"),
        ("backup", "CTL-BACKUP"),
        ("segment", "CTL-SEG"),
        ("pam", "CTL-PAM"),
        ("privileged access", "CTL-PAM"),
        ("cloud posture", "CTL-CSPM"),
        ("cspm", "CTL-CSPM"),
        ("email", "CTL-EMAIL"),
        ("patch", "CTL-PATCH"),
    )
    for keyword, control_id in keyword_map:
        if keyword in lowered:
            return control_id
    return None


def render(tool: str, result: dict[str, Any]) -> str:
    """Turn a tool result into prose, deterministically."""
    if "error" in result:
        return f"I could not answer that from the engine: {result['error']}"

    if tool == "get_posture":
        return (
            f"Expected annual cyber loss is {_inr(result['expected_annual_loss'])}, with a P90 of "
            f"{_inr(result['p90'])} and a P95 (VaR) of {_inr(result['p95'])}. That is modelled "
            f"across {result['scenarios_modelled']} risk scenarios and "
            f"{result['controls_in_place']} controls, from a seeded "
            f"{result['n_trials']:,}-trial simulation."
        )

    if tool == "get_top_risks":
        risks = result.get("risks") or []
        if not risks:
            return "No risk scenarios are currently modelled."
        top = risks[0]
        driver = top.get("max_cvss")
        parts = [
            f"The largest modelled exposure is {top['name']} on {top.get('asset') or 'an asset'}"
            f" at {_inr(top['expected_annual_loss'])} expected annual loss"
            f" ({_inr(top['p95'])} at P95).",
        ]
        if driver is not None:
            parts.append(f"It carries a maximum CVSS of {driver}.")
        weakest = top.get("weakest_controls") or []
        if weakest:
            parts.append(
                f"The weakest control over it is {weakest[0]['name']} at "
                f"{weakest[0]['effectiveness']:.0%} effectiveness."
            )
        if len(risks) > 1:
            others = ", ".join(
                f"{r['name']} ({_inr(r['expected_annual_loss'])})" for r in risks[1:4]
            )
            parts.append(f"It is followed by {others}.")
        return " ".join(parts)

    if tool == "optimize_budget":
        selected = result.get("recommended_selection") or []
        gain = result.get("optimizer_vs_cvss_first_points")
        optimizer_eal = next(
            (s["eal_after"] for s in result["strategies"] if s["strategy"] == "optimizer"), 0
        )
        text = (
            f"For a budget of {_inr(result['budget'])}, the optimizer funds "
            f"{len(selected)} controls ({', '.join(selected)}) and spends "
            f"{_inr(result['spend'])}, cutting expected annual loss to "
            f"{_inr(optimizer_eal)}."
        )
        if gain is not None:
            text += (
                f" That is {gain:.1f} percentage points more modelled risk removed than "
                f"patching by CVSS severity first, at the same budget."
            )
        return text + " " + result.get("method", "")

    if tool == "explain_control":
        upgrade = result.get("upgrade_candidate")
        protected = len(result.get("protects") or [])
        text = (
            f"{result['name']} is currently at {result['effectiveness']:.0%} effectiveness. "
            f"As a {result['category']} control it acts on {result['faire_factor']} "
            f"({result['faire_effect']}), protecting {protected} scenario(s)."
        )
        if upgrade:
            text += (
                f" Raising it to {upgrade['target_effectiveness']:.0%} costs "
                f"{_inr(upgrade['cost'])} over about {upgrade['implementation_days']} days."
            )
        return text

    if tool == "simulate_delay":
        if result["avoidable_loss"] > 0:
            return (
                f"Leaving {result['scenario_id']} unaddressed for {result['days']} days accrues "
                f"{_inr(result['loss_if_delayed'])} of modelled exposure, against "
                f"{_inr(result['loss_if_remediated_now'])} with the controls in place — an "
                f"avoidable {_inr(result['avoidable_loss'])}."
            )
        return (
            f"Leaving {result['scenario_id']} unaddressed for {result['days']} days accrues "
            f"{_inr(result['loss_if_delayed'])} of modelled exposure. No investment candidate "
            f"was applied to compare against, so there is no avoidable-loss figure for this run."
        )

    if tool == "get_framework_mapping":
        frameworks = result.get("frameworks") or []
        if not frameworks:
            return "No framework coverage is available."
        parts = [
            f"{f['framework']} coverage is {f['coverage']:.0%} "
            f"({f['covered']} covered, {f['partial']} partial, {f['gaps']} gaps, "
            f"{_inr(f['gap_exposure'])} of exposure in the gaps)."
            for f in frameworks[:2]
        ]
        return " ".join(parts) + " " + result.get("method", "")

    return f"The engine returned: {result}"


def answer(question: str, tools: list[Tool], reason: str) -> Answer:
    """Answer without an LLM. Returns an error-shaped answer when nothing matches."""
    by_name = {tool.name: tool for tool in tools}
    match = route(question, by_name)

    if match is None:
        return Answer(
            question=question,
            answer=(
                "I can answer questions about overall risk posture, the largest exposures, "
                "budget optimisation, individual controls, the cost of delaying remediation, "
                "and framework compliance. No language model is configured, so I could not "
                "interpret this question — try one of those."
            ),
            provider=FALLBACK_PROVIDER,
            model=FALLBACK_MODEL,
            tool_calls=[],
            steps=0,
            grounded=True,
            unverified_numbers=[],
        )

    call = ToolCall(
        name=match.tool,
        arguments=match.arguments,
        result=by_name[match.tool].handler(**match.arguments),
    )
    return Answer(
        question=question,
        answer=(
            f"{render(match.tool, call.result)}\n\n(Answering without a language model: {reason}.)"
        ),
        provider=FALLBACK_PROVIDER,
        model=FALLBACK_MODEL,
        tool_calls=[call],
        steps=1,
        grounded=True,
        unverified_numbers=[],
    )


__all__ = [
    "FALLBACK_MODEL",
    "FALLBACK_PROVIDER",
    "DeterministicMatch",
    "answer",
    "render",
    "route",
]
