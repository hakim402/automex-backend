"""
apps/assistant/services.py
────────────────────────────────
Orchestrates one chat turn: persist the user message, call the LLM with
conversation history + grounding context, persist the reply, and — if the
deterministic extractor finds a real email/phone this turn — capture a
Lead (once per conversation) enriched with whatever the model extracted.

Never lets a provider failure break the conversation: any AIProviderError
degrades to a friendly fallback reply instead of a 500, and is logged.
"""
from __future__ import annotations

import json
import logging
import uuid

from django.conf import settings
from django.utils import timezone

from apps.content.models import Service
from apps.crm.services import capture_ai_assistant_lead

from . import extraction
from .models import AIConversation, AIMessage
from .prompts import build_system_prompt
from .providers import AIProvider, AIProviderError, get_default_provider

logger = logging.getLogger("apps.assistant")

FALLBACK_REPLY = (
    "Sorry, I'm having trouble connecting right now. "
    "Please try again in a moment, or reach us directly via the contact form."
)


def _get_or_create_conversation(*, request, session_id: str | None, language: str, page_url: str) -> AIConversation:
    if session_id:
        conversation = AIConversation.objects.filter(session_id=session_id, is_active=True).first()
        if conversation:
            return conversation

    return AIConversation.objects.create(
        session_id=session_id or uuid.uuid4().hex,
        language=language,
        page_url=page_url or "",
        ip_address=request.META.get("REMOTE_ADDR") or None,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
    )


def _build_message_history(conversation: AIConversation, *, language_code: str) -> list[dict]:
    system_prompt = build_system_prompt(language_code=language_code)
    recent = list(
        conversation.messages.exclude(role=AIMessage.Role.SYSTEM).order_by("-created_at")[
            : settings.AI_ASSISTANT_MAX_HISTORY_MESSAGES
        ]
    )
    recent.reverse()
    return [{"role": "system", "content": system_prompt}] + [
        {"role": m.role, "content": m.content} for m in recent
    ]


def _parse_ai_reply(raw_content: str) -> tuple[str, dict]:
    """
    Returns (reply_text, lead_info_dict). Falls back to treating the raw
    content as plain text if the model didn't return valid JSON — the
    conversation must never break just because the model ignored the
    format instruction on a given turn.
    """
    try:
        parsed = json.loads(raw_content)
        reply = parsed.get("reply") or raw_content
        lead_info = parsed.get("lead_info") or {}
        if not isinstance(lead_info, dict):
            lead_info = {}
        return reply, lead_info
    except (json.JSONDecodeError, AttributeError):
        return raw_content, {}


def _resolve_service_interest(name: str | None, *, language_code: str) -> Service | None:
    if not name:
        return None
    return (
        Service.objects.published()
        .language(language_code)
        .filter(translations__name__icontains=name.strip())
        .first()
    )


def handle_chat_message(
    *,
    request,
    session_id: str | None,
    message: str,
    language: str = "en",
    page_url: str = "",
    provider: AIProvider | None = None,
) -> dict:
    provider = provider or get_default_provider()
    conversation = _get_or_create_conversation(
        request=request, session_id=session_id, language=language, page_url=page_url,
    )

    AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content=message)

    history = _build_message_history(conversation, language_code=conversation.language)

    try:
        provider_response = provider.complete(history, json_mode=True)
        reply_text, lead_info = _parse_ai_reply(provider_response.content)
    except AIProviderError:
        logger.exception("AI provider failed for conversation %s", conversation.id)
        reply_text, lead_info = FALLBACK_REPLY, {}

    AIMessage.objects.create(
        conversation=conversation,
        role=AIMessage.Role.ASSISTANT,
        content=reply_text,
        metadata={"lead_info": lead_info} if lead_info else {},
    )

    lead_captured_this_turn = False
    if not conversation.lead_captured:
        email = extraction.extract_email(message)
        if email:
            phone = extraction.extract_phone(message) or ""
            service_interest = _resolve_service_interest(
                lead_info.get("service_interest"), language_code=conversation.language,
            )
            lead = capture_ai_assistant_lead(
                request=request,
                email=email,
                full_name=lead_info.get("full_name") or "",
                phone=phone,
                company=lead_info.get("company") or "",
                message=message,
                service_interest=service_interest,
            )
            conversation.lead = lead
            conversation.lead_captured = True
            conversation.save(update_fields=["lead", "lead_captured", "updated_at"])
            lead_captured_this_turn = True

    return {
        "session_id": conversation.session_id,
        "reply": reply_text,
        "lead_captured": conversation.lead_captured,
        "lead_captured_this_turn": lead_captured_this_turn,
    }
