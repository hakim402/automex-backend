"""
apps/notifications/admin.py
───────────────────────────────
Unfold admin registrations for the multi-channel notification system:
NotificationTemplate, NotificationProviderConfig, Notification (+ read-only
NotificationDeliveryAttempt inline), NotificationPreference.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from .models import (
    Notification,
    NotificationDeliveryAttempt,
    NotificationPreference,
    NotificationProviderConfig,
    NotificationTemplate,
)

STATUS_LABELS = {
    "pending": "info",
    "queued": "info",
    "sent": "warning",
    "delivered": "success",
    "read": "success",
    "failed": "danger",
    "cancelled": "danger",
}

PRIORITY_LABELS = {
    "low": "info",
    "normal": "info",
    "high": "warning",
    "urgent": "danger",
}


# ──────────────────────────────────────────────────────────────────────────────
# TEMPLATE
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(ModelAdmin):
    list_display = ["key", "event_type", "channel", "language", "is_active", "version"]
    list_filter = [
        ("event_type", ChoicesDropdownFilter),
        ("channel", ChoicesDropdownFilter),
        "language",
        "is_active",
    ]
    search_fields = ["key", "subject", "body"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    list_filter_submit = True

    fieldsets = (
        (_("Identity"), {"fields": ("id", "key", "event_type", "channel", "language"), "classes": ["tab"]}),
        (_("Content"), {"fields": ("subject", "body"), "classes": ["tab"]}),
        (_("Status"), {"fields": ("is_active", "version", "created_by"), "classes": ["tab"]}),
    )

    @admin.action(description=_("Activate selected templates"))
    def action_activate(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_("Deactivate selected templates"))
    def action_deactivate(self, request, queryset):
        queryset.update(is_active=False)

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ──────────────────────────────────────────────────────────────────────────────
# PROVIDER CONFIG
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(NotificationProviderConfig)
class NotificationProviderConfigAdmin(ModelAdmin):
    list_display = ["channel", "provider_name", "is_active", "is_default"]
    list_filter = [("channel", ChoicesDropdownFilter), "is_active", "is_default"]
    search_fields = ["provider_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_make_default"]

    fieldsets = (
        (_("Provider"), {"fields": ("id", "channel", "provider_name"), "classes": ["tab"]}),
        (
            _("Configuration"),
            {
                "fields": ("credentials", "config"),
                "classes": ["tab"],
                "description": _(
                    "⚠️ credentials is a plaintext JSON placeholder for MVP — wire this to an "
                    "encrypted field or external secrets manager before storing real API keys."
                ),
            },
        ),
        (_("Status"), {"fields": ("is_active", "is_default"), "classes": ["tab"]}),
    )

    @admin.action(description=_("Make default for its channel"))
    def action_make_default(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                _("Select exactly one provider config to make it the channel default."),
                messages.ERROR,
            )
            return
        config = queryset.first()
        NotificationProviderConfig.objects.filter(channel=config.channel).update(is_default=False)
        config.is_default = True
        config.save(update_fields=["is_default"])
        self.message_user(
            request,
            _("%(provider)s is now the default provider for %(channel)s.")
            % {"provider": config.provider_name, "channel": config.get_channel_display()},
            messages.SUCCESS,
        )


# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICATION
# ──────────────────────────────────────────────────────────────────────────────


class NotificationDeliveryAttemptInline(TabularInline):
    model = NotificationDeliveryAttempt
    extra = 0
    can_delete = False
    tab = True
    fields = ["attempt_number", "provider_name", "status", "response_code", "duration_ms", "attempted_at"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = [
        "display_recipient",
        "event_type",
        "channel",
        "display_priority",
        "display_status",
        "retry_count",
        "created_at",
    ]
    list_filter = [
        ("event_type", ChoicesDropdownFilter),
        ("channel", ChoicesDropdownFilter),
        ("priority", ChoicesDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["recipient_email", "recipient_phone", "subject", "body"]
    autocomplete_fields = ["template", "recipient_user"]
    readonly_fields = [
        "id",
        "content_type",
        "object_id",
        "provider_message_id",
        "created_at",
        "sent_at",
        "delivered_at",
        "read_at",
    ]
    inlines = [NotificationDeliveryAttemptInline]
    date_hierarchy = "created_at"
    list_filter_submit = True
    compressed_fields = True
    actions = ["action_retry", "action_cancel"]

    fieldsets = (
        (
            _("Routing"),
            {
                "fields": (
                    "id",
                    "event_type",
                    "channel",
                    "template",
                    "recipient_user",
                    "recipient_email",
                    "recipient_phone",
                ),
                "classes": ["tab"],
            },
        ),
        (_("Content"), {"fields": ("subject", "body", "context"), "classes": ["tab"]}),
        (
            _("Related Object"),
            {"fields": ("content_type", "object_id"), "classes": ["tab"]},
        ),
        (
            _("Delivery"),
            {
                "fields": (
                    "priority",
                    "status",
                    "scheduled_at",
                    "sent_at",
                    "delivered_at",
                    "read_at",
                    "provider_message_id",
                    "failed_reason",
                    ("retry_count", "max_retries"),
                ),
                "classes": ["tab"],
            },
        ),
    )

    @display(description=_("Recipient"))
    def display_recipient(self, obj):
        return obj.recipient_user or obj.recipient_email or obj.recipient_phone or "—"

    @display(description=_("Priority"), label=PRIORITY_LABELS)
    def display_priority(self, obj):
        return obj.priority

    @display(description=_("Status"), label=STATUS_LABELS)
    def display_status(self, obj):
        return obj.status

    @admin.action(description=_("Retry selected (reset to pending)"))
    def action_retry(self, request, queryset):
        updated = queryset.filter(status="failed").update(status="pending", failed_reason="")
        self.message_user(request, _("%(count)d notification(s) queued for retry.") % {"count": updated})

    @admin.action(description=_("Cancel selected"))
    def action_cancel(self, request, queryset):
        updated = queryset.exclude(status__in=["sent", "delivered", "read"]).update(status="cancelled")
        self.message_user(
            request, _("%(count)d notification(s) cancelled.") % {"count": updated}, messages.WARNING
        )


# ──────────────────────────────────────────────────────────────────────────────
# PREFERENCE
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ["user", "event_type", "channel", "is_enabled"]
    list_filter = [
        ("event_type", ChoicesDropdownFilter),
        ("channel", ChoicesDropdownFilter),
        "is_enabled",
    ]
    search_fields = ["user__email"]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_enable", "action_disable"]

    @admin.action(description=_("Enable selected preferences"))
    def action_enable(self, request, queryset):
        queryset.update(is_enabled=True)

    @admin.action(description=_("Disable selected preferences"))
    def action_disable(self, request, queryset):
        queryset.update(is_enabled=False)