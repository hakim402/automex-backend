"""
apps/content/admin.py
─────────────────────────
Admin for all content models. Translated models use parler's
TranslatableAdmin (adds the language tab switcher) combined with Unfold's
ModelAdmin for the theme.
"""
from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from parler.admin import TranslatableAdmin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    FAQ,
    BlogCategory,
    BlogPost,
    BlogTag,
    CaseStudy,
    CaseStudyGalleryImage,
    Industry,
    ProcessStep,
    Service,
    ServiceCategory,
    TeamMember,
    Technology,
    Testimonial,
)


# ──────────────────────────────────────────────────────────────────────────────
# TAXONOMY
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Technology)
class TechnologyAdmin(ModelAdmin):
    list_display = ["name", "category", "order", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Industry)
class IndustryAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["name", "order", "is_active"]
    list_filter = ["is_active"]

    def name(self, obj: Industry) -> str:
        return obj.safe_translation_getter("name", any_language=True)


@admin.register(ProcessStep)
class ProcessStepAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["title", "order", "is_active"]
    list_filter = ["is_active"]

    def title(self, obj: ProcessStep) -> str:
        return obj.safe_translation_getter("title", any_language=True)


@admin.register(FAQ)
class FAQAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["question", "category", "service", "order", "is_active"]
    list_filter = ["category", "is_active"]
    autocomplete_fields = ["service"]

    def question(self, obj: FAQ) -> str:
        return obj.safe_translation_getter("question", any_language=True)


# ──────────────────────────────────────────────────────────────────────────────
# SERVICE
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(Service)
class ServiceAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["name", "category", "status", "is_featured", "order", "published_at"]
    list_filter = ["status", "is_featured", "category"]
    filter_horizontal = ["technologies", "industries"]
    search_fields = ["translations__name", "translations__slug"]
    readonly_fields = [
        "submitted_by", "submitted_at", "reviewed_by", "reviewed_at",
        "approved_by", "approved_at", "created_at", "updated_at",
    ]

    def name(self, obj: Service) -> str:
        return obj.safe_translation_getter("name", any_language=True)


# ──────────────────────────────────────────────────────────────────────────────
# CASE STUDIES
# ──────────────────────────────────────────────────────────────────────────────

class CaseStudyGalleryImageInline(TabularInline):
    model = CaseStudyGalleryImage
    extra = 1
    autocomplete_fields = ["media"]


@admin.register(CaseStudy)
class CaseStudyAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["title", "client_name", "client_industry", "status", "is_featured", "published_at"]
    list_filter = ["status", "is_featured", "client_industry"]
    filter_horizontal = ["technologies", "related_services"]
    inlines = [CaseStudyGalleryImageInline]
    readonly_fields = [
        "submitted_by", "submitted_at", "reviewed_by", "reviewed_at",
        "approved_by", "approved_at", "created_at", "updated_at",
    ]

    def title(self, obj: CaseStudy) -> str:
        return obj.safe_translation_getter("title", any_language=True)


# ──────────────────────────────────────────────────────────────────────────────
# BLOG
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(BlogCategory)
class BlogCategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogTag)
class BlogTagAdmin(ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogPost)
class BlogPostAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["title", "author", "category", "status", "is_featured", "published_at", "views_count"]
    list_filter = ["status", "is_featured", "category"]
    filter_horizontal = ["tags"]
    readonly_fields = [
        "submitted_by", "submitted_at", "reviewed_by", "reviewed_at",
        "approved_by", "approved_at", "created_at", "updated_at", "views_count",
    ]

    def title(self, obj: BlogPost) -> str:
        return obj.safe_translation_getter("title", any_language=True)

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# ──────────────────────────────────────────────────────────────────────────────
# TEAM & TESTIMONIALS
# ──────────────────────────────────────────────────────────────────────────────

@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ["full_name", "role_title", "department", "is_leadership", "is_active", "order"]
    list_filter = ["department", "is_leadership", "is_active"]
    search_fields = ["full_name", "role_title"]
    prepopulated_fields = {"slug": ("full_name",)}


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ["client_name", "client_company", "rating", "source", "is_featured", "is_published"]
    list_filter = ["source", "is_featured", "is_published"]
    search_fields = ["client_name", "client_company", "quote"]
