"""
apps/content/api/serializers/taxonomy.py
────────────────────────────────────────────
Serializers for reference/lookup data: ServiceCategory, Technology,
Industry, ProcessStep, FAQ.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import FAQ, Industry, ProcessStep, ServiceCategory, Technology

from .common import MediaAssetSerializer


class ServiceCategorySerializer(serializers.ModelSerializer):
    icon_image = MediaAssetSerializer(read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "slug", "icon", "icon_image", "description", "is_visible_on_nav", "order"]


class TechnologySerializer(serializers.ModelSerializer):
    logo = MediaAssetSerializer(read_only=True)
    proficiency_level_display = serializers.CharField(source="get_proficiency_level_display", read_only=True)

    class Meta:
        model = Technology
        fields = [
            "id", "name", "slug", "category", "icon", "logo",
            "website_url", "description", "proficiency_level",
            "proficiency_level_display", "order",
        ]


class IndustrySerializer(serializers.ModelSerializer):
    icon_image = MediaAssetSerializer(read_only=True)

    class Meta:
        model = Industry
        fields = ["id", "name", "slug", "description", "icon", "icon_image", "compliance_standards", "order"]


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ["id", "title", "description", "icon", "estimated_duration", "deliverables", "order"]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category", "service", "is_prominent", "order"]
