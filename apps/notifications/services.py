"""
apps/notifications/services.py
──────────────────────────────────
Thin service layer: creates Notification rows and enqueues delivery via
Celery. Callers (apps.crm services, future apps.assistant) never touch
email/SMS/Slack/WhatsApp directly — they call `notify()` and move on.

Only the EMAIL channel actually sends in this phase (Gmail SMTP, already
configured in settings). SMS/WhatsApp/Slack create the Notification row
(so the pipeline and admin UI are fully wired) but the task marks them
FAILED with a clear "channel not implemented" reason until a provider is
added — nothing silently disappears.
"""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from .models import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
)

logger = logging.getLogger("apps.notifications")


# ──────────────────────────────────────────────────────────────────────────────
# Core primitive
# ──────────────────────────────────────────────────────────────────────────────

def notify(
    *,
    event_type: str,
    channel: str = NotificationChannel.EMAIL,
    recipient_email: str = "",
    recipient_phone: str = "",
    recipient_user=None,
    subject: str = "",
    body: str = "",
    context: dict[str, Any] | None = None,
    related_object=None,
    priority: str = NotificationPriority.NORMAL,
    language: str = "en",
) -> Notification:
    """
    Creates a Notification row (status=PENDING) and enqueues async delivery.
    If an active NotificationTemplate exists for (event_type, channel,
    language), it's used to render subject/body from `context`; otherwise
    the caller-supplied `subject`/`body` are used as-is.
    """
    context = context or {}

    template = NotificationTemplate.objects.filter(
        event_type=event_type, channel=channel, language=language, is_active=True,
    ).first()
    if template:
        try:
            subject = template.subject.format(**context) or subject
            body = template.body.format(**context) or body
        except (KeyError, IndexError):
            logger.warning(
                "notify: template %s missing a context key, falling back to caller-supplied content",
                template.key,
            )

    kwargs: dict[str, Any] = dict(
        event_type=event_type,
        channel=channel,
        template=template,
        recipient_user=recipient_user,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
        subject=subject,
        body=body,
        context=context,
        priority=priority,
        status=NotificationStatus.PENDING,
    )

    if related_object is not None:
        kwargs["content_type"] = ContentType.objects.get_for_model(type(related_object))
        kwargs["object_id"] = related_object.pk

    notification = Notification.objects.create(**kwargs)

    # Imported here (not at module level) to avoid a hard import-time
    # dependency between services.py and tasks.py / Celery app wiring.
    from .tasks import send_notification_task

    send_notification_task.delay(str(notification.id))
    return notification


# ──────────────────────────────────────────────────────────────────────────────
# Business-facing helpers
# ──────────────────────────────────────────────────────────────────────────────

_EVENT_TYPE_BY_LEAD_TYPE = {
    "contact": NotificationEventType.LEAD_CREATED,
    "quote": NotificationEventType.QUOTE_REQUESTED,
    "consultation": NotificationEventType.CONSULTATION_BOOKED,
    "newsletter": NotificationEventType.NEWSLETTER_SUBSCRIBED,
    "ai_assistant": NotificationEventType.AI_LEAD_CAPTURED,
}


def notify_admins_of_new_lead(lead) -> list[Notification]:
    """
    Sends one email notification per configured admin recipient
    (settings.ADMIN_NOTIFICATION_EMAILS) whenever a new Lead is captured,
    regardless of entry channel (contact form, quote request, booking,
    newsletter, AI assistant).
    """
    event_type = _EVENT_TYPE_BY_LEAD_TYPE.get(lead.lead_type, NotificationEventType.LEAD_CREATED)

    subject = f"New {lead.get_lead_type_display()} — {lead.full_name}"
    body = (
        f"A new {lead.get_lead_type_display().lower()} came in on the AUTOMEX site.\n\n"
        f"Name: {lead.full_name}\n"
        f"Email: {lead.email}\n"
        f"Phone: {lead.phone or '-'}\n"
        f"Company: {lead.company or '-'}\n"
        f"Service interest: {lead.service_interest or '-'}\n"
        f"Message:\n{lead.message or '-'}\n\n"
        f"Source: {lead.source_page or '-'}\n"
        f"UTM: source={lead.utm_source or '-'} medium={lead.utm_medium or '-'} campaign={lead.utm_campaign or '-'}\n\n"
        f"View in admin: {settings.FRONTEND_BASE_URL}/admin/crm/lead/{lead.id}/change/"
    )
    context = {
        "lead_id": str(lead.id),
        "full_name": lead.full_name,
        "email": lead.email,
        "lead_type": lead.lead_type,
    }

    notifications = []
    for recipient_email in settings.ADMIN_NOTIFICATION_EMAILS:
        notifications.append(
            notify(
                event_type=event_type,
                channel=NotificationChannel.EMAIL,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                context=context,
                related_object=lead,
                priority=NotificationPriority.HIGH,
            )
        )
    return notifications
