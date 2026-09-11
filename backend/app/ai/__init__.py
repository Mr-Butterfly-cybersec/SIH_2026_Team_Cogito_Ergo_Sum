"""AI layer: tool-calling over the deterministic engine.

The LLM never computes, estimates or recalls a number. It selects a tool, the engine runs,
and the model turns the result into language. A grounding check flags any figure in the prose
that the tools did not return.
"""

from app.ai.agent import SYSTEM_PROMPT, Answer, RiskAgent, ToolCall, check_grounding
from app.ai.providers import Provider, ProviderError, ProviderRouter, resolve_providers
from app.ai.service import AiService, AskResult, get_ai_service, reset_ai_service
from app.ai.tools import DEFAULT_BUDGET, TOOL_SPECS, Tool, build_tools, tool_schemas

__all__ = [
    "DEFAULT_BUDGET",
    "SYSTEM_PROMPT",
    "TOOL_SPECS",
    "AiService",
    "Answer",
    "AskResult",
    "Provider",
    "ProviderError",
    "ProviderRouter",
    "RiskAgent",
    "Tool",
    "ToolCall",
    "build_tools",
    "check_grounding",
    "get_ai_service",
    "reset_ai_service",
    "resolve_providers",
    "tool_schemas",
]
