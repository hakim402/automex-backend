"""
apps/content/api/serializers/blog.py
─────────────────────────────────────
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import BlogCategory, BlogPost, BlogTag

from .common import MediaAssetSerializer, SEOSerializerMixin


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description", "order"]


class BlogTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogTag
        fields = ["id", "name", "slug"]


class BlogAuthorSerializer(serializers.Serializer):
    """Minimal public author info — never expose the full accounts.User record."""

    id         = serializers.UUIDField()
    full_name  = serializers.SerializerMethodField()
    bio        = serializers.SerializerMethodField()
    role_title = serializers.SerializerMethodField()
    slug       = serializers.CharField()
    avatar     = MediaAssetSerializer(allow_null=True)
    linkedin_url = serializers.CharField(allow_blank=True)
    github_url   = serializers.CharField(allow_blank=True)

    def get_full_name(self, obj):
        lang = self.context.get("language_code", "en")
        return obj.safe_translation_getter("full_name", language_code=lang) or ""

    def get_bio(self, obj):
        lang = self.context.get("language_code", "en")
        return obj.safe_translation_getter("bio", language_code=lang) or ""

    def get_role_title(self, obj):
        lang = self.context.get("language_code", "en")
        return obj.safe_translation_getter("role_title", language_code=lang) or ""


class BlogPostListSerializer(serializers.ModelSerializer):
    category    = BlogCategorySerializer(read_only=True)
    tags        = BlogTagSerializer(many=True, read_only=True)
    cover_image = MediaAssetSerializer(read_only=True)
    author      = BlogAuthorSerializer(read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "title", "excerpt", "category", "tags", "cover_image",
            "author", "reading_time_minutes", "is_featured", "published_at",
        ]


class BlogPostDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    category    = BlogCategorySerializer(read_only=True)
    tags        = BlogTagSerializer(many=True, read_only=True)
    cover_image = MediaAssetSerializer(read_only=True)
    author      = BlogAuthorSerializer(read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "title", "excerpt", "content", "category", "tags",
            "cover_image", "author", "reading_time_minutes", "views_count",
            "is_featured", "published_at", "seo",
        ]
