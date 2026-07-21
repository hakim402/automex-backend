"""
apps/content/api/serializers/partners.py
────────────────────────────────────────────
Technology partners, certifications, and ecosystem relationships.
Non-translatable, simple read-only serializers.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import Certification, Partner

from .common import MediaAssetSerializer


class PartnerSerializer(serializers.ModelSerializer):
    logo = MediaAssetSerializer(read_only=True)
    partner_type_display = serializers.CharField(source="get_partner_type_display", read_only=True)
    tier_display = serializers.CharField(source="get_tier_display", read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id", "name", "slug", "logo", "website_url",
            "partner_type", "partner_type_display", "tier", "tier_display",
            "description", "is_active", "order",
        ]


class CertificationSerializer(serializers.ModelSerializer):
    badge_image = MediaAssetSerializer(read_only=True)

    class Meta:
        model = Certification
        fields = [
            "id", "name", "issuer", "badge_image",
            "credential_url", "credential_id",
            "issue_date", "expiry_date",
            "related_services", "is_active", "order",
        ]
