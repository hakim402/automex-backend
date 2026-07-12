"""
apps/core/utils/language.py
───────────────────────────────
Resolves which language a public content API request should be served in.

Priority (per product decision):
    1. ?lang=<code> query param, if present and valid
    2. Accept-Language header, best match against settings.LANGUAGES
    3. settings.PARLER_DEFAULT_LANGUAGE_CODE
"""
from __future__ import annotations

from django.conf import settings


def _valid_codes() -> set[str]:
    return {code for code, _label in settings.LANGUAGES}


def resolve_language(request) -> str:
    valid_codes = _valid_codes()

    query_lang = request.query_params.get("lang") if hasattr(request, "query_params") else request.GET.get("lang")
    if query_lang:
        query_lang = query_lang.strip().lower()
        if query_lang in valid_codes:
            return query_lang

    accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    for part in accept_language.split(","):
        code = part.split(";")[0].strip().lower()
        # Accept-Language may send region-qualified codes like "fr-FR" or "zh-CN"
        primary = code.split("-")[0]
        if code in valid_codes:
            return code
        if primary in valid_codes:
            return primary
        # Our own codes can carry a script/region subtag we don't expect
        # from a browser header (e.g. "zh-hans" vs. browser's "zh-CN") —
        # fall back to any configured code sharing the same primary subtag.
        prefixed_match = next((c for c in valid_codes if c.startswith(f"{primary}-")), None)
        if prefixed_match:
            return prefixed_match

    return getattr(settings, "PARLER_DEFAULT_LANGUAGE_CODE", "en")
