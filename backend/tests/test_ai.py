"""AI layer tests (offline — no network, no API keys)."""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.ai.agent import RiskAgent, ToolCall, check_grounding
from app.ai.fallback import FALLBACK_PROVIDER, answer, render, route
from app.ai.providers import Provider, ProviderError, ProviderRouter, resolve_providers
from app.ai.service import AiService
from app.ai.tools import build_tools
from app.config import Settings
from app.engine import ScenarioEngine, get_engine
from app.main import app
from app.optimization.context import load_planning_context


@pytest.fixture(scope="module")
def engine() -> ScenarioEngine:
    return ScenarioEngine(load_planning_context())


@pytest.fixture(scope="module")
def tools(engine: ScenarioEngine):
    return build_tools(engine)


@pytest.fixture(scope="module")
def offline_service(engine: ScenarioEngine) -> AiService:
    """No keys configured -> the deterministic path."""
    return AiService(engine, Settings(_env_file=None))


class StubRouter:
    """A router that replays scripted messages instead of calling a provider."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self._messages = list(messages)
        self.seen: list[list[dict[str, Any]]] = []
        self.available = [
            Provider(id="stub", label="Stub", base_url="", model="stub-1", requires_key=False)
        ]

    def chat(self, messages: list[dict[str, Any]], **_kwargs: Any):
        self.seen.append(messages)
        if not self._messages:
            raise ProviderError("stub exhausted")
        return self._messages.pop(0), self.available[0]

    def reachable_providers(self, **_kwargs: Any):
        return self.available


# --- tools ------------------------------------------------------------------------------
def test_all_tools_have_schemas(tools) -> None:
    assert len(tools) == 6
    for tool in tools:
        schema = tool.schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == tool.name
        assert schema["function"]["description"]


def test_tools_never_write(tools) -> None:
    """Every tool must be read-only: it must not mutate the engine."""
    before = {cid: c.effectiveness for cid, c in get_engine().context.controls.items()}
    for tool in tools:
        with contextlib.suppress(TypeError):
            tool.handler()
    after = {cid: c.effectiveness for cid, c in get_engine().context.controls.items()}
    assert before == after


def test_top_risks_are_ranked(engine: ScenarioEngine, tools) -> None:
    tool = next(t for t in tools if t.name == "get_top_risks")
    risks = tool.handler(limit=4)["risks"]
    eals = [r["expected_annual_loss"] for r in risks]
    assert eals == sorted(eals, reverse=True)


def test_tool_handles_unknown_input(tools) -> None:
    explain = next(t for t in tools if t.name == "explain_control")
    assert "error" in explain.handler(control_id="NOPE")
    delay = next(t for t in tools if t.name == "simulate_delay")
    assert "error" in delay.handler(scenario_id="NOPE")


# --- grounding --------------------------------------------------------------------------
def test_grounding_accepts_tool_numbers() -> None:
    calls = [ToolCall(name="t", arguments={}, result={"eal": 12_345_678.0})]
    grounded, unverified = check_grounding("Expected annual loss is ₹1.23 Cr.", calls)
    assert grounded
    assert unverified == []


def test_grounding_flags_fabricated_numbers() -> None:
    calls = [ToolCall(name="t", arguments={}, result={"eal": 1_000_000.0})]
    grounded, unverified = check_grounding("The loss is ₹9.99 Cr and 42,000 incidents.", calls)
    assert not grounded
    assert unverified


def test_grounding_ignores_small_counts() -> None:
    calls = [ToolCall(name="t", arguments={}, result={"eal": 1_000_000.0})]
    grounded, _ = check_grounding("We modelled 3 scenarios across 8 controls.", calls)
    assert grounded


# --- fallback routing -------------------------------------------------------------------
@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What is our highest financial cyber risk?", "get_top_risks"),
        ("What can we do with 25 lakh?", "optimize_budget"),
        ("Where should the security budget go?", "optimize_budget"),
        ("What happens if we delay patching for 30 days?", "simulate_delay"),
        ("Why is MFA recommended?", "explain_control"),
        ("Are we compliant with RBI?", "get_framework_mapping"),
        ("How do we score on NIST CSF?", "get_framework_mapping"),
    ],
)
def test_router_picks_the_right_tool(question: str, expected: str, tools) -> None:
    match = route(question, {tool.name: tool for tool in tools})
    assert match is not None
    assert match.tool == expected


def test_router_returns_none_for_off_topic(tools) -> None:
    assert route("How is the weather today?", {t.name: t for t in tools}) is None


def test_budget_is_parsed_from_lakhs(tools) -> None:
    match = route("What can we do with 25 lakh?", {t.name: t for t in tools})
    assert match is not None
    assert match.arguments["budget"] == 2_500_000


def test_delay_uses_the_largest_scenario_that_control_protects(tools) -> None:
    """'Delay patching' must ask about what patching fixes, not the biggest risk overall."""
    by_name = {t.name: t for t in tools}
    match = route("What happens if we delay patching for 30 days?", by_name)
    assert match is not None
    protected = {
        entry["scenario_id"]
        for entry in by_name["explain_control"].handler(control_id="CTL-PATCH")["protects"]
    }
    assert match.arguments["scenario_id"] in protected


def test_offline_answer_is_grounded(tools) -> None:
    result = answer("What is our highest risk?", tools, "test")
    assert result.provider == FALLBACK_PROVIDER
    assert result.grounded
    assert result.tool_calls
    assert "₹" in result.answer


def test_offline_answer_handles_off_topic(tools) -> None:
    result = answer("What is the weather?", tools, "test")
    assert result.grounded
    assert result.tool_calls == []


def test_render_handles_tool_errors() -> None:
    assert "could not answer" in render("get_top_risks", {"error": "boom"})


# --- agent loop -------------------------------------------------------------------------
def test_agent_calls_a_tool_then_answers(engine: ScenarioEngine, tools) -> None:
    tool_result = next(t for t in tools if t.name == "get_posture").handler()
    router = StubRouter(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "function": {"name": "get_posture", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "assistant",
                "content": f"Expected annual loss is ₹{tool_result['expected_annual_loss']:,}.",
            },
        ]
    )
    agent = RiskAgent(router, tools, max_steps=4)
    result = agent.ask("What is our posture?")

    assert result.provider == "stub"
    assert result.steps == 2
    assert [c.name for c in result.tool_calls] == ["get_posture"]
    assert result.grounded


def test_agent_passes_tool_results_back_to_the_model(tools) -> None:
    router = StubRouter(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "c1", "function": {"name": "get_posture", "arguments": "{}"}}
                ],
            },
            {"role": "assistant", "content": "Done."},
        ]
    )
    RiskAgent(router, tools, max_steps=4).ask("posture?")
    second_call_messages = router.seen[1]
    assert any(message["role"] == "tool" for message in second_call_messages)


def test_agent_survives_a_bad_tool_name(tools) -> None:
    router = StubRouter(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c1", "function": {"name": "nope", "arguments": "{}"}}],
            },
            {"role": "assistant", "content": "I could not do that."},
        ]
    )
    result = RiskAgent(router, tools, max_steps=4).ask("?")
    assert result.tool_calls[0].ok is False


def test_agent_raises_when_step_budget_is_exhausted(tools) -> None:
    looping = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "c", "function": {"name": "get_posture", "arguments": "{}"}}],
    }
    router = StubRouter([looping] * 10)
    with pytest.raises(ProviderError, match="did not produce a final answer"):
        RiskAgent(router, tools, max_steps=2).ask("?")


# --- service ----------------------------------------------------------------------------
def test_service_falls_back_without_keys(offline_service: AiService) -> None:
    result = offline_service.ask("What is our highest risk?")
    assert result.degraded
    assert result.reason
    assert result.answer.provider == FALLBACK_PROVIDER


def test_service_uses_a_provider_when_available(engine: ScenarioEngine, tools) -> None:
    """A usable provider must produce a grounded answer, not the deterministic fallback.

    The scripted model calls a tool first, because that is what a tool-capable model does —
    and what the agent now requires before it will accept prose.
    """
    router = StubRouter(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_posture", "arguments": "{}"},
                    }
                ],
            },
            {"role": "assistant", "content": "Overall posture retrieved from the engine."},
        ]
    )
    service = AiService(engine, Settings(_env_file=None), router=router, tools=tools)
    result = service.ask("anything")
    assert not result.degraded
    assert result.answer.provider == "stub"
    assert result.answer.tool_calls, "the answer should be grounded in a tool result"


def test_service_rejects_prose_that_called_no_tool(engine: ScenarioEngine, tools) -> None:
    """A model that cannot call tools must not have its prose presented as an answer.

    Observed with `mistral:7b`: it replies "let me call the tool named get_risk_posture" as
    *prose*. No structured call, no numbers — so the grounding check passes and a confident
    non-answer would be shown while claiming an action it never took. Falling back to the
    deterministic path gives the user a real, engine-backed answer instead.
    """
    router = StubRouter(
        [{"role": "assistant", "content": "I will now call the tool to find your risk."}]
    )
    service = AiService(engine, Settings(_env_file=None), router=router, tools=tools)
    result = service.ask("What is our highest risk?")

    assert result.degraded
    assert "tool calling" in (result.reason or "")
    assert result.answer.tool_calls, "the fallback answers from the engine, so it cites tools"


def test_service_falls_back_when_the_provider_errors(engine: ScenarioEngine, tools) -> None:
    class Broken:
        def chat(self, *_a: Any, **_k: Any):
            raise ProviderError("boom")

        @property
        def providers(self):
            return []

        def reachable_providers(self, **_k: Any):
            return [Provider(id="x", label="X", base_url="", model="m", api_key="k")]

    service = AiService(engine, Settings(_env_file=None), router=Broken(), tools=tools)
    result = service.ask("What is our highest risk?")
    assert result.degraded
    assert "language model unavailable" in (result.reason or "")


def test_empty_and_overlong_questions_are_rejected(offline_service: AiService) -> None:
    with pytest.raises(ValueError):
        offline_service.ask("   ")
    with pytest.raises(ValueError, match="at most"):
        offline_service.ask("x" * 501)


# --- provider router --------------------------------------------------------------------
def test_provider_chain_order() -> None:
    providers = resolve_providers(Settings(_env_file=None))
    assert [p.id for p in providers] == ["groq", "gemini", "openrouter", "ollama"]
    # Ollama needs no key, so it is *configured* by default; the rest are not.
    assert providers[-1].is_configured
    assert not providers[0].is_configured


def test_keyless_provider_is_configured_but_not_assumed_reachable() -> None:
    """Regression: a keyless provider is always configured, so availability must be probed.

    Ollama has no credential, so `is_configured` is necessarily true — the base URL is a
    non-empty string. Treating that as "available" made the status endpoint claim Ollama was
    the active provider regardless of whether anything was listening.
    """
    router = ProviderRouter(resolve_providers(Settings(_env_file=None)))
    assert [p.id for p in router.configured] == ["ollama"]

    # This machine's reachability is not the point; that the check happens at all is. Assert
    # the probe returns a *reason*, which is what makes the status page actionable.
    probe = router.probe(router.providers[-1])
    assert isinstance(probe.ok, bool)
    assert probe.detail, "the probe must explain itself, not just return a flag"


def test_probe_reports_a_missing_model_as_the_reason() -> None:
    """A running server with an unpulled model is the common failure, and must say so.

    Observed in practice: Ollama was up with llava/mistral/deepseek installed, the configured
    model was llama3.2, and every request failed with "model not found" while the status page
    reported the provider as active.
    """

    class ModelListClient:
        def __init__(self, **_kwargs):
            pass

        def get_json(self, _path):
            return {"data": [{"id": "mistral:7b"}, {"id": "llava:7b"}]}

        def close(self):
            pass

    router = ProviderRouter(
        resolve_providers(Settings(_env_file=None)), client_factory=ModelListClient
    )
    probe = router.probe(router.providers[-1])

    assert probe.ok is False
    assert "llama3.2" in probe.detail
    assert "ollama pull" in probe.detail, "the message should say how to fix it"


def test_probe_accepts_an_installed_model() -> None:
    class ModelListClient:
        def __init__(self, **_kwargs):
            pass

        def get_json(self, _path):
            return {"data": [{"id": "llama3.2:latest"}]}

        def close(self):
            pass

    router = ProviderRouter(
        resolve_providers(Settings(_env_file=None)), client_factory=ModelListClient
    )
    assert router.probe(router.providers[-1]).ok is True


def test_probe_treats_an_unreachable_host_as_not_ok() -> None:
    class DeadClient:
        def __init__(self, **_kwargs):
            raise ConnectionError("refused")

    router = ProviderRouter(resolve_providers(Settings(_env_file=None)), client_factory=DeadClient)
    probe = router.probe(router.providers[-1])
    assert probe.ok is False
    assert "unreachable" in probe.detail


def test_probe_result_is_cached() -> None:
    """The status endpoint is polled, so the probe must not run on every request."""
    calls = {"n": 0}

    class CountingClient:
        def __init__(self, **_kwargs):
            pass

        def get_json(self, _path):
            calls["n"] += 1
            return {"data": [{"id": "llama3.2:latest"}]}

        def close(self):
            pass

    router = ProviderRouter(
        resolve_providers(Settings(_env_file=None)), client_factory=CountingClient
    )
    ollama = router.providers[-1]

    assert router.reachable(ollama) is True
    assert router.reachable(ollama) is True
    assert calls["n"] == 1, "the probe should be cached within its TTL"
    assert router.reachable(ollama, force=True) is True
    assert calls["n"] == 2


def test_status_separates_configured_from_available() -> None:
    """`configured` is knowable offline; `available` requires the provider to answer."""
    router = ProviderRouter(resolve_providers(Settings(_env_file=None)))
    rows, active = router.status()

    ollama_row = next(row for row in rows if row["id"] == "ollama")
    assert ollama_row["configured"] is True
    assert ollama_row["available"] is False, "not running here, so it must not be active"
    assert active == []


def test_router_attempts_keyless_provider_even_when_probe_would_fail() -> None:
    """`chat` must not gate on the probe — the attempt *is* the reachability test.

    A probe result can be stale, and a provider can come up between the probe and the call.
    Skipping on probe state would turn a recoverable situation into a guaranteed fallback.
    """
    seen: list[str] = []

    class RecordingClient:
        def __init__(self, **kwargs):
            seen.append(kwargs.get("base_url", ""))

        def post_json(self, _path, _payload, headers=None):
            raise ProviderError("boom")

        def close(self):
            pass

    router = ProviderRouter(
        resolve_providers(Settings(_env_file=None)), client_factory=RecordingClient
    )
    with pytest.raises(ProviderError):
        router.chat([{"role": "user", "content": "hi"}])
    assert seen, "the keyless provider should have been attempted"


def test_router_raises_when_nothing_is_configured() -> None:
    router = ProviderRouter([])
    with pytest.raises(ProviderError, match="no provider"):
        router.chat([{"role": "user", "content": "hi"}])


# --- API --------------------------------------------------------------------------------
def test_ask_endpoint_answers_without_a_key() -> None:
    client = TestClient(app)
    body = client.post("/api/v1/ask", json={"question": "What is our highest risk?"}).json()
    assert body["answer"]
    assert body["degraded"] is True
    assert body["tool_calls"]
    assert body["grounding"]["grounded"] is True


def test_ask_endpoint_rejects_empty_question() -> None:
    assert TestClient(app).post("/api/v1/ask", json={"question": ""}).status_code == 422


def test_ai_tools_endpoint_lists_six_tools() -> None:
    tools = TestClient(app).get("/api/v1/ai/tools").json()
    assert {t["name"] for t in tools} == {
        "get_posture",
        "get_top_risks",
        "optimize_budget",
        "explain_control",
        "simulate_delay",
        "get_framework_mapping",
    }


def test_ai_status_endpoint() -> None:
    body = TestClient(app).get("/api/v1/ai/status").json()
    assert body["enabled"] is True
    assert len(body["providers"]) == 4
    assert "deterministic" in body["fallback"]
