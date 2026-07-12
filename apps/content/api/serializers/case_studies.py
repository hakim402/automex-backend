"""
apps/content/api/serializers/case_studies.py
─────────────────────────────────────────────────
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import CaseStudy

from .common import MediaAssetSerializer, SEOSerializerMixin
from .taxonomy import IndustrySerializer, TechnologySerializer


class CaseStudyGalleryImageSerializer(serializers.Serializer):
    id      = serializers.UUIDField()
    media   = MediaAssetSerializer()
    caption = serializers.CharField()
    order   = serializers.IntegerField()


class CaseStudyListSerializer(serializers.ModelSerializer):
    client_industry = IndustrySerializer(read_only=True)
    thumbnail       = MediaAssetSerializer(read_only=True)

    class Meta:
        model = CaseStudy
        fields = [
            "id", "slug", "title", "client_name", "client_industry",
            "thumbnail", "is_featured", "order", "published_at",
        ]


class CaseStudyDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    client_industry = IndustrySerializer(read_only=True)
    client_logo     = MediaAssetSerializer(read_only=True)
    thumbnail       = MediaAssetSerializer(read_only=True)
    technologies    = TechnologySerializer(many=True, read_only=True)
    gallery         = CaseStudyGalleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = CaseStudy
        fields = [
            "id", "slug", "title", "overview", "challenge", "solution", "results",
            "client_name", "client_industry", "client_logo", "thumbnail",
            "technologies", "gallery", "project_url", "project_duration_weeks",
            "is_featured", "published_at", "seo",
        ]
