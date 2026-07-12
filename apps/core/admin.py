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
from .models import ContentRevision, MediaAsset, Redirect, SEOSettings


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

    fieldsets = (
        (_("File"), {"fields": ("id", "title", "file", "file_type"), "classes": ["tab"]}),
        (
            _("Metadata"),
            {
                "fields": ("mime_type", "size_bytes", "width", "height", "alt_text", "caption", "tags"),
                "classes": ["tab"],
            },
        ),
        (_("Audit"), {"fields": ("uploaded_by", "created_at", "updated_at"), "classes": ["tab"]}),
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

    fieldsets = (
        (_("Site"), {"fields": ("site_name", "default_meta_title_suffix", "default_meta_description", "default_og_image"), "classes": ["tab"]}),
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
            },
        ),
        (
            _("Verification & Analytics"),
            {
                "fields": ("google_site_verification", "google_analytics_id", "google_tag_manager_id"),
                "classes": ["tab"],
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