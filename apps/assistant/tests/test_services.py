from __future__ import annotations

import pytest
from django.test import RequestFactory

from apps.assistant import services
from apps.assistant.models import AIConversation, AIMessage
from apps.content.tests.factories import create_service
from apps.crm.models import Lead

from .factories import FakeAIProvider, FakeMalformedProvider, create_conversation

pytestmark = pytest.mark.django_db

rf = RequestFactory()


def _request():
    return rf.post("/api/v1/assistant/chat/", HTTP_USER_AGENT="pytest-agent", REMOTE_ADDR="9.9.9.9")


# ──────────────────────────────────────────────────────────────────────────────
# Conversation lifecycle
# ──────────────────────────────────────────────────────────────────────────────

def test_first_message_creates_new_conversation_and_returns_session_id():
    provider = FakeAIProvider(reply="Hi! How can I help?")
    result = services.handle_chat_message(
        request=_request(), session_id=None, message="Hello", provider=provider,
    )

    assert result["reply"] == "Hi! How can I help?"
    assert result["session_id"]
    assert AIConversation.objects.filter(session_id=result["session_id"]).exists()


def test_second_message_reuses_existing_conversation():
    conversation = create_conversation(session_id="existing-session")
    provider = FakeAIProvider()

    result = services.handle_chat_message(
        request=_request(), session_id="existing-session", message="Follow-up question", provider=provider,
    )

    assert result["session_id"] == "existing-session"
    assert conversation.messages.count() == 2  # user + assistant


def test_conversation_stores_both_user_and_assistant_messages():
    provider = FakeAIProvider(reply="Sure thing.")
    result = services.handle_chat_message(
        request=_request(), session_id=None, message="What services do you offer?", provider=provider,
    )

    conversation = AIConversation.objects.get(session_id=result["session_id"])
    roles = list(conversation.messages.order_by("created_at").values_list("role", flat=True))
    assert roles == [AIMessage.Role.USER, AIMessage.Role.ASSISTANT]


# ──────────────────────────────────────────────────────────────────────────────
# Provider failure handling
# ──────────────────────────────────────────────────────────────────────────────

def test_provider_failure_returns_fallback_reply_not_an_exception():
    provider = FakeAIProvider(should_fail=True)
    result = services.handle_chat_message(
        request=_request(), session_id=None, message="Hello?", provider=provider,
    )

    assert result["reply"] == services.FALLBACK_REPLY
    assert result["lead_captured"] is False


def test_malformed_json_from_model_falls_back_to_raw_text_not_a_crash():
    provider = FakeMalformedProvider()
    result = services.handle_chat_message(
        request=_request(), session_id=None, message="Hello", provider=provider,
    )

    assert result["reply"] == "Sure, happy to help with that!"


# ──────────────────────────────────────────────────────────────────────────────
# Lead capture (regex-triggered, LLM-enriched)
# ──────────────────────────────────────────────────────────────────────────────

def test_lead_captured_when_email_present_in_message():
    provider = FakeAIProvider(lead_info={"full_name": "Jane Doe", "company": "Acme Corp", "intent_score": 85})
    result = services.handle_chat_message(
        request=_request(),
        session_id=None,
        message="I'm Jane, my email is jane@example.com, can we talk?",
        provider=provider,
    )

    assert result["lead_captured"] is True
    assert result["lead_captured_this_turn"] is True
    lead = Lead.objects.get(email="jane@example.com")
    assert lead.lead_type == Lead.LeadType.AI_ASSISTANT
    assert lead.full_name == "Jane Doe"
    assert lead.company == "Acme Corp"


def test_no_lead_captured_when_no_email_in_message():
    provider = FakeAIProvider(lead_info={"full_name": "Someone", "intent_score": 90})
    result = services.handle_chat_message(
        request=_request(), session_id=None, message="Just browsing, thanks.", provider=provider,
    )

    assert result["lead_captured"] is False
    assert Lead.objects.count() == 0


def test_lead_captured_only_once_per_conversation():
    provider = FakeAIProvider()
    first = services.handle_chat_message(
        request=_request(), session_id=None, message="Email me at repeat@example.com", provider=provider,
    )
    second = services.handle_chat_message(
        request=_request(),
        session_id=first["session_id"],
        message="Also reach me at repeat@example.com again",
        provider=provider,
    )

    assert first["lead_captured_this_turn"] is True
    assert second["lead_captured_this_turn"] is False
    assert Lead.objects.filter(email="repeat@example.com").count() == 1


def test_lead_resolves_service_interest_by_name_match():
    create_service(slug="ai-development", name="Artificial Intelligence")
    provider = FakeAIProvider(lead_info={"service_interest": "Artificial Intelligence"})

    services.handle_chat_message(
        request=_request(),
        session_id=None,
        message="Reach me at interested@example.com about AI",
        provider=provider,
    )

    lead = Lead.objects.get(email="interested@example.com")
    assert lead.service_interest is not None
    assert lead.service_interest.safe_translation_getter("name") == "Artificial Intelligence"


def test_lead_defaults_full_name_to_email_prefix_when_llm_gives_none():
    provider = FakeAIProvider(lead_info={})
    services.handle_chat_message(
        request=_request(), session_id=None, message="noreply@example.com is my email", provider=provider,
    )

    lead = Lead.objects.get(email="noreply@example.com")
    assert lead.full_name == "noreply"


def test_conversation_lead_fk_is_linked_after_capture():
    provider = FakeAIProvider()
    result = services.handle_chat_message(
        request=_request(), session_id=None, message="contact@example.com", provider=provider,
    )

    conversation = AIConversation.objects.get(session_id=result["session_id"])
    assert conversation.lead is not None
    assert conversation.lead.email == "contact@example.com"
