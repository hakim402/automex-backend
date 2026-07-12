"""
apps/assistant/extraction.py
─────────────────────────────────
Deterministic (regex) signal extraction from a visitor's raw message —
the reliable trigger for lead capture, per design decision. The LLM's own
structured output (see prompts.py / services.py) enriches a lead once
triggered, but never gates the capture decision by itself — regex either
finds a real email/phone or it doesn't.
"""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Deliberately conservative: 7+ digits with optional separators/country code,
# to avoid false-positives on things like "we have 3 offices" or years.
_PHONE_RE = re.compile(r"(?:\+?\d[\d\-.\s]{6,}\d)")


def extract_email(text: str) -> str | None:
    match = _EMAIL_RE.search(text or "")
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    match = _PHONE_RE.search(text or "")
    if not match:
        return None
    digits_only = re.sub(r"\D", "", match.group(0))
    if len(digits_only) < 7:  # guard against short number-like substrings slipping through
        return None
    return match.group(0).strip()
