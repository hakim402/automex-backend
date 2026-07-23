"""
apps/content/api/serializers/blog.py
─────────────────────────────────────
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import BlogCategory, BlogHeroImage, BlogPost, BlogTag

from .common import MediaAssetSerializer, SEOSerializerMixin


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description", "icon", "is_active", "order"]


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


class BlogHeroImageSerializer(serializers.Serializer):
    id       = serializers.UUIDField()
    image    = MediaAssetSerializer(allow_null=True)
    caption  = serializers.SerializerMethodField()
    is_cover = serializers.BooleanField()
    order    = serializers.IntegerField()

    def get_caption(self, obj):
        lang = self.context.get("language_code", "en")
        return obj.safe_translation_getter("caption", language_code=lang) or ""


class BlogPostListSerializer(serializers.ModelSerializer):
    category        = BlogCategorySerializer(read_only=True)
    tags            = BlogTagSerializer(many=True, read_only=True)
    cover_image     = MediaAssetSerializer(read_only=True)
    thumbnail_image = MediaAssetSerializer(read_only=True)
    author          = BlogAuthorSerializer(read_only=True)
    content_type_display = serializers.CharField(source="get_content_type_display", read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "title", "excerpt", "category", "tags",
            "cover_image", "thumbnail_image", "author",
            "content_type", "content_type_display",
            "reading_time_minutes", "is_featured", "is_premium",
            "video_embed_url", "published_at",
        ]


class BlogPostDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    category        = BlogCategorySerializer(read_only=True)
    tags            = BlogTagSerializer(many=True, read_only=True)
    cover_image     = MediaAssetSerializer(read_only=True)
    thumbnail_image = MediaAssetSerializer(read_only=True)
    author          = BlogAuthorSerializer(read_only=True)
    content_type_display = serializers.CharField(source="get_content_type_display", read_only=True)
    hero_images     = serializers.SerializerMethodField()
    related_services    = serializers.SerializerMethodField()
    related_case_studies = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "title", "excerpt", "content",
            "category", "tags", "cover_image", "thumbnail_image",
            "author", "content_type", "content_type_display",
            "reading_time_minutes", "views_count",
            "is_featured", "is_premium", "video_embed_url",
            "external_url", "hero_images",
            "related_services", "related_case_studies",
            "published_at", "created_at", "updated_at", "seo",
        ]

    def get_hero_images(self, obj):
        items = obj.hero_images.all()
        if hasattr(obj, "_prefetched_objects_cache") and "hero_images" in obj._prefetched_objects_cache:
            items = obj._prefetched_objects_cache["hero_images"]
        return BlogHeroImageSerializer(items, many=True, context=self.context).data

    def get_related_services(self, obj):
        from .services import ServiceListSerializer
        services = obj.related_services.all()
        if hasattr(obj, "_prefetched_objects_cache") and "related_services" in obj._prefetched_objects_cache:
            services = obj._prefetched_objects_cache["related_services"]
        return ServiceListSerializer(services, many=True, context=self.context).data

    def get_related_case_studies(self, obj):
        from .case_studies import CaseStudyListSerializer
        studies = obj.related_case_studies.all()
        if hasattr(obj, "_prefetched_objects_cache") and "related_case_studies" in obj._prefetched_objects_cache:
            studies = obj._prefetched_objects_cache["related_case_studies"]
        return CaseStudyListSerializer(studies, many=True, context=self.context).data
