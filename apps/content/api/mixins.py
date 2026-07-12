"""
apps/content/api/mixins.py
──────────────────────────────
Shared behaviour for every public content viewset:
- API-key gated, not JWT (overrides the project-wide JWT default)
- resolves the request language (?lang= > Accept-Language > default),
  activates it for the duration of the request, and makes it available
  both as a queryset filter and in serializer context
- scoped rate limiting via the "public_content" throttle scope
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import translation
from rest_framework.throttling import ScopedRateThrottle

from apps.core.permissions import HasValidAPIKey
from apps.core.utils.language import resolve_language


class PublicContentViewSetMixin:
    """Mix into any ReadOnlyModelViewSet exposing published content publicly."""

    authentication_classes = []
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_content"

    language_code: str = "en"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.language_code = resolve_language(request)
        translation.activate(self.language_code)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["language_code"] = self.language_code
        return context


class TranslatedSlugLookupMixin:
    """
    Mix in AFTER PublicContentViewSetMixin on any viewset whose model's
    `slug` field lives inside django-parler's TranslatedFields (Service,
    CaseStudy, BlogPost, Industry) — `slug` isn't a real column on the base
    table, so DRF's default get_object() (which does queryset.get(slug=...))
    can't resolve it. This filters through the translations relation for
    the currently-resolved language instead, via parler's `.translated()`.
    """

    lookup_field = "slug"

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs[self.lookup_url_kwarg or self.lookup_field]
        obj = get_object_or_404(queryset.translated(self.language_code, slug=lookup_value))
        self.check_object_permissions(self.request, obj)
        return obj
