"""
apps/core/api/seo_views.py
──────────────────────────────
JSON alternatives to the server-rendered /sitemap.xml and site-wide SEO
defaults — for a Next.js frontend that prefers to generate its own
sitemap.xml (app/sitemap.ts) and <head> tags natively rather than
depending on Django's XML output. Same API-key gate as the content API.
"""
from __future__ import annotations

from itertools import chain

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import BlogPost, CaseStudy, Service
from apps.core.models import MediaAsset, SEOSettings
from apps.core.permissions import HasValidAPIKey

# Added drf-spectacular imports
from drf_spectacular.utils import extend_schema, inline_serializer


@method_decorator(cache_page(60 * 15), name="dispatch")
class SEOSettingsView(APIView):
    authentication_classes = []
    permission_classes = [HasValidAPIKey]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="SEOSettingsResponse",
                fields={
                    "site_name": serializers.CharField(),
                    "default_meta_title_suffix": serializers.CharField(),
                    "default_meta_description": serializers.CharField(),
                    "default_og_image": serializers.CharField(allow_null=True),
                    "organization": inline_serializer(
                        name="Organization",
                        fields={
                            "legal_name": serializers.CharField(),
                            "logo": serializers.CharField(allow_null=True),
                            "url": serializers.URLField(),
                            "social_profiles": serializers.JSONField(),
                            "contact_email": serializers.EmailField(),
                            "contact_phone": serializers.CharField(),
                        }
                    ),
                    "google_site_verification": serializers.CharField(),
                    "google_analytics_id": serializers.CharField(),
                    "google_tag_manager_id": serializers.CharField(),
                }
            )
        }
    )
    def get(self, request, *args, **kwargs):
        settings_obj = SEOSettings.get_solo()
        return Response({
            "site_name": settings_obj.site_name,
            "default_meta_title_suffix": settings_obj.default_meta_title_suffix,
            "default_meta_description": settings_obj.default_meta_description,
            "default_og_image": _media_url(request, settings_obj.default_og_image),
            "organization": {
                "legal_name": settings_obj.organization_legal_name,
                "logo": _media_url(request, settings_obj.organization_logo),
                "url": settings_obj.organization_url,
                "social_profiles": settings_obj.organization_social_profiles,
                "contact_email": settings_obj.contact_email,
                "contact_phone": settings_obj.contact_phone,
            },
            "google_site_verification": settings_obj.google_site_verification,
            "google_analytics_id": settings_obj.google_analytics_id,
            "google_tag_manager_id": settings_obj.google_tag_manager_id,
        })


@method_decorator(cache_page(60 * 60), name="dispatch")
class SitemapURLsView(APIView):
    """Flat list of every published URL — same underlying data as /sitemap.xml, as JSON."""

    authentication_classes = []
    permission_classes = [HasValidAPIKey]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="SitemapEntry",
                fields={
                    "path": serializers.CharField(),
                    "lastmod": serializers.CharField(),
                    "changefreq": serializers.CharField(),
                    "priority": serializers.FloatField(),
                },
                many=True
            )
        }
    )
    def get(self, request, *args, **kwargs):
        entries = list(chain(
            (_entry("services", s) for s in Service.objects.published().language("en")),
            (_entry("case-studies", c) for c in CaseStudy.objects.published().language("en")),
            (_entry("blog", b) for b in BlogPost.objects.published().language("en")),
        ))
        return Response(entries)


def _entry(path_prefix: str, obj) -> dict:
    slug = obj.safe_translation_getter("slug", language_code="en", any_language=True)
    return {
        "path": f"/{path_prefix}/{slug}/",
        "lastmod": obj.updated_at.isoformat(),
        "priority": float(obj.sitemap_priority),
        "changefreq": obj.sitemap_changefreq,
    }


def _media_url(request, media_asset: MediaAsset | None) -> str | None:
    if not media_asset or not media_asset.file:
        return None
    return request.build_absolute_uri(media_asset.file.url)