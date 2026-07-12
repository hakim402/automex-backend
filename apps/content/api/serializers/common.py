"""
apps/content/api/serializers/common.py
──────────────────────────────────────────
Shared building blocks used by every content serializer: a compact media
representation, and a reusable SEO payload builder so the frontend never
has to reimplement <head>-tag logic per content type.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.core.models import MediaAsset


class MediaAssetSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = ["id", "url", "alt_text", "caption", "width", "height", "file_type"]

    def get_url(self, obj: MediaAsset) -> str | None:
        request = self.context.get("request")
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class SEOSerializerMixin(serializers.Serializer):
    """
    Mix into any content detail serializer whose model uses
    apps.core.models.SEOFieldsMixin + seo_translated_fields(). Produces a
    single `seo` object with everything needed to render <head> tags and
    JSON-LD on the frontend, with sensible fallbacks baked in server-side
    so the frontend doesn't have to know the fallback chain.
    """

    seo = serializers.SerializerMethodField()

    def get_seo(self, obj) -> dict:
        request = self.context.get("request")

        og_image = obj.og_image
        if og_image is None:
            og_image = getattr(obj, "hero_image", None) or getattr(obj, "thumbnail", None) or getattr(obj, "cover_image", None)

        og_image_url = None
        if og_image and getattr(og_image, "file", None):
            og_image_url = request.build_absolute_uri(og_image.file.url) if request else og_image.file.url

        title = getattr(obj, "meta_title", "") or getattr(obj, "name", None) or getattr(obj, "title", "")
        description = getattr(obj, "meta_description", "") or getattr(obj, "short_description", None) or ""

        return {
            "meta_title": title,
            "meta_description": description,
            "meta_keywords": getattr(obj, "meta_keywords", ""),
            "canonical_url": getattr(obj, "canonical_url", ""),
            "og_title": title,
            "og_description": description,
            "og_image": og_image_url,
            "og_type": obj.og_type,
            "twitter_card": obj.twitter_card,
            "robots_meta_content": obj.robots_meta_content,
            "sitemap_priority": str(obj.sitemap_priority),
            "sitemap_changefreq": obj.sitemap_changefreq,
            "structured_data_type": obj.structured_data_type,
        }
