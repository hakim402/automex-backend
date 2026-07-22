"""
apps/content/api/serializers/portfolio.py
──────────────────────────────────────────────
Portfolio projects with gallery images — list/detail split pattern.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import PortfolioProject

from .common import MediaAssetSerializer
from .taxonomy import IndustrySerializer, TechnologySerializer


class PortfolioGalleryImageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    image = MediaAssetSerializer()
    caption = serializers.SerializerMethodField()
    order = serializers.IntegerField()

    def get_caption(self, obj):
        lang = self.context.get("language_code", "en")
        return obj.safe_translation_getter("caption", language_code=lang) or ""


class PortfolioProjectListSerializer(serializers.ModelSerializer):
    cover_image = MediaAssetSerializer(read_only=True)
    industry = IndustrySerializer(read_only=True)

    class Meta:
        model = PortfolioProject
        fields = [
            "id", "slug", "title", "short_description",
            "cover_image", "client_name", "completion_year",
            "industry", "is_featured", "is_published",
            "order",
        ]


class PortfolioProjectDetailSerializer(serializers.ModelSerializer):
    cover_image = MediaAssetSerializer(read_only=True)
    services = serializers.SerializerMethodField()
    technologies = TechnologySerializer(many=True, read_only=True)
    industry = IndustrySerializer(read_only=True)
    gallery = PortfolioGalleryImageSerializer(many=True, read_only=True, source="gallery_images")

    class Meta:
        model = PortfolioProject
        fields = [
            "id", "slug", "title", "short_description",
            "cover_image", "services", "technologies", "industry",
            "project_url", "client_name", "completion_year",
            "gallery", "is_featured", "is_published",
            "order", "created_at",
        ]

    def get_services(self, obj):
        language_code = self.context.get("language_code", "en")
        from apps.content.models import Service
        services = obj.services.language(language_code).all()
        return [
            {"id": s.id, "slug": s.slug, "name": s.safe_translation_getter("name")}
            for s in services
        ]
