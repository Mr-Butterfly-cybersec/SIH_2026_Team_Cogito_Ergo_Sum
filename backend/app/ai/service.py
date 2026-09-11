"""The AI service: ask a question, get a grounded answer.

Order of operations:

1. If AI is enabled and a provider is configured, run the tool-calling agent.
2. If the agent fails for any reason (no credential, outage, rate limit, malformed output),
   fall back to the deterministic answer path.

Either way the answer is built from the same read-only tool layer, so the numbers are the
engine's, and the response carries the raw tool results so the UI can show the evidence
beneath the prose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai import fallback as deterministic
from app.ai.agent import Answer, RiskAgent
from app.ai.providers import ProviderError, ProviderRouter
from app.ai.tools import Tool, build_tools
from app.config import Settings, get_settings
from app.engine.service import ScenarioEngine, get_engine

MAX_QUESTION_CHARS = 500


@dataclass
class AskResult:
    answer: Answer
    degraded: bool = False
    reason: str | None = None
    available_providers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = self.answer.to_dict()
        payload["degraded"] = self.degraded
        payload["reason"] = self.reason
        payload["available_providers"] = self.available_providers
        return payload


class AiService:
    def __init__(
        self,
        engine: ScenarioEngine,
        settings: Settings,
        *,
        router: ProviderRouter | None = None,
        tools: list[Tool] | None = None,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.tools = tools if tools is not None else build_tools(engine)
        self.router = router if router is not None else ProviderRouter.from_settings(settings)

    def ask(self, question: str) -> AskResult:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValueError(f"question must be at most {MAX_QUESTION_CHARS} characters")

        # Probe rather than assume. A keyless provider is always "configured", so without a
        # reachability check this was truthy on a machine with no local runtime — every
        # question then paid for an agent attempt that could only fail, before falling back.
        available = [provider.id for provider in self.router.reachable_providers()]

        if self.settings.ai_enabled and available:
            agent = RiskAgent(self.router, self.tools, max_steps=self.settings.ai_max_steps)
            try:
                return AskResult(
                    answer=agent.ask(question),
                    degraded=False,
                    available_providers=available,
                )
            except ProviderError as exc:
                reason = f"language model unavailable ({exc})"
            except Exception as exc:  # noqa: BLE001 - never fail a question on provider bugs
                reason = f"language model error ({type(exc).__name__}: {exc})"
        elif not self.settings.ai_enabled:
            reason = "AI layer disabled by configuration"
        else:
            reason = "no language model provider configured"

        return AskResult(
            answer=deterministic.answer(question, self.tools, reason),
            degraded=True,
            reason=reason,
            available_providers=available,
        )

    def provider_status(self) -> dict[str, Any]:
        rows, active = self.router.status()
        return {
            "enabled": self.settings.ai_enabled,
            "providers": rows,
            "active": active,
            "fallback": "deterministic engine answers when no provider is available",
            "max_steps": self.settings.ai_max_steps,
        }


_SERVICE: AiService | None = None


def get_ai_service() -> AiService:
    """Process-wide AI service, sharing the engine singleton."""
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = AiService(get_engine(), get_settings())
    return _SERVICE


def reset_ai_service() -> None:
    global _SERVICE
    _SERVICE = None


__all__ = [
    "MAX_QUESTION_CHARS",
    "AiService",
    "AskResult",
    "get_ai_service",
    "reset_ai_service",
]
