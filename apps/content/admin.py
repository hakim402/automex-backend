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

from parler.admin import TranslatableAdmin, TranslatableInlineModelAdmin
from unfold.admin import ModelAdmin, TabularInline


class UnfoldTranslatableTabularInline(TranslatableInlineModelAdmin, TabularInline):
    """Unfold-themed TabularInline that supports parler translated fields."""
    pass
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.core.admin_mixins import ActiveToggleAdminMixin, PublishableAdminMixin

from .models import (
    FAQ,
    AICapability,
    BlogAuthor,
    BlogCategory,
    BlogHeroImage,
    BlogPost,
    BlogTag,
    CaseStudy,
    CaseStudyGalleryImage,
    Certification,
    Industry,
    Partner,
    PortfolioGalleryImage,
    PortfolioProject,
    ProcessStep,
    Service,
    ServiceAddOn,
    ServiceCategory,
    ServiceClientLogo,
    ServiceComparisonRow,
    ServiceDeliverable,
    ServiceDocument,
    ServiceHeroImage,
    ServiceProcessStep,
    ServiceSLA,
    ServiceTestimonial,
    TechExpertiseArea,
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
        "description": _(
            "Search engine optimisation settings for this page. "
            "Meta title and description appear in search result snippets. "
            "Canonical URL prevents duplicate-content penalties. "
            "OG image is used for social media link previews (Open Graph). "
            "Sitemap priority and change frequency control crawling behaviour."
        ),
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
class ServiceCategoryAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "slug", "icon", "display_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["translations__name", "slug"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")


@admin.register(Technology)
class TechnologyAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "category", "display_active", "order"]
    list_filter = [("category", ChoicesDropdownFilter), "is_active"]
    search_fields = ["translations__name", "slug"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["category", "order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")


@admin.register(Industry)
class IndustryAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "icon", "display_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["translations__name", "translations__slug"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    list_filter_submit = True
    warn_unsaved_form = True

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
    list_filter_submit = True
    warn_unsaved_form = True

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
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")


# ──────────────────────────────────────────────────────────────────────────────
# SERVICE INLINES
# ──────────────────────────────────────────────────────────────────────────────


class ServiceHeroImageInline(UnfoldTranslatableTabularInline):
    model = ServiceHeroImage
    extra = 1
    tab = True
    fields = ["image", "title", "caption", "is_cover", "order"]
    autocomplete_fields = ["image"]


class ServiceProcessStepInline(TabularInline):
    model = ServiceProcessStep
    extra = 1
    tab = True
    fields = ["process_step", "custom_title", "custom_description", "order"]
    autocomplete_fields = ["process_step"]


class ServiceDeliverableInline(UnfoldTranslatableTabularInline):
    model = ServiceDeliverable
    extra = 1
    tab = True
    fields = ["title", "description", "icon", "order"]


class ServiceAddOnInline(UnfoldTranslatableTabularInline):
    model = ServiceAddOn
    extra = 1
    tab = True
    fields = ["name", "description", "price", "is_included_in_enterprise", "order"]


class ServiceComparisonRowInline(UnfoldTranslatableTabularInline):
    model = ServiceComparisonRow
    extra = 1
    tab = True
    fields = ["feature_name", "standard_value", "premium_value", "enterprise_value", "is_highlighted", "order"]


class ServiceClientLogoInline(UnfoldTranslatableTabularInline):
    model = ServiceClientLogo
    extra = 1
    tab = True
    fields = ["logo", "client_name", "client_url", "order"]
    autocomplete_fields = ["logo"]


class ServiceTestimonialInline(TabularInline):
    model = ServiceTestimonial
    extra = 1
    tab = True
    fields = ["testimonial", "is_featured", "order"]
    autocomplete_fields = ["testimonial"]


class ServiceDocumentInline(UnfoldTranslatableTabularInline):
    model = ServiceDocument
    extra = 1
    tab = True
    fields = ["title", "file", "document_type", "is_public", "order"]
    autocomplete_fields = ["file"]


class ServiceSLAInline(UnfoldTranslatableTabularInline):
    model = ServiceSLA
    extra = 1
    tab = True
    fields = ["guarantee_name", "value", "description", "icon", "order"]


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
    save_on_top = True
    inlines = [
        ServiceHeroImageInline,
        ServiceProcessStepInline,
        ServiceDeliverableInline,
        ServiceAddOnInline,
        ServiceComparisonRowInline,
        ServiceClientLogoInline,
        ServiceTestimonialInline,
        ServiceDocumentInline,
        ServiceSLAInline,
    ]

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
                "description": _(
                    "Translatable content fields. Use the language tabs above to enter content for each "
                    "supported language. Slug is auto-generated from the name and used in the URL."
                ),
            },
        ),
        (
            _("Presentation"),
            {
                "fields": ("category", "icon", "hero_image", "technologies", "industries", "is_featured", "order"),
                "classes": ["tab"],
                "description": _(
                    "Controls how this service appears on the website. "
                    "Hero image is the main banner shown at the top of the service page. "
                    "Featured services appear on the homepage. Order controls the sort position in listings."
                ),
            },
        ),
        SEO_FIELDSET,
        PublishableAdminMixin.editorial_fieldset,
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
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


class CaseStudyGalleryImageInline(UnfoldTranslatableTabularInline):
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
    warn_unsaved_form = True
    save_on_top = True

    fieldsets = (
        (
            _("Content"),
            {
                "fields": ("id", "title", "slug", "overview", "challenge", "solution", "results"),
                "classes": ["tab"],
                "description": _(
                    "Translatable content fields. Use the language tabs above to enter content for each "
                    "supported language. Challenge, solution, and results are the core narrative sections."
                ),
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
                "description": _(
                    "Project metadata displayed alongside the case study narrative. "
                    "Client logo appears in the header and listing cards. "
                    "Related services links this case study to the services it showcases."
                ),
            },
        ),
        SEO_FIELDSET,
        PublishableAdminMixin.editorial_fieldset,
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
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
class BlogCategoryAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "slug", "display_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["translations__name", "slug"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")


@admin.register(BlogTag)
class BlogTagAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["translations__name", "slug"]
    readonly_fields = ["id"]
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")


@admin.register(BlogAuthor)
class BlogAuthorAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["full_name", "role_title", "email", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["translations__full_name", "translations__role_title", "email"]
    autocomplete_fields = ["avatar"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["slug"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("full_name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (
            _("Profile"),
            {
                "fields": ("id", "full_name", "slug", "bio", "avatar", "role_title"),
                "classes": ["tab"],
                "description": _(
                    "Author display name, URL slug, and professional bio shown on the author archive page. "
                    "Avatar is displayed next to blog posts and in the author listing."
                ),
            },
        ),
        (
            _("Contact & Social"),
            {
                "fields": ("email", "linkedin_url", "github_url"),
                "classes": ["tab"],
                "description": _("Public-facing contact info and social links shown on the author page."),
            },
        ),
        (_("Display"), {"fields": ("is_active",), "classes": ["tab"],
         "description": _("Inactive authors are hidden from the website.")}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


class BlogHeroImageInline(UnfoldTranslatableTabularInline):
    model = BlogHeroImage
    extra = 1
    autocomplete_fields = ["image"]
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
    inlines = [BlogHeroImageInline]
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
    warn_unsaved_form = True
    save_on_top = True

    fieldsets = (
        (_("Content"), {"fields": ("id", "title", "slug", "excerpt", "content"), "classes": ["tab"],
         "description": _(
             "Translatable content fields. Use language tabs for each supported language. "
             "Excerpt is the short preview shown in listing cards and search results."
         )}),
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
                "description": _(
                    "Controls how the blog post appears in listings. "
                    "Reading time is auto-calculated from content length. "
                    "Views count is read-only and incremented on each page view."
                ),
            },
        ),
        SEO_FIELDSET,
        PublishableAdminMixin.editorial_fieldset,
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
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
class TeamMemberAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["display_header", "role_title", "department", "is_leadership", "display_active", "order"]
    list_filter = [("department", ChoicesDropdownFilter), "is_leadership", "is_active"]
    search_fields = ["translations__full_name", "translations__role_title", "email"]
    autocomplete_fields = ["user", "photo"]
    filter_horizontal = ["projects_showcase"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("full_name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (
            _("Profile"),
            {
                "fields": ("id", "user", "full_name", "slug", "role_title", "department", "bio", "photo"),
                "classes": ["tab"],
                "description": _(
                    "If linked to a User account, the email and name sync from the User record. "
                    "Photo is displayed on the team page and in the about section."
                ),
            },
        ),
        (
            _("Contact & Social"),
            {
                "fields": ("email", "linkedin_url", "github_url", "twitter_url"),
                "classes": ["tab"],
                "description": _("Optional social links displayed on the team member card."),
            },
        ),
        (
            _("Display"),
            {
                "fields": ("is_leadership", "is_active", "order"),
                "classes": ["tab"],
                "description": _(
                    "Leadership members appear in a separate highlighted section. "
                    "Inactive members are hidden from the team page."
                ),
            },
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
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
class TestimonialAdmin(TranslatableAdmin, ModelAdmin):
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
    search_fields = ["translations__client_name", "translations__client_company", "translations__quote"]
    autocomplete_fields = ["client_avatar", "client_industry", "related_case_study", "related_service"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_feature", "action_unfeature", "action_publish", "action_unpublish"]
    ordering = ["order", "-created_at"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (
            _("Client"),
            {"fields": ("id", "client_name", "client_role", "client_company", "client_avatar"), "classes": ["tab"],
             "description": _("Who gave the testimonial. Client avatar appears next to the quote on the website.")},
        ),
        (
            _("Review"),
            {"fields": ("quote", "rating", "source", "source_url"), "classes": ["tab"],
             "description": _(
                 "The testimonial quote and star rating (1-5). "
                 "Source identifies where the review came from (e.g. Google, Clutch, direct). "
                 "Source URL links to the original review for verification."
             )},
        ),
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
                "description": _(
                    "Optionally associate this testimonial with a specific case study or service. "
                    "Featured testimonials appear on the homepage. Unpublished testimonials are hidden."
                ),
            },
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
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


# ──────────────────────────────────────────────────────────────────────────────
# PORTFOLIO
# ──────────────────────────────────────────────────────────────────────────────


class PortfolioGalleryImageInline(UnfoldTranslatableTabularInline):
    model = PortfolioGalleryImage
    extra = 1
    autocomplete_fields = ["image"]
    readonly_fields = ["id"]


@admin.register(PortfolioProject)
class PortfolioProjectAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["title", "client_name", "industry", "is_featured", "is_published", "completion_year", "order"]
    list_filter = ["is_featured", "is_published", ("industry", RelatedDropdownFilter)]
    search_fields = ["translations__title", "translations__client_name", "translations__short_description"]
    autocomplete_fields = ["cover_image", "industry"]
    filter_horizontal = ["services", "technologies"]
    inlines = [PortfolioGalleryImageInline]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order", "-created_at"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("title",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (_("Project"), {"fields": ("id", "title", "slug", "short_description", "cover_image"), "classes": ["tab"],
         "description": _("Core project identity. Short description is used in listing cards.")}),
        (_("Details"), {"fields": ("client_name", "project_url", "completion_year", "industry"), "classes": ["tab"],
         "description": _("Client-facing project metadata shown in the portfolio detail page.")}),
        (_("Relations"), {"fields": ("services", "technologies"), "classes": ["tab"],
         "description": _("Which services were delivered and technologies were used in this project.")}),
        (_("Display"), {"fields": ("is_featured", "is_published", "order"), "classes": ["tab"],
         "description": _("Featured projects appear on the homepage. Unpublished projects are hidden.")}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# EXPERTISE
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(AICapability)
class AICapabilityAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "category", "maturity_level", "is_active", "order"]
    list_filter = ["is_active", ("category", ChoicesDropdownFilter), ("maturity_level", ChoicesDropdownFilter)]
    search_fields = ["translations__name", "translations__description"]
    autocomplete_fields = ["cover_image"]
    filter_horizontal = ["related_services", "technologies"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (_("Capability"), {"fields": ("id", "name", "slug", "description", "category", "maturity_level"), "classes": ["tab"],
         "description": _(
             "Core AI capability identity. Category groups similar capabilities. "
             "Maturity level indicates whether this is research, experimental, or production-ready."
         )}),
        (_("Media"), {"fields": ("icon", "demo_url", "cover_image"), "classes": ["tab"],
         "description": _("Visual assets and optional demo link for showcasing this capability.")}),
        (_("Relations"), {"fields": ("related_services", "technologies"), "classes": ["tab"],
         "description": _("Link to services this capability enables and technologies used to implement it.")}),
        (_("Display"), {"fields": ("is_active", "order"), "classes": ["tab"],
         "description": _("Inactive capabilities are hidden from the website.")}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


@admin.register(TechExpertiseArea)
class TechExpertiseAreaAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "category", "is_active", "order"]
    list_filter = ["is_active", ("category", ChoicesDropdownFilter)]
    search_fields = ["translations__name", "translations__description"]
    filter_horizontal = ["technologies", "case_studies"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (_("Expertise Area"), {"fields": ("id", "name", "slug", "description", "icon", "category"), "classes": ["tab"],
         "description": _(
             "Technical expertise identity. Category groups related expertise areas "
             "(e.g. Cloud, AI, Security). Icon is displayed on the expertise listing page."
         )}),
        (_("Relations"), {"fields": ("technologies", "case_studies"), "classes": ["tab"],
         "description": _("Which technologies and case studies demonstrate this expertise area.")}),
        (_("Display"), {"fields": ("is_active", "order"), "classes": ["tab"],
         "description": _("Inactive expertise areas are hidden from the website.")}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# PARTNERS & CERTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Partner)
class PartnerAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "partner_type", "tier", "is_active", "order"]
    list_filter = ["is_active", ("partner_type", ChoicesDropdownFilter), ("tier", ChoicesDropdownFilter)]
    search_fields = ["translations__name", "translations__description"]
    autocomplete_fields = ["logo"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (_("Partner"), {"fields": ("id", "name", "slug", "logo", "website_url", "description"), "classes": ["tab"],
         "description": _("Basic partner information. Logo is displayed on the partners page and footer.")}),
        (_("Classification"), {"fields": ("partner_type", "tier"), "classes": ["tab"],
         "description": _(
             "Partner type (technology, reseller, etc.) and tier (strategic, gold, silver) "
             "control display grouping and prominence on the website."
         )}),
        (_("Display"), {"fields": ("is_active", "order"), "classes": ["tab"],
         "description": _("Inactive partners are hidden from the website.")}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


@admin.register(Certification)
class CertificationAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    list_display = ["name", "issuer", "is_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["translations__name", "translations__issuer", "credential_id"]
    autocomplete_fields = ["badge_image"]
    filter_horizontal = ["related_services"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["order"]
    list_filter_submit = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    fieldsets = (
        (_("Certification"), {"fields": ("id", "name", "issuer", "badge_image"), "classes": ["tab"],
         "description": _("Certification name, issuing body, and badge image displayed on the credentials page.")}),
        (_("Credentials"), {"fields": ("credential_url", "credential_id", "issue_date", "expiry_date"), "classes": ["tab"],
         "description": _(
             "Verification details. Credential URL links to the external verification page. "
             "Expiry date is used to flag certifications that need renewal."
         )}),
        (_("Relations"), {"fields": ("related_services",), "classes": ["tab"],
         "description": _("Which services this certification applies to.")}),
        (_("Display"), {"fields": ("is_active", "order"), "classes": ["tab"],
         "description": _("Inactive certifications are hidden from the website.")}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# SERVICE SUB‑MODELS (standalone registrations — also inlined in ServiceAdmin)
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(ServiceHeroImage)
class ServiceHeroImageAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "title", "caption", "is_cover", "order"]
    list_filter = ["is_cover"]
    search_fields = ["service__translations__name", "translations__title", "translations__caption"]
    autocomplete_fields = ["service", "image"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("Hero Image"), {"fields": ("id", "service", "image", "title", "caption"), "classes": ["tab"],
         "description": _("Translatable fields. Use the language tabs above to enter content for each supported language. Mark one as cover for the main banner.")}),
        (_("Display"), {"fields": ("is_cover", "order"), "classes": ["tab"],
         "description": _("Cover image is used as the main hero banner. Order controls the carousel sequence.")}),
    )


@admin.register(ServiceProcessStep)
class ServiceProcessStepAdmin(ModelAdmin):
    list_display = ["service", "process_step", "custom_title", "order"]
    search_fields = ["service__translations__name", "custom_title"]
    autocomplete_fields = ["service", "process_step"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (_("Link"), {"fields": ("id", "service", "process_step"), "classes": ["tab"],
         "description": _("Links a global Process Step to a specific service, allowing custom overrides.")}),
        (_("Customization"), {"fields": ("custom_title", "custom_description"), "classes": ["tab"],
         "description": _("Override the default title and description from the linked Process Step for this service.")}),
        (_("Display"), {"fields": ("order",), "classes": ["tab"],
         "description": _("Sort order in the process steps list.")}),
    )


@admin.register(ServiceDeliverable)
class ServiceDeliverableAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "title", "icon", "order"]
    search_fields = ["service__translations__name", "translations__title", "translations__description"]
    autocomplete_fields = ["service"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("Deliverable"), {"fields": ("id", "service", "title", "description", "icon"), "classes": ["tab"],
         "description": _("Translatable fields. Use language tabs for each supported language. A tangible output the client receives from this service. Icon is shown next to the title.")}),
        (_("Display"), {"fields": ("order",), "classes": ["tab"],
         "description": _("Sort order in the deliverables list.")}),
    )


@admin.register(ServiceAddOn)
class ServiceAddOnAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "name", "price", "is_included_in_enterprise", "order"]
    list_filter = ["is_included_in_enterprise"]
    search_fields = ["service__translations__name", "translations__name", "translations__description"]
    autocomplete_fields = ["service"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("Add-On"), {"fields": ("id", "service", "name", "description", "price"), "classes": ["tab"],
         "description": _("Translatable fields. Use language tabs for each supported language. Optional upgrade or add-on offered alongside this service. Price is displayed on the service page.")}),
        (_("Display"), {"fields": ("is_included_in_enterprise", "order"), "classes": ["tab"],
         "description": _("If included in enterprise, this add-on shows as bundled in the enterprise tier.")}),
    )


@admin.register(ServiceComparisonRow)
class ServiceComparisonRowAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "feature_name", "standard_value", "premium_value", "enterprise_value", "is_highlighted", "order"]
    list_filter = ["is_highlighted"]
    search_fields = ["service__translations__name", "translations__feature_name"]
    autocomplete_fields = ["service"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("Comparison Row"), {"fields": ("id", "service", "feature_name"), "classes": ["tab"],
         "description": _("Translatable feature name. A feature row in the tier comparison table. Each row compares Standard vs Premium vs Enterprise.")}),
        (_("Values"), {"fields": ("standard_value", "premium_value", "enterprise_value"), "classes": ["tab"],
         "description": _("What each tier offers for this feature (e.g. '✓', 'Unlimited', 'Contact us').")}),
        (_("Display"), {"fields": ("is_highlighted", "order"), "classes": ["tab"],
         "description": _("Highlighted rows get a distinct background to draw attention in the comparison table.")}),
    )


@admin.register(ServiceClientLogo)
class ServiceClientLogoAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "client_name", "order"]
    search_fields = ["service__translations__name", "translations__client_name"]
    autocomplete_fields = ["service", "logo"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("Client Logo"), {"fields": ("id", "service", "logo", "client_name", "client_url"), "classes": ["tab"],
         "description": _("Translatable client name. A client logo displayed in the service page logo carousel or trust bar.")}),
        (_("Display"), {"fields": ("order",), "classes": ["tab"],
         "description": _("Sort order in the logo carousel.")}),
    )


@admin.register(ServiceTestimonial)
class ServiceTestimonialAdmin(ModelAdmin):
    list_display = ["service", "testimonial", "is_featured", "order"]
    list_filter = ["is_featured"]
    search_fields = ["service__translations__name", "testimonial__client_name"]
    autocomplete_fields = ["service", "testimonial"]
    readonly_fields = ["id"]
    ordering = ["service", "-is_featured", "order"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (_("Link"), {"fields": ("id", "service", "testimonial"), "classes": ["tab"],
         "description": _("Associate an existing Testimonial with this service to show social proof.")}),
        (_("Display"), {"fields": ("is_featured", "order"), "classes": ["tab"],
         "description": _("Featured testimonials appear more prominently on the service page.")}),
    )


@admin.register(ServiceDocument)
class ServiceDocumentAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "title", "document_type", "is_public", "order"]
    list_filter = [("document_type", ChoicesDropdownFilter), "is_public"]
    search_fields = ["service__translations__name", "translations__title", "translations__description"]
    autocomplete_fields = ["service", "file"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("Document"), {"fields": ("id", "service", "title", "description", "file", "document_type"), "classes": ["tab"],
         "description": _(
             "Translatable fields. Use language tabs for each supported language. "
             "Upload a downloadable document (brochure, datasheet, case study PDF). "
             "Document type controls the icon and grouping on the service page."
         )}),
        (_("Display"), {"fields": ("is_public", "order"), "classes": ["tab"],
         "description": _("Non-public documents are only visible to authenticated clients.")}),
    )


@admin.register(ServiceSLA)
class ServiceSLAAdmin(TranslatableAdmin, ModelAdmin):
    list_display = ["service", "guarantee_name", "value", "icon", "order"]
    search_fields = ["service__translations__name", "translations__guarantee_name", "translations__value", "translations__description"]
    autocomplete_fields = ["service"]
    readonly_fields = ["id"]
    ordering = ["service", "order"]
    compressed_fields = True
    warn_unsaved_form = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service").prefetch_related("translations")

    fieldsets = (
        (_("SLA"), {"fields": ("id", "service", "guarantee_name", "value", "description", "icon"), "classes": ["tab"],
         "description": _(
             "Translatable fields. Use language tabs for each supported language. "
             "A service-level guarantee (e.g. '99.9% Uptime', '24h Response'). "
             "Value is the metric, description explains the guarantee terms."
         )}),
        (_("Display"), {"fields": ("order",), "classes": ["tab"],
         "description": _("Sort order in the SLA guarantees list.")}),
    )