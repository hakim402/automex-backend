"""
apps/core/permissions.py
───────────────────────────
DRF permission and authentication classes shared across apps.
"""
from __future__ import annotations

import logging

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.models import APIKey

logger = logging.getLogger(__name__)

API_KEY_HEADER = "HTTP_X_API_KEY"  # request.META key for the "X-API-Key" header


class OptionalJWTAuthentication(BaseAuthentication):
    """
    Attempts JWT authentication but never raises — if no valid token is
    present, the request proceeds as anonymous (request.user will be
    AnonymousUser).  Use on public endpoints that *optionally* accept a
    Bearer token so authenticated users get their records linked while
    anonymous visitors still work.
    """

    def authenticate(self, request):
        try:
            return JWTAuthentication().authenticate(request)
        except Exception:
            # Invalid / expired / malformed token → treat as anonymous
            return None


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
