"""
apps/content/api/serializers/misc.py
─────────────────────────────────────
Team members and testimonials — simple, non-translatable, non-workflow
content, so no SEO mixin needed here.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import TeamMember, Testimonial

from .common import MediaAssetSerializer


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = MediaAssetSerializer(read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id", "full_name", "slug", "role_title", "department", "bio", "photo",
            "linkedin_url", "github_url", "twitter_url", "is_leadership", "order",
        ]


class TestimonialSerializer(serializers.ModelSerializer):
    client_avatar = MediaAssetSerializer(read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            "id", "client_name", "client_role", "client_company", "client_avatar",
            "quote", "rating", "source", "source_url",
            "related_case_study", "related_service", "is_featured", "order",
        ]
