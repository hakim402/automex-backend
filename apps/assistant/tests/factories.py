"""
apps/assistant/tests/factories.py
──────────────────────────────────────
Includes a FakeAIProvider (implements the same AIProvider interface as
GroqProvider) so tests never touch the network or need a real GROQ_API_KEY —
standard practice for testing external API integrations.
"""
from __future__ import annotations

import json

from apps.assistant.models import AIConversation, AIKnowledgeEntry
from apps.assistant.providers import AIProvider, AIProviderError, AIProviderResponse


def create_conversation(**kwargs) -> AIConversation:
    defaults = dict(session_id="test-session-1", language="en")
    defaults.update(kwargs)
    return AIConversation.objects.create(**defaults)


def create_knowledge_entry(**kwargs) -> AIKnowledgeEntry:
    defaults = dict(
        question="Do you sign NDAs?",
        answer="Yes, we sign NDAs before any detailed discovery call.",
        category="general",
    )
    defaults.update(kwargs)
    return AIKnowledgeEntry.objects.create(**defaults)


class FakeAIProvider(AIProvider):
    """Returns a fixed, valid JSON reply — or raises, if configured to fail."""

    def __init__(self, reply: str = "Thanks for reaching out!", lead_info: dict | None = None, should_fail: bool = False):
        self.reply = reply
        self.lead_info = lead_info or {}
        self.should_fail = should_fail
        self.last_messages_sent: list[dict] | None = None

    def complete(self, messages, *, json_mode: bool = False) -> AIProviderResponse:
        self.last_messages_sent = messages
        if self.should_fail:
            raise AIProviderError("Simulated provider failure.")
        content = json.dumps({"reply": self.reply, "lead_info": self.lead_info})
        return AIProviderResponse(content=content, raw={"choices": [{"message": {"content": content}}]})


class FakeMalformedProvider(AIProvider):
    """Simulates the model ignoring the JSON-only instruction."""

    def complete(self, messages, *, json_mode: bool = False) -> AIProviderResponse:
        return AIProviderResponse(content="Sure, happy to help with that!", raw={})
