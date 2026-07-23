"""
apps/content/api/serializers/case_studies.py
─────────────────────────────────────────────────
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import CaseStudy

from .common import MediaAssetSerializer, SEOSerializerMixin
from .taxonomy import IndustrySerializer, TechnologySerializer
from .misc import TestimonialSerializer


class CaseStudyGalleryImageSerializer(serializers.Serializer):
    id              = serializers.UUIDField()
    media           = MediaAssetSerializer()
    caption         = serializers.SerializerMethodField()
    is_before_after = serializers.BooleanField()
    image_type      = serializers.CharField()
    image_type_display = serializers.SerializerMethodField()
    order           = serializers.IntegerField()

    def get_caption(self, obj):
        lang = self.context.get("language_code", "en")
        return obj.safe_translation_getter("caption", language_code=lang) or ""

    def get_image_type_display(self, obj):
        return obj.get_image_type_display()


class CaseStudyListSerializer(serializers.ModelSerializer):
    client_industry = IndustrySerializer(read_only=True)
    client_logo     = MediaAssetSerializer(read_only=True)
    thumbnail       = MediaAssetSerializer(read_only=True)
    project_type_display = serializers.CharField(source="get_project_type_display", read_only=True)

    class Meta:
        model = CaseStudy
        fields = [
            "id", "slug", "title", "overview",
            "client_name", "client_industry", "client_logo", "thumbnail",
            "project_type", "project_type_display",
            "key_metrics", "is_ai_project",
            "is_featured", "order", "published_at",
        ]


class CaseStudyDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    client_industry = IndustrySerializer(read_only=True)
    client_logo     = MediaAssetSerializer(read_only=True)
    thumbnail       = MediaAssetSerializer(read_only=True)
    technologies    = TechnologySerializer(many=True, read_only=True)
    gallery         = CaseStudyGalleryImageSerializer(many=True, read_only=True)
    project_type_display = serializers.CharField(source="get_project_type_display", read_only=True)
    related_services = serializers.SerializerMethodField()
    testimonial     = TestimonialSerializer(read_only=True)

    class Meta:
        model = CaseStudy
        fields = [
            "id", "slug", "title", "overview", "challenge", "solution", "results",
            "client_name", "client_industry", "client_logo", "client_website",
            "thumbnail",
            "project_type", "project_type_display",
            "team_size", "project_year", "project_duration_display",
            "key_metrics", "is_ai_project", "ai_models_used",
            "technologies", "gallery",
            "related_services", "testimonial",
            "project_url", "project_duration_weeks",
            "is_featured", "published_at", "seo",
        ]

    def get_related_services(self, obj):
        from .services import ServiceListSerializer
        services = obj.related_services.all()
        if hasattr(obj, "_prefetched_objects_cache") and "related_services" in obj._prefetched_objects_cache:
            services = obj._prefetched_objects_cache["related_services"]
        return ServiceListSerializer(services, many=True, context=self.context).data
