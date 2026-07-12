"""
apps/content/api/serializers/services.py
────────────────────────────────────────────
List serializer stays light (for grid/card rendering); detail serializer
carries the full landing-page payload including nested taxonomy and SEO.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import FAQ, Service

from .common import MediaAssetSerializer, SEOSerializerMixin
from .taxonomy import FAQSerializer, IndustrySerializer, ServiceCategorySerializer, TechnologySerializer


class ServiceListSerializer(serializers.ModelSerializer):
    category   = ServiceCategorySerializer(read_only=True)
    hero_image = MediaAssetSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "slug", "name", "short_description", "icon",
            "hero_image", "category", "is_featured", "order",
        ]


class ServiceDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    category     = ServiceCategorySerializer(read_only=True)
    hero_image   = MediaAssetSerializer(read_only=True)
    technologies = TechnologySerializer(many=True, read_only=True)
    industries   = IndustrySerializer(many=True, read_only=True)
    faqs         = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id", "slug", "name", "short_description", "overview",
            "problems_we_solve", "features", "benefits", "icon", "hero_image",
            "category", "technologies", "industries", "faqs",
            "is_featured", "published_at", "seo",
        ]

    def get_faqs(self, obj: Service):
        language_code = self.context.get("language_code")
        qs = FAQ.objects.filter(service=obj, is_active=True)
        if language_code:
            qs = qs.language(language_code)
        return FAQSerializer(qs.order_by("order"), many=True, context=self.context).data
