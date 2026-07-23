"""
apps/assistant/providers.py
────────────────────────────────
Thin, swappable LLM provider layer. Only Groq is implemented, but nothing
in apps.assistant.services talks to Groq directly — everything goes
through the AIProvider interface, so swapping providers later (or adding
a second one) doesn't touch business logic.

Groq's API is OpenAI-compatible (POST {base_url}/chat/completions), so
this also works unmodified against any other OpenAI-compatible endpoint
by changing GROQ_API_BASE_URL.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import requests
from django.conf import settings

logger = logging.getLogger("apps.assistant")


class AIProviderError(Exception):
    """Raised for any provider failure — missing config, timeout, HTTP error, bad response shape."""


@dataclass
class AIProviderResponse:
    content: str
    raw: dict = field(default_factory=dict)


class AIProvider:
    """Interface every provider implements."""

    def complete(self, messages: list[dict], *, json_mode: bool = False) -> AIProviderResponse:
        raise NotImplementedError


class GroqProvider(AIProvider):
    """
    OpenAI-compatible chat completion via Groq. `messages` follows the
    standard [{"role": "system"|"user"|"assistant", "content": str}, ...]
    shape.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.base_url = (base_url or settings.GROQ_API_BASE_URL).rstrip("/")
        self.model = model or settings.GROQ_MODEL
        self.timeout = timeout or settings.GROQ_REQUEST_TIMEOUT_SECONDS

    def complete(self, messages: list[dict], *, json_mode: bool = False) -> AIProviderResponse:
        if not self.api_key:
            raise AIProviderError("GROQ_API_KEY is not configured.")

        payload = {"model": self.model, "messages": messages, "temperature": 0.4}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as exc:
            raise AIProviderError("Groq request timed out.") from exc
        except requests.exceptions.RequestException as exc:
            raise AIProviderError(f"Groq request failed: {exc}") from exc

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Unexpected Groq response shape: {data}") from exc

        return AIProviderResponse(content=content, raw=data)


def get_default_provider() -> AIProvider:
    """
    Returns a GroqProvider configured from the ThirdPartyIntegration registry
    if an active AI integration exists, otherwise falls back to settings.
    """
    try:
        from apps.notifications.models import ThirdPartyIntegration

        integration = ThirdPartyIntegration.objects.filter(
            provider_type=ThirdPartyIntegration.ProviderType.AI,
            provider_name__icontains="groq",
            is_active=True,
        ).first()

        if integration is None:
            # Try any active AI integration
            integration = ThirdPartyIntegration.objects.filter(
                provider_type=ThirdPartyIntegration.ProviderType.AI,
                is_active=True,
            ).first()

        if integration:
            creds = integration.credentials or {}
            return GroqProvider(
                api_key=creds.get("api_key", ""),
                base_url=creds.get("base_url"),
                model=creds.get("model") or (integration.config or {}).get("model"),
                timeout=integration.config.get("timeout") if integration.config else None,
            )
    except Exception as exc:
        logger.warning("Failed to load AI provider from ThirdPartyIntegration, falling back to settings: %s", exc)
        # Fall through to settings-based config

    return GroqProvider()
