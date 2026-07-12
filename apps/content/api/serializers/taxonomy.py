"""
apps/content/api/serializers/taxonomy.py
────────────────────────────────────────────
Serializers for reference/lookup data: ServiceCategory, Technology,
Industry, ProcessStep, FAQ.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import FAQ, Industry, ProcessStep, ServiceCategory, Technology


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "slug", "icon", "order"]


class TechnologySerializer(serializers.ModelSerializer):
    class Meta:
        model = Technology
        fields = ["id", "name", "slug", "category", "icon", "website_url", "order"]


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ["id", "name", "slug", "description", "icon", "order"]


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ["id", "title", "description", "icon", "order"]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category", "service", "order"]
