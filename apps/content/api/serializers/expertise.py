"""
apps/content/api/serializers/expertise.py
──────────────────────────────────────────────
AI capabilities and technical expertise areas.
Non-translatable with nested technology references.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import AICapability, TechExpertiseArea

from .common import MediaAssetSerializer
from .taxonomy import TechnologySerializer


class AICapabilitySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    maturity_level_display = serializers.CharField(source="get_maturity_level_display", read_only=True)
    cover_image = MediaAssetSerializer(read_only=True)
    technologies = TechnologySerializer(many=True, read_only=True)

    class Meta:
        model = AICapability
        fields = [
            "id", "name", "slug", "description",
            "category", "category_display", "maturity_level", "maturity_level_display",
            "icon", "demo_url", "cover_image",
            "related_services", "technologies",
            "is_active", "order",
        ]


class TechExpertiseAreaSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    technologies = TechnologySerializer(many=True, read_only=True)

    class Meta:
        model = TechExpertiseArea
        fields = [
            "id", "name", "slug", "description",
            "icon", "category", "category_display",
            "technologies", "case_studies",
            "is_active", "order",
        ]
