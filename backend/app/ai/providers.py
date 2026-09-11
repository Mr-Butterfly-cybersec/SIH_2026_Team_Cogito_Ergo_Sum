"""LLM provider router: one OpenAI-compatible interface, four providers, with fallback.

All four providers we support expose an OpenAI-compatible ``/chat/completions`` endpoint, so
a single code path handles them and the only differences are the base URL, credential and
model name.

The chain is tried in order and the first provider that answers wins:

    Groq  →  Gemini  →  OpenRouter (:free)  →  Ollama (local)

Fallback is deliberate: the demo must survive a provider outage, a rate limit or a revoked
key. A provider with no credential configured is skipped rather than attempted. If none are
available the caller falls back to the deterministic, non-LLM answer path.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.ingestion.base import HttpClient

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class ProviderError(RuntimeError):
    """A provider was reachable but could not produce a usable completion."""


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    base_url: str
    model: str
    api_key: str | None = None
    requires_key: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def is_configured(self) -> bool:
        """Whether we have enough configuration to *attempt* this provider.

        Deliberately not the same as "reachable". A key is knowable offline; a local runtime
        is not — see :meth:`ProviderRouter.reachable`.
        """
        return bool(self.api_key) if self.requires_key else bool(self.base_url)

    def to_dict(self, *, reachable: bool | None = None) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "model": self.model,
            "configured": self.is_configured,
            "available": self.is_configured if reachable is None else reachable,
            "requires_key": self.requires_key,
        }


def resolve_providers(settings: Settings) -> list[Provider]:
    """The fallback chain, in priority order."""
    return [
        Provider(
            id="groq",
            label="Groq",
            base_url=GROQ_BASE_URL,
            model=settings.ai_groq_model,
            api_key=settings.groq_api_key,
        ),
        Provider(
            id="gemini",
            label="Google Gemini",
            base_url=GEMINI_BASE_URL,
            model=settings.ai_gemini_model,
            api_key=settings.gemini_api_key,
        ),
        Provider(
            id="openrouter",
            label="OpenRouter (free tier)",
            base_url=OPENROUTER_BASE_URL,
            model=settings.ai_openrouter_model,
            api_key=settings.openrouter_api_key,
        ),
        Provider(
            id="ollama",
            label="Ollama (local)",
            base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
            model=settings.ai_ollama_model,
            api_key=None,
            requires_key=False,
        ),
    ]


@dataclass(frozen=True)
class Reachability:
    """Whether a provider can actually serve a completion right now, and why not if it can't."""

    ok: bool
    detail: str

    def __bool__(self) -> bool:
        return self.ok


def _model_matches(configured: str, installed: str) -> bool:
    """Match a model name against an installed tag, tolerating an implicit ``:latest``."""
    if configured == installed:
        return True
    return installed.split(":", 1)[0] == configured.split(":", 1)[0] and (
        ":" not in configured or ":" not in installed
    )


class ProviderRouter:
    """Calls the first provider in the chain that returns a usable completion."""

    #: How long a reachability result is trusted. Long enough that a polling status endpoint
    #: does not hammer a local runtime, short enough that starting Ollama shows up promptly.
    PROBE_TTL_SECONDS = 10.0

    def __init__(
        self,
        providers: list[Provider],
        *,
        client_factory: Callable[..., HttpClient] = HttpClient,
        timeout: float = 30.0,
        probe_timeout: float = 1.5,
    ) -> None:
        self.providers = providers
        self._client_factory = client_factory
        self._timeout = timeout
        self._probe_timeout = probe_timeout
        self._probe_cache: dict[str, tuple[float, Reachability]] = {}
        self._last_detail: dict[str, str] = {}

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        client_factory: Callable[..., HttpClient] = HttpClient,
    ) -> ProviderRouter:
        return cls(
            resolve_providers(settings),
            client_factory=client_factory,
            timeout=settings.ai_timeout,
        )

    @property
    def configured(self) -> list[Provider]:
        """Providers we could attempt — no network involved."""
        return [provider for provider in self.providers if provider.is_configured]

    def probe(self, provider: Provider, *, force: bool = False) -> Reachability:
        """Whether a **keyless** provider can serve a completion right now.

        Reachability alone is not the question. A keyless provider is always "configured" —
        the base URL is a non-empty string — so configuration tells us nothing, and a running
        server tells us only half of it: if the configured model has not been pulled, every
        request fails with "model not found" while the status page cheerfully reports the
        provider as active. So the probe checks the ``/models`` listing for the configured
        model and reports the concrete reason when it is absent.

        Results are cached briefly because this performs a network call and the status
        endpoint is polled by the dashboard.
        """
        if provider.requires_key:
            return Reachability(provider.is_configured, "credential configured")

        now = time.monotonic()
        cached = self._probe_cache.get(provider.id)
        if cached is not None and not force and now - cached[0] < self.PROBE_TTL_SECONDS:
            return cached[1]

        result = self._probe_keyless(provider)
        self._probe_cache[provider.id] = (now, result)
        return result

    def _probe_keyless(self, provider: Provider) -> Reachability:
        try:
            client = self._client_factory(
                base_url=provider.base_url, timeout=self._probe_timeout, max_retries=0
            )
            try:
                listing = client.get_json("/models")
            finally:
                client.close()
        except Exception as exc:  # noqa: BLE001 - unreachable is a normal outcome
            return Reachability(False, f"unreachable ({type(exc).__name__})")

        installed = [
            str(entry.get("id", ""))
            for entry in (listing or {}).get("data", [])
            if isinstance(entry, dict)
        ]
        if not installed:
            return Reachability(False, "reachable but reports no models")

        if any(_model_matches(provider.model, model) for model in installed):
            return Reachability(True, f"model {provider.model} available")

        return Reachability(
            False,
            f"model '{provider.model}' is not pulled — `ollama pull {provider.model}`",
        )

    def reachable(self, provider: Provider, *, force: bool = False) -> bool:
        return self.probe(provider, force=force).ok

    def reachable_providers(self, *, force: bool = False) -> list[Provider]:
        return [
            provider
            for provider in self.providers
            if provider.is_configured and self.probe(provider, force=force).ok
        ]

    def status(self, *, force: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
        """Provider rows and the ids that would actually answer, for the status endpoint."""
        rows: list[dict[str, Any]] = []
        active: list[str] = []
        for provider in self.providers:
            if not provider.is_configured:
                rows.append(provider.to_dict(reachable=False))
                continue
            probe = self.probe(provider, force=force)
            row = provider.to_dict(reachable=probe.ok)
            row["detail"] = probe.detail
            rows.append(row)
            if probe.ok:
                active.append(provider.id)
        return rows, active

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], Provider]:
        """Return ``(message, provider)`` for the first provider that answers.

        Raises :class:`ProviderError` if every provider fails, so the caller can degrade to
        the deterministic answer path.
        """
        errors: list[str] = []

        for provider in self.providers:
            # Skip only what is *unconfigured*: an attempt is itself the reachability test, so
            # pre-probing here would add a round trip for no benefit.
            if not provider.is_configured:
                continue

            payload: dict[str, Any] = {
                "model": provider.model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            headers = {"content-type": "application/json", **provider.extra_headers}
            if provider.api_key:
                headers["authorization"] = f"Bearer {provider.api_key}"

            try:
                client = self._client_factory(
                    base_url=provider.base_url, timeout=self._timeout, max_retries=1
                )
                try:
                    response = client.post_json("/chat/completions", payload, headers=headers)
                finally:
                    client.close()
            except Exception as exc:  # noqa: BLE001 - any provider failure falls through
                errors.append(f"{provider.id}: {type(exc).__name__}: {exc}")
                continue

            choices = response.get("choices") or []
            if not choices or "message" not in choices[0]:
                errors.append(f"{provider.id}: malformed completion")
                continue

            return choices[0]["message"], provider

        raise ProviderError(
            "no provider produced a completion"
            + (f" ({'; '.join(errors)})" if errors else " (none configured)")
        )


__all__ = [
    "GEMINI_BASE_URL",
    "GROQ_BASE_URL",
    "OPENROUTER_BASE_URL",
    "Provider",
    "ProviderError",
    "ProviderRouter",
    "resolve_providers",
]
