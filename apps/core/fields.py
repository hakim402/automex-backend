"""
apps/core/fields.py
─────────────────────
EncryptedJSONField — transparent at-rest encryption for JSON-shaped secrets
(currently: NotificationProviderConfig.credentials, which holds real
third-party API keys/tokens for SendGrid/Twilio/Slack/WhatsApp once those
are wired up).

Stored as encrypted text (Fernet, symmetric — appropriate here since the
application itself needs to read the plaintext back to make outbound API
calls; this is encryption-at-rest against DB dumps/backups/read-replica
access, not a substitute for proper secrets-manager isolation for very
high-sensitivity deployments).

Key management: settings.FIELD_ENCRYPTION_KEY must be a valid Fernet key
(44-char urlsafe-base64 string). Generate one with:

    python manage.py generate_field_encryption_key

In production, ImproperlyConfigured is raised at startup if this key is
missing — storing secrets unencrypted is not an acceptable silent fallback.
In DEBUG, a fixed dev-only key is used instead (convenience, not security —
never reuse the dev key anywhere real).
"""
from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

_DEV_ONLY_FALLBACK_KEY = b"XxJ3z5G0S6qv8h1yE9rP4nQ7wA2iT0lU6mC8bF1kD3o="  # NEVER use outside DEBUG


def _get_fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
    if not key:
        if settings.DEBUG:
            return Fernet(_DEV_ONLY_FALLBACK_KEY)
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY is not set. Generate one with "
            "`python manage.py generate_field_encryption_key` and add it to your .env "
            "before storing any real credentials — this must not run with DEBUG=False and no key."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedJSONField(models.TextField):
    """Drop-in replacement for JSONField when the content is a secret."""

    description = "JSON data, encrypted at rest"

    def get_prep_value(self, value):
        if value is None:
            return value
        plaintext = json.dumps(value)
        return _get_fernet().encrypt(plaintext.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return {} if value == "" else None
        try:
            plaintext = _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Wrong/rotated key, or the row predates encryption being enabled.
            return {}
        return json.loads(plaintext)

    def to_python(self, value):
        if value is None or isinstance(value, dict):
            return value
        if value == "":
            return {}
        try:
            plaintext = _get_fernet().decrypt(value.encode()).decode()
            return json.loads(plaintext)
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def value_to_string(self, obj):
        return json.dumps(self.value_from_object(obj))
