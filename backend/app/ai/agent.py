"""The tool-calling agent loop, and a grounding check on the model's prose.

The loop is deliberately small and bounded: the model may call tools, we execute them against
the deterministic engine, feed the results back, and repeat up to ``max_steps``.

The **grounding check** is the honesty mechanism. A language model can write a confident
sentence containing a number that no tool ever produced. We do not take that on trust: we
extract every figure from the final prose and verify it against the values the tools actually
returned. Anything unverifiable is reported to the caller rather than silently believed.

This is advisory, not a hard block — currency formatting and unit choices ("1.83 Cr" vs
"18,310,638") make exact comparison impossible. The report is a heuristic that flags possible
fabrications for a human to inspect.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.providers import Provider, ProviderError, ProviderRouter
from app.ai.tools import Tool

SYSTEM_PROMPT = """You are the explanation layer of a cyber-risk decision engine.

ABSOLUTE RULE: you never compute or invent a number. Every figure you state must come
verbatim from a tool result. If a tool did not return a value, say you do not know — do not
estimate, extrapolate or recall one from training.

You have tools that query the platform's deterministic risk engine (FAIR-style loss models,
Monte Carlo simulation and a CP-SAT budget optimizer, all built from real NVD/CVSS, EPSS and
CISA KEV intelligence). Always call a tool before answering a quantitative question.

How to work:
1. Call the tool(s) that answer the question. Prefer one focused tool call over many.
2. Answer in 2-4 sentences of plain business language, leading with the rupee figure.
3. Cite the concrete evidence you used (scenario or asset names, CVSS/EPSS, control ids).
4. State the modelled nature of the numbers when it matters: these are distributions with a
   stated confidence, not accounting facts.

Style: direct and executive. No preamble, no restating the question, no bullet-point dumps
unless asked to compare options. Use Indian numbering conventions (lakh/crore) when writing
rupee amounts, and keep tool precision (do not round 1.83 Cr to "about 2 Cr")."""


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "ok": self.ok,
            "result": self.result,
        }


@dataclass
class Answer:
    question: str
    answer: str
    provider: str
    model: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    grounded: bool = True
    unverified_numbers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "provider": self.provider,
            "model": self.model,
            "steps": self.steps,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "grounding": {
                "grounded": self.grounded,
                "unverified_numbers": self.unverified_numbers,
                "note": (
                    "Heuristic check: figures in the answer are matched against the numbers "
                    "returned by the tools. Anything listed above could not be verified and "
                    "should be treated with suspicion."
                ),
            },
        }


# --- grounding ---------------------------------------------------------------------------
_NUMBER_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?![\w])")

_UNIT_SCALES: tuple[float, ...] = (
    1.0,
    1e2,  # percent
    1e3,  # thousand
    1e5,  # lakh
    1e7,  # crore
    1e9,
)


def _collect_numbers(value: Any, out: list[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        out.append(float(value))
    elif isinstance(value, dict):
        for item in value.values():
            _collect_numbers(item, out)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_numbers(item, out)


def tool_numbers(tool_calls: list[ToolCall]) -> list[float]:
    values: list[float] = []
    for call in tool_calls:
        _collect_numbers(call.result, values)
    return values


def _is_grounded(candidate: float, values: list[float], tolerance: float = 0.02) -> bool:
    """True if a stated figure matches a tool value, allowing rounding and unit scaling."""
    for value in values:
        for scale in _UNIT_SCALES:
            scaled = value / scale
            if scaled == 0:
                continue
            if abs(candidate - scaled) <= tolerance * abs(scaled):
                return True
        if value != 0 and abs(candidate - value) <= tolerance * abs(value):
            return True
    return False


def check_grounding(answer: str, tool_calls: list[ToolCall]) -> tuple[bool, list[str]]:
    """Flag figures in the prose that no tool returned. Small integers are ignored."""
    values = tool_numbers(tool_calls)
    unverified: list[str] = []

    for match in _NUMBER_RE.finditer(answer):
        raw = match.group(1)
        try:
            candidate = float(raw.replace(",", ""))
        except ValueError:  # pragma: no cover - regex guarantees numeric
            continue
        if candidate < 10:  # counts, ranks, "3 steps"
            continue
        if not _is_grounded(candidate, values):
            unverified.append(raw)

    return (not unverified), unverified


# --- agent loop --------------------------------------------------------------------------
class RiskAgent:
    """Drives a bounded tool-calling conversation against the engine."""

    def __init__(
        self,
        router: ProviderRouter,
        tools: list[Tool],
        *,
        max_steps: int = 4,
        require_tool_use: bool = True,
    ) -> None:
        self.router = router
        self.tools = {tool.name: tool for tool in tools}
        self.tool_schemas = [tool.schema() for tool in tools]
        self.max_steps = max_steps
        #: When true, a first-step answer that cites no tool is rejected rather than shown.
        self.require_tool_use = require_tool_use

    def _execute(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        tool = self.tools.get(name)
        if tool is None:
            return ToolCall(
                name=name, arguments=arguments, result={"error": f"unknown tool: {name}"}, ok=False
            )
        try:
            result = tool.handler(**arguments)
        except TypeError as exc:
            return ToolCall(
                name=name,
                arguments=arguments,
                result={"error": f"bad arguments: {exc}"},
                ok=False,
            )
        except Exception as exc:  # noqa: BLE001 - a tool failure must not kill the answer
            return ToolCall(
                name=name,
                arguments=arguments,
                result={"error": f"{type(exc).__name__}: {exc}"},
                ok=False,
            )
        return ToolCall(name=name, arguments=arguments, result=result)

    def ask(self, question: str) -> Answer:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        collected: list[ToolCall] = []
        provider: Provider | None = None

        for step in range(1, self.max_steps + 1):
            message, provider = self.router.chat(messages, tools=self.tool_schemas)
            requested = message.get("tool_calls") or []

            if not requested:
                content = (message.get("content") or "").strip()

                # A model that answers a quantitative question without consulting the engine
                # has produced something we cannot stand behind — and some local models do not
                # support tool calling at all. Observed with `mistral:7b`, which replies
                # "let me call the tool named get_risk_posture" as *prose*: no structured call,
                # no numbers, so the grounding check passes and a confident non-answer would be
                # shown to the user while claiming an action it never took.
                #
                # Better to fail here and let the deterministic path answer.
                if self.require_tool_use and not collected:
                    raise ProviderError(
                        f"model '{provider.model}' returned prose without calling a tool — it "
                        f"may not support tool calling, in which case pick a different model"
                    )

                if not content:
                    raise ProviderError("model returned neither tool calls nor content")
                grounded, unverified = check_grounding(content, collected)
                return Answer(
                    question=question,
                    answer=content,
                    provider=provider.id,
                    model=provider.model,
                    tool_calls=collected,
                    steps=step,
                    grounded=grounded,
                    unverified_numbers=unverified,
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": requested,
                }
            )

            for call in requested:
                function = call.get("function", {})
                name = function.get("name", "")
                raw_args = function.get("arguments") or "{}"
                try:
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    arguments = {}
                executed = self._execute(name, arguments if isinstance(arguments, dict) else {})
                collected.append(executed)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", name),
                        "name": name,
                        "content": json.dumps(executed.result, default=str),
                    }
                )

        # Step budget exhausted: return the tool evidence without prose rather than loop on.
        raise ProviderError(f"model did not produce a final answer within {self.max_steps} steps")


__all__ = [
    "SYSTEM_PROMPT",
    "Answer",
    "RiskAgent",
    "ToolCall",
    "check_grounding",
    "tool_numbers",
]
