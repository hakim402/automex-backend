"""
apps/content/admin.py
───────────────────────
Unfold admin registrations for every public-facing content model.

Translation note
-----------------
Service / CaseStudy / BlogPost / Industry / ProcessStep / FAQ all use
django-parler (TranslatableModel + TranslatedFields). Their ModelAdmins mix
in parler's `TranslatableAdmin` alongside Unfold's `ModelAdmin`:

    class ServiceAdmin(TranslatableAdmin, PublishableAdminMixin, ModelAdmin):
        ...

`TranslatableAdmin` renders the language-switch tab bar (via its own
`admin/parler/change_form.html`, which extends whatever template Unfold
would otherwise use) and lets translated fields be used directly in
`list_display`, `fieldsets`, and (via `translations__<field>`) `search_fields`.

For a fully Unfold-themed language tab bar (matching the dark/light theme
exactly) install the optional community package `django-unfold-extra` and
swap `TranslatableAdmin` for `unfold_extra.contrib.parler.TranslatableAdmin`
— everything else in this file stays the same. Plain parler works out of the
box without that extra dependency, which is what's used below.
"""
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from parler.admin import TranslatableAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.core.admin_mixins import ActiveToggleAdminMixin, PublishableAdminMixin

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
    Technology,
    TeamMember,
    Testimonial,
)

# ──────────────────────────────────────────────────────────────────────────────
# SHARED SEO FIELDSET  (language-independent half of SEOFieldsMixin)
# ──────────────────────────────────────────────────────────────────────────────

SEO_FIELDSET = (
    _("SEO"),
    {
        "fields": (
            "meta_title",
            "meta_description",
            "meta_keywords",
            "canonical_url",
            "og_image",
            "og_type",
            "twitter_card",
            ("robots_index", "robots_follow"),
            ("sitemap_priority", "sitemap_changefreq"),
            "structured_data_type",
        ),
        "classes": ["tab"],
    },
)
# NOTE: meta_title/meta_description/meta_keywords/canonical_url are
# per-language (inside TranslatedFields via seo_translated_fields()); the
# rest (og_image, robots_*, sitemap_*, structured_data_type) live directly
# on the model. Parler's TranslatableAdmin lets both kinds share one
# fieldset transparently.


# ──────────────────────────────────────────────────────────────────────────────
# TAXONOMY
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["name", "slug", "icon", "display_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order", "name"]


@admin.register(Technology)
class TechnologyAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["name", "category", "display_active", "order"]
    list_filter = [("category", ChoicesDropdownFilter), "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["category", "order", "name"]
    list_filter_submit = True


@admin.register(Industry)
class IndustryAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "icon", "display_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["translations__name", "translations__slug"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")


@admin.register(ProcessStep)
class ProcessStepAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["title", "icon", "display_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["translations__title"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")


@admin.register(FAQ)
class FAQAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["question", "category", "service", "display_active", "order"]
    list_filter = [("category", ChoicesDropdownFilter), ("service", RelatedDropdownFilter), "is_active"]
    search_fields = ["translations__question", "translations__answer"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    autocomplete_fields = ["service"]
    list_filter_submit = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")


# ──────────────────────────────────────────────────────────────────────────────
# SERVICE
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Service)
class ServiceAdmin(TranslatableAdmin, PublishableAdminMixin, ModelAdmin):
    list_display = ["name", "category", "display_status", "is_featured", "order", "created_at"]
    list_filter = [
        ("category", RelatedDropdownFilter),
        ("status", ChoicesDropdownFilter),
        "is_featured",
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["translations__name", "translations__slug"]
    autocomplete_fields = ["category", "hero_image"]
    filter_horizontal = ["technologies", "industries"]
    readonly_fields = ["id", "created_at", "updated_at", *PublishableAdminMixin.editorial_readonly_fields]
    actions = [*PublishableAdminMixin.publishable_actions]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Content"),
            {
                "fields": (
                    "id",
                    "name",
                    "slug",
                    "short_description",
                    "overview",
                    "problems_we_solve",
                    "features",
                    "benefits",
                ),
                "classes": ["tab"],
            },
        ),
        (
            _("Presentation"),
            {
                "fields": ("category", "icon", "hero_image", "technologies", "industries", "is_featured", "order"),
                "classes": ["tab"],
            },
        ),
        SEO_FIELDSET,
        PublishableAdminMixin.editorial_fieldset,
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .prefetch_related("translations", "technologies", "industries")
        )


# ──────────────────────────────────────────────────────────────────────────────
# CASE STUDY
# ──────────────────────────────────────────────────────────────────────────────


class CaseStudyGalleryImageInline(TabularInline):
    model = CaseStudyGalleryImage
    extra = 0
    tab = True
    fields = ["media", "caption", "order"]
    autocomplete_fields = ["media"]


@admin.register(CaseStudy)
class CaseStudyAdmin(TranslatableAdmin, PublishableAdminMixin, ModelAdmin):
    list_display = ["title", "client_name", "client_industry", "display_status", "is_featured", "order"]
    list_filter = [
        ("client_industry", RelatedDropdownFilter),
        ("status", ChoicesDropdownFilter),
        "is_featured",
    ]
    search_fields = ["translations__title", "translations__slug", "client_name"]
    autocomplete_fields = ["client_industry", "client_logo", "thumbnail"]
    filter_horizontal = ["technologies", "related_services"]
    readonly_fields = ["id", "created_at", "updated_at", *PublishableAdminMixin.editorial_readonly_fields]
    actions = [*PublishableAdminMixin.publishable_actions]
    inlines = [CaseStudyGalleryImageInline]
    list_filter_submit = True
    compressed_fields = True

    fieldsets = (
        (
            _("Content"),
            {
                "fields": ("id", "title", "slug", "overview", "challenge", "solution", "results"),
                "classes": ["tab"],
            },
        ),
        (
            _("Client & Project"),
            {
                "fields": (
                    "client_name",
                    "client_industry",
                    "client_logo",
                    "thumbnail",
                    "technologies",
                    "related_services",
                    "project_url",
                    "project_duration_weeks",
                    "is_featured",
                    "order",
                ),
                "classes": ["tab"],
            },
        ),
        SEO_FIELDSET,
        PublishableAdminMixin.editorial_fieldset,
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("title",)}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("client_industry")
            .prefetch_related("translations", "technologies", "related_services")
        )


# ──────────────────────────────────────────────────────────────────────────────
# BLOG
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(BlogCategory)
class BlogCategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id"]
    ordering = ["order", "name"]


@admin.register(BlogTag)
class BlogTagAdmin(ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["id"]


@admin.register(BlogPost)
class BlogPostAdmin(TranslatableAdmin, PublishableAdminMixin, ModelAdmin):
    list_display = ["title", "author", "category", "display_status", "is_featured", "views_count", "published_at"]
    list_filter = [
        ("category", RelatedDropdownFilter),
        ("author", RelatedDropdownFilter),
        ("status", ChoicesDropdownFilter),
        "is_featured",
        ("published_at", RangeDateFilter),
    ]
    search_fields = ["translations__title", "translations__slug", "translations__content"]
    autocomplete_fields = ["author", "category", "cover_image"]
    filter_horizontal = ["tags"]
    readonly_fields = [
        "id",
        "views_count",
        "created_at",
        "updated_at",
        *PublishableAdminMixin.editorial_readonly_fields,
    ]
    actions = [*PublishableAdminMixin.publishable_actions]
    date_hierarchy = "published_at"
    list_filter_submit = True
    compressed_fields = True

    fieldsets = (
        (_("Content"), {"fields": ("id", "title", "slug", "excerpt", "content"), "classes": ["tab"]}),
        (
            _("Presentation"),
            {
                "fields": (
                    "author",
                    "category",
                    "tags",
                    "cover_image",
                    "reading_time_minutes",
                    "views_count",
                    "is_featured",
                ),
                "classes": ["tab"],
            },
        ),
        SEO_FIELDSET,
        PublishableAdminMixin.editorial_fieldset,
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("title",)}

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related("translations", "tags")
        )


# ──────────────────────────────────────────────────────────────────────────────
# TEAM
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(TeamMember)
class TeamMemberAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["display_header", "role_title", "department", "is_leadership", "display_active", "order"]
    list_filter = [("department", ChoicesDropdownFilter), "is_leadership", "is_active"]
    search_fields = ["full_name", "role_title", "email"]
    prepopulated_fields = {"slug": ("full_name",)}
    autocomplete_fields = ["user", "photo"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order", "full_name"]
    list_filter_submit = True

    fieldsets = (
        (
            _("Profile"),
            {
                "fields": ("id", "user", "full_name", "slug", "role_title", "department", "bio", "photo"),
                "classes": ["tab"],
            },
        ),
        (
            _("Contact & Social"),
            {"fields": ("email", "linkedin_url", "github_url", "twitter_url"), "classes": ["tab"]},
        ),
        (_("Display"), {"fields": ("is_leadership", "is_active", "order"), "classes": ["tab"]}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    @display(description=_("Team Member"), header=True)
    def display_header(self, obj):
        parts = [p for p in obj.full_name.split() if p]
        initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else obj.full_name[:2].upper()
        return [obj.full_name, obj.email or "—", initials]


# ──────────────────────────────────────────────────────────────────────────────
# TESTIMONIAL
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = [
        "client_name",
        "client_company",
        "display_rating",
        "source",
        "is_featured",
        "is_published",
        "order",
    ]
    list_filter = [("source", ChoicesDropdownFilter), "is_featured", "is_published"]
    search_fields = ["client_name", "client_company", "quote"]
    autocomplete_fields = ["client_avatar", "related_case_study", "related_service"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_feature", "action_unfeature", "action_publish", "action_unpublish"]
    ordering = ["order", "-created_at"]
    list_filter_submit = True

    fieldsets = (
        (
            _("Client"),
            {"fields": ("id", "client_name", "client_role", "client_company", "client_avatar"), "classes": ["tab"]},
        ),
        (_("Review"), {"fields": ("quote", "rating", "source", "source_url"), "classes": ["tab"]}),
        (
            _("Linking & Display"),
            {
                "fields": (
                    "related_case_study",
                    "related_service",
                    "is_featured",
                    "is_published",
                    "order",
                ),
                "classes": ["tab"],
            },
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    @display(description=_("Rating"))
    def display_rating(self, obj):
        return format_html("★" * obj.rating + "☆" * (5 - obj.rating))

    @admin.action(description=_("Mark as featured"))
    def action_feature(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description=_("Remove from featured"))
    def action_unfeature(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description=_("Publish selected"))
    def action_publish(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description=_("Unpublish selected"))
    def action_unpublish(self, request, queryset):
        queryset.update(is_published=False)