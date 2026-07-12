"""
apps/core/models/api_key.py
───────────────────────────────
Lightweight API key for the public content API (apps.content). This is NOT
user authentication — JWT (apps.accounts) stays the auth mechanism for
anything acting on behalf of a person. An APIKey identifies a *consuming
frontend* (e.g. the Next.js marketing site, a mobile app) so public
read-only endpoints aren't wide open to arbitrary scraping, while still
requiring no login.

The raw key is shown to the admin exactly once, at creation time (via the
`create_api_key` management command or the admin's read-only "key" display
immediately after creation) — only its SHA-256 hash is ever persisted,
mirroring the pattern already used by apps.accounts.AbstractToken.
"""
from __future__ import annotations

import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimeStampedModel, UUIDModel


class APIKey(UUIDModel, TimeStampedModel):
    name = models.CharField(
        _("name"), max_length=200,
        help_text=_("Which consumer this key belongs to, e.g. 'automex-frontend-web'."),
    )
    key_hash = models.CharField(_("key hash"), max_length=64, unique=True, db_index=True, editable=False)
    prefix = models.CharField(
        _("key prefix"), max_length=12, db_index=True, editable=False,
        help_text=_("First characters of the raw key, shown in the admin for identification. Not a secret."),
    )

    is_active     = models.BooleanField(_("active"), default=True, db_index=True)
    last_used_at  = models.DateTimeField(_("last used at"), null=True, blank=True)
    expires_at    = models.DateTimeField(_("expires at"), null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("created by"),
    )

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("API key")
        verbose_name_plural = _("API keys")
        indexes = [models.Index(fields=["is_active"], name="idx_apikey_active")]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}…)"

    # ── Key generation / verification ──────────────────────────────────────

    @staticmethod
    def hash_raw_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def generate(cls, name: str, created_by=None, expires_at=None) -> tuple["APIKey", str]:
        """
        Creates a new APIKey row and returns (instance, raw_key). The raw
        key is only ever available here — callers MUST surface it to the
        admin immediately, since it cannot be retrieved again afterward.
        """
        raw_key = secrets.token_urlsafe(32)
        instance = cls.objects.create(
            name=name,
            key_hash=cls.hash_raw_key(raw_key),
            prefix=raw_key[:8],
            created_by=created_by,
            expires_at=expires_at,
        )
        return instance, raw_key
