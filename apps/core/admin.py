"""
apps/core/admin.py
─────────────────────
Admin for cross-cutting core models: MediaAsset, APIKey, SEOSettings, Redirect.
"""
from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import APIKey, MediaAsset, Redirect, SEOSettings


@admin.register(MediaAsset)
class MediaAssetAdmin(ModelAdmin):
    list_display = ["title_or_filename", "file_type", "size_bytes", "uploaded_by", "created_at"]
    list_filter = ["file_type"]
    search_fields = ["title", "alt_text", "caption"]
    readonly_fields = ["created_at", "updated_at", "width", "height", "mime_type", "size_bytes"]

    @display(description=_("Title"))
    def title_or_filename(self, obj: MediaAsset) -> str:
        return obj.title or obj.file.name

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(APIKey)
class APIKeyAdmin(ModelAdmin):
    list_display = ["name", "prefix", "is_active", "last_used_at", "expires_at", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "prefix"]
    readonly_fields = ["key_hash", "prefix", "last_used_at", "created_at", "updated_at", "created_by"]

    def has_change_permission(self, request, obj=None):
        # Keys are immutable once created (aside from is_active/expires_at) —
        # the raw key is never stored, so there's nothing else safe to edit.
        return True

    def get_readonly_fields(self, request, obj=None):
        if obj:  # existing key — only allow toggling is_active/expires_at
            return self.readonly_fields
        return ["last_used_at", "created_at", "updated_at", "created_by"]

    def save_model(self, request, obj, form, change):
        if not change:
            # Creating directly in admin without the management command:
            # generate the key here and show it once via a message.
            from django.contrib import messages

            instance, raw_key = type(obj).generate(name=obj.name, created_by=request.user)
            obj.pk = instance.pk
            messages.warning(
                request,
                f"Raw API key (copy now, shown only once): {raw_key}",
            )
            return
        super().save_model(request, obj, form, change)


@admin.register(SEOSettings)
class SEOSettingsAdmin(ModelAdmin):
    list_display = ["site_name", "organization_legal_name", "updated_at"]

    def has_add_permission(self, request):
        # Singleton — block adding a second row once one exists.
        return not SEOSettings.objects.exists()


@admin.register(Redirect)
class RedirectAdmin(ModelAdmin):
    list_display = ["old_path", "new_path", "is_permanent", "is_active", "hit_count"]
    list_filter = ["is_permanent", "is_active"]
    search_fields = ["old_path", "new_path"]
    readonly_fields = ["hit_count", "created_at", "updated_at"]
