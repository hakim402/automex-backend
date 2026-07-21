"""
apps/assistant/prompts.py
────────────────────────────
Builds the system prompt each conversation turn is sent with — grounded in
real published Services and curated AIKnowledgeEntry rows (lightweight
RAG: no vector search, just "here's everything true about us right now",
which is plenty at this content scale).

The model is instructed to always answer in JSON (required for Groq's
json_object response_format, which also requires the literal word "JSON"
to appear in the prompt) matching a fixed schema — see parse_ai_reply()
in services.py for how that gets consumed.

Prompt components are cached for 5 minutes to avoid hitting the DB on
every single chat turn.
"""
from __future__ import annotations

from django.core.cache import cache

from apps.assistant.models import AIKnowledgeEntry
from apps.content.models import Service

_PROMPT_CACHE_TTL = 300  # 5 minutes

_SYSTEM_PROMPT_TEMPLATE = """You are the AI Sales Assistant for AUTOMEX, a technology consulting and \
software development company. You help visitors on the AUTOMEX website understand our services and \
gently move genuinely interested visitors toward providing contact info or booking a consultation — \
never pushy, never repeat the same ask twice in a row.

Respond in {language} unless the visitor clearly writes in a different language, in which case follow them.

AUTOMEX services currently offered:
{services_block}

Additional knowledge you can draw on:
{knowledge_block}

You MUST respond with valid JSON only, matching exactly this schema (no prose outside the JSON):
{{
  "reply": "<your conversational reply to the visitor, plain text>",
  "lead_info": {{
    "full_name": "<name if the visitor stated one this turn, else null>",
    "company": "<company if stated this turn, else null>",
    "service_interest": "<which AUTOMEX service they seem interested in, else null>",
    "intent_score": <integer 0-100, how ready this visitor seems to talk to sales>
  }}
}}
"""


def _services_block(language_code: str) -> str:
    cache_key = f"assistant_services_block_{language_code}"
    block = cache.get(cache_key)
    if block is not None:
        return block

    services = Service.objects.published().language(language_code)[:20]
    if not services:
        block = "(no services currently published)"
    else:
        lines = []
        for service in services:
            name = service.safe_translation_getter("name", any_language=True) or ""
            short_description = service.safe_translation_getter("short_description", any_language=True) or ""
            lines.append(f"- {name}: {short_description}")
        block = "\n".join(lines)

    cache.set(cache_key, block, _PROMPT_CACHE_TTL)
    return block


def _knowledge_block() -> str:
    cache_key = "assistant_knowledge_block"
    block = cache.get(cache_key)
    if block is not None:
        return block

    entries = AIKnowledgeEntry.objects.filter(is_active=True)[:30]
    if not entries:
        block = "(no additional curated knowledge yet)"
    else:
        block = "\n".join(f"- Q: {e.question}\n  A: {e.answer}" for e in entries)

    cache.set(cache_key, block, _PROMPT_CACHE_TTL)
    return block


def build_system_prompt(*, language_code: str = "en") -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(
        language=language_code,
        services_block=_services_block(language_code),
        knowledge_block=_knowledge_block(),
    )
