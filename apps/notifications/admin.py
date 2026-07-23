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
    ThirdPartyIntegration,
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
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": ("id", "key", "event_type", "channel", "language"),
                "classes": ["tab"],
                "description": _(
                    "Uniquely identifies this template. Language-specific templates share the same key. "
                    "Event type determines when this template is triggered (e.g. lead_created, booking_confirmed)."
                ),
            },
        ),
        (
            _("Content"),
            {
                "fields": ("subject", "body"),
                "classes": ["tab"],
                "description": _(
                    "Mustache-style placeholders ({{ variable }}) are supported for dynamic content. "
                    "Subject is used for email push notifications; body is the full message content."
                ),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active", "version", "created_by"),
                "classes": ["tab"],
                "description": _(
                    "Version is auto-incremented on each save to track template changes. "
                    "Inactive templates are skipped by the notification dispatcher."
                ),
            },
        ),
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
    list_display = ["channel", "provider_name", "is_active", "is_default", "integration"]
    list_filter = [("channel", ChoicesDropdownFilter), "is_active", "is_default"]
    search_fields = ["provider_name"]
    autocomplete_fields = ["integration"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_make_default"]
    list_filter_submit = True
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Provider"),
            {
                "fields": ("id", "channel", "provider_name"),
                "classes": ["tab"],
                "description": _("Which notification channel this config serves and the provider handle."),
            },
        ),
        (
            _("Configuration"),
            {
                "fields": ("credentials", "config", "integration"),
                "classes": ["tab"],
                "description": _(
                    "Credentials holds encrypted provider secrets (API keys, tokens). "
                    "Config holds non-secret settings like region or priority. "
                    "Link to a Third-Party Integration for centralized credential management."
                ),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active", "is_default"),
                "classes": ["tab"],
                "description": _(
                    "Only one config per channel should be the default. "
                    "The default provider is used when no specific provider is requested."
                ),
            },
        ),
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
    warn_unsaved_form = True
    save_on_top = True
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
                "description": _(
                    "Determines which template and provider are used to deliver this notification. "
                    "Recipient can be a registered user (preferred) or a raw email/phone number. "
                    "Channel selects email, SMS, push, or in-app delivery."
                ),
            },
        ),
        (
            _("Content"),
            {
                "fields": ("subject", "body", "context"),
                "classes": ["tab"],
                "description": _(
                    "Final rendered subject and body after template interpolation. "
                    "Context stores the JSON variables that were merged into the template."
                ),
            },
        ),
        (
            _("Related Object"),
            {
                "fields": ("content_type", "object_id"),
                "classes": ["tab"],
                "description": _(
                    "Generic foreign key linking to the model instance that triggered this notification "
                    "(e.g. a Lead, Booking, or Ticket)."
                ),
            },
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
                "description": _(
                    "Delivery lifecycle tracking. Priority affects queuing order. "
                    "Leave scheduled_at blank for immediate delivery. "
                    "Provider message ID is the external ID returned by the delivery service."
                ),
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
        failed_qs = queryset.filter(status="failed")
        notification_ids = list(failed_qs.values_list("id", flat=True))
        updated = failed_qs.update(status="pending", failed_reason="")

        # Re-enqueue delivery for each reset notification
        if notification_ids:
            from .tasks import send_notification_task
            for nid in notification_ids:
                send_notification_task.delay(str(nid))

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
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Preference"),
            {
                "fields": ("id", "user", "event_type", "channel"),
                "classes": ["tab"],
                "description": _(
                    "Per-user, per-event-type, per-channel opt-in/opt-out. "
                    "Users manage these from their notification settings page. "
                    "Disabled preferences will skip that channel for that event type."
                ),
            },
        ),
        (_("Status"), {"fields": ("is_enabled",), "classes": ["tab"]}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    @admin.action(description=_("Enable selected preferences"))
    def action_enable(self, request, queryset):
        queryset.update(is_enabled=True)

    @admin.action(description=_("Disable selected preferences"))
    def action_disable(self, request, queryset):
        queryset.update(is_enabled=False)


# ──────────────────────────────────────────────────────────────────────────────
# THIRD-PARTY INTEGRATION
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(ThirdPartyIntegration)
class ThirdPartyIntegrationAdmin(ModelAdmin):
    list_display = [
        "name",
        "provider_type",
        "provider_name",
        "is_active",
        "is_default_for_type",
        "last_tested_at",
        "display_test_result",
    ]
    list_filter = [
        ("provider_type", ChoicesDropdownFilter),
        "is_active",
        "is_default_for_type",
    ]
    search_fields = ["name", "provider_name", "description"]
    readonly_fields = ["id", "last_tested_at", "last_test_result", "created_at", "updated_at"]
    actions = ["action_test_connection", "action_activate", "action_deactivate"]
    list_filter_submit = True
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": ("id", "name", "slug", "provider_type", "provider_name", "description"),
                "classes": ["tab"],
            },
        ),
        (
            _("Credentials"),
            {
                "fields": ("credentials",),
                "classes": ["tab", "collapse"],
                "description": _(
                    "Encrypted at rest using Fernet encryption. "
                    "SMTP: {\"host\": \"smtp.gmail.com\", \"port\": 587, \"use_tls\": true, "
                    "\"username\": \"...\", \"password\": \"...\", \"from_email\": \"...\"}. "
                    "Twilio: {\"account_sid\": \"...\", \"auth_token\": \"...\", \"from_number\": \"...\"}."
                ),
            },
        ),
        (
            _("Config"),
            {"fields": ("config",), "classes": ["tab", "collapse"]},
        ),
        (
            _("Status"),
            {
                "fields": ("is_active", "is_default_for_type", "last_tested_at", "last_test_result"),
                "classes": ["tab"],
            },
        ),
    )

    @display(description=_("Test Result"))
    def display_test_result(self, obj):
        if not obj.last_test_result:
            return "—"
        if obj.last_test_result == "success":
            return [obj.last_test_result, {"color": "success"}]
        return [obj.last_test_result, {"color": "danger"}]

    @admin.action(description=_("Test connection"))
    def action_test_connection(self, request, queryset):
        from .services import test_integration_connection

        for integration in queryset:
            result = test_integration_connection(str(integration.id))
            if result["success"]:
                self.message_user(
                    request,
                    _("%(name)s: %(msg)s") % {"name": integration.name, "msg": result["message"]},
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    _("%(name)s: %(msg)s") % {"name": integration.name, "msg": result["message"]},
                    messages.ERROR,
                )

    @admin.action(description=_("Activate selected"))
    def action_activate(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_("Deactivate selected"))
    def action_deactivate(self, request, queryset):
        queryset.update(is_active=False)


# ──────────────────────────────────────────────────────────────────────────────
# DELIVERY ATTEMPT (standalone — read-only log; also inlined in NotificationAdmin)
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(NotificationDeliveryAttempt)
class NotificationDeliveryAttemptAdmin(ModelAdmin):
    list_display = ["notification", "attempt_number", "provider_name", "display_status", "response_code", "duration_ms", "attempted_at"]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        "provider_name",
        ("attempted_at", RangeDateFilter),
    ]
    search_fields = ["notification__recipient_email", "provider_name", "error_message"]
    readonly_fields = [
        "id",
        "notification",
        "attempt_number",
        "provider_name",
        "status",
        "response_code",
        "response_payload",
        "error_message",
        "duration_ms",
        "attempted_at",
    ]
    date_hierarchy = "attempted_at"
    list_filter_submit = True
    ordering = ["-attempted_at"]

    fieldsets = (
        (
            _("Attempt"),
            {
                "fields": ("id", "notification", "attempt_number", "provider_name", "status"),
                "classes": ["tab"],
                "description": _(
                    "Each delivery attempt is logged automatically. "
                    "Attempt number tracks retries. Provider name is the service used (e.g. SendGrid, Twilio)."
                ),
            },
        ),
        (
            _("Result"),
            {
                "fields": ("response_code", "response_payload", "error_message", "duration_ms"),
                "classes": ["tab"],
                "description": _(
                    "HTTP response code from the provider (200 = success). "
                    "Response payload is the full provider response for debugging. "
                    "Duration is the round-trip time in milliseconds."
                ),
            },
        ),
        (_("Timestamp"), {"fields": ("attempted_at",), "classes": ["tab"],
         "description": _("When this delivery attempt was made. Read-only audit trail.")}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(description=_("Status"), label=STATUS_LABELS)
    def display_status(self, obj):
        return obj.status