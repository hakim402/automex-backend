"""
apps/core/admin.py
─────────────────────
Unfold admin registrations for shared/core infrastructure models:
MediaAsset (central asset library), ContentRevision (read-only audit trail),
SEOSettings (singleton), and Redirect (301/302 table).
"""
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter
from unfold.decorators import display

from .admin_mixins import ActiveToggleAdminMixin
from .models import APIKey, ContentRevision, MediaAsset, Redirect, SEOSettings


def _human_size(num_bytes: int | None) -> str:
    if not num_bytes:
        return "—"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ──────────────────────────────────────────────────────────────────────────────
# MEDIA ASSET
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ["display_thumbnail", "display_title", "file_type", "display_size", "uploaded_by", "created_at"]
    list_filter = [
        ("file_type", ChoicesDropdownFilter),
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["title", "alt_text", "caption"]
    readonly_fields = ["id", "mime_type", "size_bytes", "width", "height", "created_at", "updated_at"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (_("File"), {"fields": ("id", "title", "file", "file_type"), "classes": ["tab"],
         "description": _("The uploaded file. File type is auto-detected from the MIME type on upload.")}),
        (
            _("Metadata"),
            {
                "fields": ("mime_type", "size_bytes", "width", "height", "alt_text", "caption", "tags"),
                "classes": ["tab"],
                "description": _(
                    "Technical metadata auto-extracted from the file on upload. "
                    "Alt text is critical for accessibility (screen readers) and SEO. "
                    "Caption is displayed below the image in content pages. "
                    "Tags support comma-separated values for filtering."
                ),
            },
        ),
        (_("Audit"), {"fields": ("uploaded_by", "created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-populated upload tracking and timestamps.")}),
    )

    @display(description=_("Preview"))
    def display_thumbnail(self, obj):
        if obj.file_type == MediaAsset.FileType.IMAGE and obj.file:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />',
                obj.file.url,
            )
        return "—"

    @display(description=_("Title"))
    def display_title(self, obj):
        return obj.title or obj.file.name

    @display(description=_("Size"), ordering="size_bytes")
    def display_size(self, obj):
        return _human_size(obj.size_bytes)


# ──────────────────────────────────────────────────────────────────────────────
# CONTENT REVISION  (read-only audit trail — written by the service layer)
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(ContentRevision)
class ContentRevisionAdmin(ModelAdmin):
    list_display = ["content_type", "object_id", "version", "status_at_snapshot", "created_by", "created_at"]
    list_filter = [
        ("content_type", ChoicesDropdownFilter),
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["object_id", "change_summary"]
    readonly_fields = [
        "id",
        "content_type",
        "object_id",
        "version",
        "status_at_snapshot",
        "snapshot",
        "change_summary",
        "created_by",
        "created_at",
    ]

    def has_add_permission(self, request):
        # Revisions are written exclusively by the service layer on status
        # transitions — never created manually from the admin.
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────────────────────────────────────
# SEO SETTINGS  (singleton)
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(SEOSettings)
class SEOSettingsAdmin(ModelAdmin):
    readonly_fields = ["id"]
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (_("Site"), {"fields": ("site_name", "default_meta_title_suffix", "default_meta_description", "default_og_image"), "classes": ["tab"],
         "description": _(
             "Default meta tags used as fallback when a specific page does not provide its own. "
             "Site name is appended to page titles. Default OG image is used for social sharing."
         )}),
        (
            _("Organization (JSON-LD)"),
            {
                "fields": (
                    "organization_legal_name",
                    "organization_logo",
                    "organization_url",
                    "organization_social_profiles",
                    "contact_email",
                    "contact_phone",
                ),
                "classes": ["tab"],
                "description": _(
                    "Used to generate Schema.org Organization structured data for the homepage. "
                    "This helps search engines display rich results (knowledge panel, sitelinks). "
                    "Social profiles should be entered as JSON: {\"twitter\": \"...\", \"linkedin\": \"...\"}."
                ),
            },
        ),
        (
            _("Verification & Analytics"),
            {
                "fields": ("google_site_verification", "google_analytics_id", "google_tag_manager_id"),
                "classes": ["tab"],
                "description": _(
                    "Google service IDs. Site verification proves domain ownership for Search Console. "
                    "Analytics ID (e.g. G-XXXXXXXXXX) enables GA4 tracking. "
                    "Tag Manager ID (e.g. GTM-XXXXXXX) enables GTM container loading."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        # True singleton: block "Add" once a row already exists.
        return not SEOSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────────────────────────────────────
# REDIRECT
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Redirect)
class RedirectAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["old_path", "new_path", "is_permanent", "display_active", "hit_count"]
    list_filter = ["is_permanent", "is_active"]
    search_fields = ["old_path", "new_path"]
    readonly_fields = ["id", "hit_count", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    list_filter_submit = True

    fieldsets = (
        (_("Redirect"), {"fields": ("id", "old_path", "new_path"), "classes": ["tab"],
         "description": _(
             "Old path should be a relative URL (e.g. /old-page). "
             "New path can be relative or absolute. 301 = permanent (cached by browsers). 302 = temporary."
         )}),
        (_("Status"), {"fields": ("is_permanent", "is_active", "hit_count"), "classes": ["tab"],
         "description": _(
             "Hit count is auto-incremented each time the redirect is followed. "
             "Inactive redirects are ignored by the middleware."
         )}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"],
         "description": _("Auto-managed timestamps.")}),
    )


# ──────────────────────────────────────────────────────────────────────────────
# API KEY
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(APIKey)
class APIKeyAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["name", "display_prefix", "display_active", "last_used_at", "expires_at", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "prefix"]
    readonly_fields = ["id", "key_hash", "prefix", "last_used_at", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": ("id", "name", "prefix", "key_hash"),
                "classes": ["tab"],
                "description": _(
                    "The raw API key is shown ONLY at creation time. "
                    "Only a SHA-256 hash is stored — the raw key cannot be retrieved later. "
                    "If lost, revoke this key and create a new one."
                ),
            },
        ),
        (
            _("Lifecycle"),
            {
                "fields": ("is_active", "expires_at", "last_used_at"),
                "classes": ["tab"],
                "description": _(
                    "Expired API keys are automatically rejected by the API. "
                    "Last used at is updated on every authenticated request."
                ),
            },
        ),
        (
            _("Audit"),
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ["tab"],
            },
        ),
    )

    @display(description=_("Prefix"))
    def display_prefix(self, obj):
        return f"{obj.prefix}…" if obj.prefix else "—"