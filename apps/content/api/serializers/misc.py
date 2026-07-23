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
from .taxonomy import IndustrySerializer


class TeamMemberSerializer(serializers.ModelSerializer):
    photo = MediaAssetSerializer(read_only=True)
    department_display = serializers.CharField(source="get_department_display", read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            "id", "full_name", "slug", "role_title", "department", "department_display", "bio", "photo",
            "email", "linkedin_url", "github_url", "twitter_url",
            "is_leadership", "is_available_for_consulting",
            "specializations", "certifications", "years_of_experience",
            "education", "languages", "projects_showcase",
            "order",
        ]


class TestimonialSerializer(serializers.ModelSerializer):
    client_avatar = MediaAssetSerializer(read_only=True)
    video_thumbnail = MediaAssetSerializer(read_only=True)
    client_industry = IndustrySerializer(read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = Testimonial
        fields = [
            "id", "client_name", "client_role", "client_company", "client_avatar",
            "quote", "rating", "source", "source_display", "source_url",
            "related_case_study", "related_service", "is_featured", "order",
            "video_url", "video_thumbnail", "project_impact",
            "client_industry", "is_video_testimonial",
        ]
