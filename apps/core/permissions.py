"""
apps/core/permissions.py
───────────────────────────
DRF permission classes shared across apps.
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework.permissions import BasePermission

from apps.core.models import APIKey

API_KEY_HEADER = "HTTP_X_API_KEY"  # request.META key for the "X-API-Key" header


class HasValidAPIKey(BasePermission):
    """
    Grants access if the request carries a valid, active, non-expired
    `X-API-Key` header. Used on public content endpoints (apps.content)
    instead of JWT — these are read-only marketing pages with no concept
    of a logged-in user, just a known frontend consumer.
    """

    message = "A valid X-API-Key header is required."

    def has_permission(self, request, view) -> bool:
        raw_key = request.META.get(API_KEY_HEADER, "")
        if not raw_key:
            return False

        key_hash = APIKey.hash_raw_key(raw_key)
        try:
            api_key = APIKey.objects.get(key_hash=key_hash, is_active=True)
        except APIKey.DoesNotExist:
            return False

        if api_key.expires_at and api_key.expires_at <= timezone.now():
            return False

        # Best-effort usage tracking; avoid failing the request if this write fails.
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        request.api_key = api_key
        return True
