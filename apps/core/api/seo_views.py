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

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import BlogPost, CaseStudy, Service
from apps.core.models import MediaAsset, SEOSettings
from apps.core.permissions import HasValidAPIKey


class SEOSettingsView(APIView):
    authentication_classes = []
    permission_classes = [HasValidAPIKey]

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


class SitemapURLsView(APIView):
    """Flat list of every published URL — same underlying data as /sitemap.xml, as JSON."""

    authentication_classes = []
    permission_classes = [HasValidAPIKey]

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
