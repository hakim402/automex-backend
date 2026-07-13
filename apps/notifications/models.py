"""
apps/notifications/models.py
────────────────────────────────
Enterprise multi-channel notification system covering: Email, SMS,
WhatsApp, Slack, and In-App. Every business event (lead created, quote
requested, consultation booked, content published, ...) is decoupled from
delivery mechanics through this layer:

    trigger event → NotificationTemplate (per event+channel+language)
                  → Notification (queued instance, generic-linked to the
                     triggering object) → NotificationDeliveryAttempt
                     (retry-tracked log) via a provider from
                     NotificationProviderConfig.

Staff can opt in/out per (event_type, channel) via NotificationPreference.

NOTE on secrets: NotificationProviderConfig.credentials uses
apps.core.fields.EncryptedJSONField (Fernet, key in settings.FIELD_ENCRYPTION_KEY)
— encrypted at rest, not a plain JSONField. See apps/core/fields.py for
the key-management notes (generate via `manage.py generate_field_encryption_key`).
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import EncryptedJSONField
from apps.core.models import TimeStampedModel, UUIDModel


class NotificationChannel(models.TextChoices):
    EMAIL    = "email",    _("Email")
    SMS      = "sms",      _("SMS")
    WHATSAPP = "whatsapp", _("WhatsApp")
    SLACK    = "slack",    _("Slack")
    IN_APP   = "in_app",   _("In-App")


class NotificationEventType(models.TextChoices):
    LEAD_CREATED                 = "lead_created",                 _("Lead Created")
    LEAD_ASSIGNED                = "lead_assigned",                _("Lead Assigned")
    LEAD_STATUS_CHANGED          = "lead_status_changed",          _("Lead Status Changed")
    QUOTE_REQUESTED              = "quote_requested",               _("Quote Requested")
    CONSULTATION_BOOKED          = "consultation_booked",           _("Consultation Booked")
    CONSULTATION_REMINDER        = "consultation_reminder",         _("Consultation Reminder")
    CONSULTATION_CANCELLED       = "consultation_cancelled",        _("Consultation Cancelled")
    NEWSLETTER_SUBSCRIBED        = "newsletter_subscribed",         _("Newsletter Subscribed")
    AI_LEAD_CAPTURED             = "ai_lead_captured",              _("AI Assistant Captured Lead")
    CONTENT_SUBMITTED_FOR_REVIEW = "content_submitted_for_review",  _("Content Submitted for Review")
    CONTENT_APPROVED             = "content_approved",              _("Content Approved")
    CONTENT_PUBLISHED            = "content_published",             _("Content Published")
    CONTENT_REJECTED             = "content_rejected",               _("Content Rejected")
    SYSTEM_ALERT                 = "system_alert",                   _("System Alert")
    CUSTOM                       = "custom",                         _("Custom")


class NotificationPriority(models.TextChoices):
    LOW    = "low",    _("Low")
    NORMAL = "normal", _("Normal")
    HIGH   = "high",   _("High")
    URGENT = "urgent", _("Urgent")


class NotificationStatus(models.TextChoices):
    PENDING   = "pending",   _("Pending")
    QUEUED    = "queued",    _("Queued")
    SENT      = "sent",      _("Sent")
    DELIVERED = "delivered", _("Delivered")
    READ      = "read",      _("Read")
    FAILED    = "failed",    _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


class NotificationTemplate(UUIDModel, TimeStampedModel):
    key = models.SlugField(
        _("key"), max_length=150, unique=True,
        help_text=_("Unique identifier, e.g. 'lead_created.email.en'."),
    )
    event_type = models.CharField(_("event type"), max_length=40, choices=NotificationEventType.choices, db_index=True)
    channel    = models.CharField(_("channel"), max_length=20, choices=NotificationChannel.choices, db_index=True)
    language   = models.CharField(_("language"), max_length=10, default="en")

    subject = models.CharField(
        _("subject"), max_length=255, blank=True,
        help_text=_("Used for email/push. Supports {placeholders} resolved from the notification context."),
    )
    body = models.TextField(_("body"), help_text=_("Supports {placeholders} resolved from the notification context."))

    is_active = models.BooleanField(_("active"), default=True, db_index=True)
    version   = models.PositiveIntegerField(_("version"), default=1)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("created by"),
    )

    class Meta:
        ordering            = ["event_type", "channel", "language"]
        verbose_name        = _("notification template")
        verbose_name_plural = _("notification templates")
        constraints = [
            models.UniqueConstraint(
                fields=["event_type", "channel", "language"], name="uq_template_event_channel_lang",
            ),
        ]

    def __str__(self) -> str:
        return self.key


class NotificationProviderConfig(UUIDModel, TimeStampedModel):
    """
    Which external provider handles each channel (SendGrid/SES for email,
    Twilio for SMS, Meta Cloud API for WhatsApp, Incoming Webhook for Slack).
    See module docstring re: credential encryption before production use.
    """

    channel       = models.CharField(_("channel"), max_length=20, choices=NotificationChannel.choices, db_index=True)
    provider_name = models.CharField(
        _("provider name"), max_length=100,
        help_text=_("e.g. 'sendgrid', 'twilio', 'slack_webhook', 'whatsapp_cloud_api'."),
    )
    credentials = EncryptedJSONField(_("credentials"), blank=True, default=dict)
    config      = models.JSONField(_("extra config"), default=dict, blank=True)

    is_active  = models.BooleanField(_("active"), default=True)
    is_default = models.BooleanField(_("default for channel"), default=False)

    class Meta:
        ordering            = ["channel", "-is_default"]
        verbose_name        = _("notification provider config")
        verbose_name_plural = _("notification provider configs")
        constraints = [
            models.UniqueConstraint(
                fields=["channel"],
                condition=models.Q(is_default=True),
                name="uq_one_default_provider_per_channel",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_channel_display()} → {self.provider_name}"


class Notification(UUIDModel, TimeStampedModel):
    event_type = models.CharField(_("event type"), max_length=40, choices=NotificationEventType.choices, db_index=True)
    channel    = models.CharField(_("channel"), max_length=20, choices=NotificationChannel.choices, db_index=True)
    template   = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notifications", verbose_name=_("template"),
    )

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notifications", verbose_name=_("recipient (internal user)"),
    )
    recipient_email = models.EmailField(_("recipient email"), blank=True)
    recipient_phone = models.CharField(_("recipient phone"), max_length=30, blank=True)

    subject = models.CharField(_("subject"), max_length=255, blank=True)
    body    = models.TextField(_("rendered body"), blank=True)
    context = models.JSONField(_("render context"), default=dict, blank=True)

    # ── Generic link to the triggering object (Lead, ConsultationBooking, etc.) ──
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("related content type"),
    )
    object_id      = models.UUIDField(_("related object id"), null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    priority = models.CharField(
        _("priority"), max_length=10, choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL, db_index=True,
    )
    status = models.CharField(
        _("status"), max_length=20, choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING, db_index=True,
    )

    scheduled_at = models.DateTimeField(_("scheduled at"), null=True, blank=True)
    sent_at      = models.DateTimeField(_("sent at"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("delivered at"), null=True, blank=True)
    read_at      = models.DateTimeField(_("read at"), null=True, blank=True)

    provider_message_id = models.CharField(_("provider message id"), max_length=255, blank=True)
    failed_reason        = models.TextField(_("failed reason"), blank=True)
    retry_count           = models.PositiveSmallIntegerField(_("retry count"), default=0)
    max_retries            = models.PositiveSmallIntegerField(_("max retries"), default=3)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("notification")
        verbose_name_plural = _("notifications")
        indexes = [
            models.Index(fields=["status", "priority", "-created_at"], name="idx_notif_status_prio_created"),
            models.Index(fields=["recipient_user", "status"], name="idx_notif_recipient_status"),
            models.Index(fields=["content_type", "object_id"], name="idx_notif_related_object"),
            models.Index(fields=["event_type", "channel"], name="idx_notif_event_channel"),
        ]

    def __str__(self) -> str:
        target = self.recipient_user_id or self.recipient_email or self.recipient_phone or "unknown"
        return f"{self.get_event_type_display()} → {target} ({self.get_channel_display()})"


class NotificationDeliveryAttempt(UUIDModel):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="delivery_attempts", verbose_name=_("notification"),
    )
    attempt_number    = models.PositiveSmallIntegerField(_("attempt number"))
    provider_name     = models.CharField(_("provider name"), max_length=100, blank=True)
    status            = models.CharField(_("status"), max_length=20, choices=NotificationStatus.choices)
    response_code     = models.CharField(_("response code"), max_length=20, blank=True)
    response_payload  = models.JSONField(_("response payload"), default=dict, blank=True)
    error_message     = models.TextField(_("error message"), blank=True)
    duration_ms       = models.PositiveIntegerField(_("duration (ms)"), null=True, blank=True)
    attempted_at      = models.DateTimeField(_("attempted at"), auto_now_add=True)

    class Meta:
        ordering            = ["-attempted_at"]
        verbose_name        = _("notification delivery attempt")
        verbose_name_plural = _("notification delivery attempts")
        constraints = [
            models.UniqueConstraint(fields=["notification", "attempt_number"], name="uq_delivery_attempt_number"),
        ]

    def __str__(self) -> str:
        return f"Attempt #{self.attempt_number} for {self.notification_id} — {self.status}"


class NotificationPreference(UUIDModel, TimeStampedModel):
    """Per-staff-user opt-in/opt-out per (event_type, channel). Absence of a row = default enabled."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notification_preferences", verbose_name=_("user"),
    )
    event_type = models.CharField(_("event type"), max_length=40, choices=NotificationEventType.choices)
    channel    = models.CharField(_("channel"), max_length=20, choices=NotificationChannel.choices)
    is_enabled = models.BooleanField(_("enabled"), default=True)

    class Meta:
        ordering            = ["user", "event_type", "channel"]
        verbose_name        = _("notification preference")
        verbose_name_plural = _("notification preferences")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event_type", "channel"], name="uq_notif_pref_user_event_channel",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.event_type}/{self.channel}: {'on' if self.is_enabled else 'off'}"
