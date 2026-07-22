"""
apps/notifications/services.py
──────────────────────────────────
Notification service layer — creates Notification rows, enqueues delivery
via Celery, and provides high-level helpers for user-facing emails,
admin alerts, and dynamic SMTP dispatch.

Callers (apps.crm services, apps.assistant) never touch email/SMS/Slack/
WhatsApp directly — they call `notify()` or one of the business helpers
and move on.

Dynamic SMTP dispatch: prefers ThirdPartyIntegration credentials when
available, falls back to settings.EMAIL_HOST for zero-config deployments.
"""
from __future__ import annotations

import logging
import secrets
import smtplib
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import get_connection
from django.utils import timezone

from .models import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    ThirdPartyIntegration,
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
    batch_id: str = "",
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
        batch_id=batch_id,
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
# Dynamic SMTP dispatch
# ──────────────────────────────────────────────────────────────────────────────


def get_smtp_backend(integration=None):
    """
    Build a Django email backend from a ThirdPartyIntegration row's
    credentials. Falls back to settings.EMAIL_HOST if no integration
    is provided or found.

    Returns a Django EmailConnection instance.
    """
    if integration is None:
        integration = ThirdPartyIntegration.objects.filter(
            provider_type=ThirdPartyIntegration.ProviderType.SMTP,
            is_active=True,
            is_default_for_type=True,
        ).first()

    if integration is None:
        # Fall back to Django's default SMTP settings
        return get_connection()

    creds = integration.credentials or {}
    host = creds.get("host", settings.EMAIL_HOST)
    port = creds.get("port", settings.EMAIL_PORT)
    use_tls = creds.get("use_tls", settings.EMAIL_USE_TLS)
    username = creds.get("username", settings.EMAIL_HOST_USER)
    password = creds.get("password", settings.EMAIL_HOST_PASSWORD)

    return get_connection(
        host=host,
        port=int(port),
        use_tls=use_tls,
        username=username,
        password=password,
    )


def send_email_via_provider(
    recipient: str,
    subject: str,
    body: str,
    html_body: str = "",
    provider_slug: str | None = None,
) -> bool:
    """
    Send an email using a specific SMTP integration or the default one.
    Returns True on success, False on failure.
    """
    from django.core.mail import EmailMultiAlternatives

    integration = None
    if provider_slug:
        integration = ThirdPartyIntegration.objects.filter(
            slug=provider_slug,
            provider_type=ThirdPartyIntegration.ProviderType.SMTP,
            is_active=True,
        ).first()

    try:
        connection = get_smtp_backend(integration)
        from_email = (integration.credentials or {}).get(
            "from_email", settings.DEFAULT_FROM_EMAIL,
        ) if integration else settings.DEFAULT_FROM_EMAIL

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[recipient],
            connection=connection,
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send()
        return True
    except Exception:
        logger.exception("send_email_via_provider: failed to send to %s", recipient)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────────────────────────────


def create_guest_token() -> str:
    """Generate a secure random token for guest tracking."""
    return secrets.token_urlsafe(48)


def test_integration_connection(integration_id: str) -> dict:
    """
    Test the connection for a ThirdPartyIntegration.
    Returns {"success": bool, "message": str}.
    """
    try:
        integration = ThirdPartyIntegration.objects.get(id=integration_id)
    except ThirdPartyIntegration.DoesNotExist:
        return {"success": False, "message": "Integration not found."}

    now = timezone.now()

    if integration.provider_type == ThirdPartyIntegration.ProviderType.SMTP:
        creds = integration.credentials or {}
        try:
            host = creds.get("host", "")
            port = int(creds.get("port", 587))
            use_tls = creds.get("use_tls", True)
            username = creds.get("username", "")
            password = creds.get("password", "")

            if use_tls:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(host, port, timeout=10)
            if username:
                server.login(username, password)
            server.quit()

            integration.last_tested_at = now
            integration.last_test_result = "success"
            integration.save(update_fields=["last_tested_at", "last_test_result", "updated_at"])
            return {"success": True, "message": "SMTP connection successful."}
        except Exception as exc:
            error_msg = f"failed: {exc}"
            integration.last_tested_at = now
            integration.last_test_result = error_msg[:255]
            integration.save(update_fields=["last_tested_at", "last_test_result", "updated_at"])
            return {"success": False, "message": error_msg}

    elif integration.provider_type == ThirdPartyIntegration.ProviderType.SMS:
        # Basic validation — Twilio API test would go here
        creds = integration.credentials or {}
        if creds.get("account_sid") and creds.get("auth_token"):
            integration.last_tested_at = now
            integration.last_test_result = "success"
            integration.save(update_fields=["last_tested_at", "last_test_result", "updated_at"])
            return {"success": True, "message": "SMS credentials look valid."}
        return {"success": False, "message": "Missing required SMS credentials."}

    else:
        # Generic: just check credentials exist
        if integration.credentials:
            integration.last_tested_at = now
            integration.last_test_result = "success"
            integration.save(update_fields=["last_tested_at", "last_test_result", "updated_at"])
            return {"success": True, "message": "Credentials present."}
        return {"success": False, "message": "No credentials configured."}


# ──────────────────────────────────────────────────────────────────────────────
# Business-facing helpers — Admin alerts
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
    (settings.ADMIN_NOTIFICATION_EMAILS) whenever a new Lead is captured.
    Enhanced with priority, source_channel, and tags.
    """
    event_type = _EVENT_TYPE_BY_LEAD_TYPE.get(lead.lead_type, NotificationEventType.LEAD_CREATED)

    tags_str = ", ".join(lead.tags) if lead.tags else "-"
    subject = f"New {lead.get_lead_type_display()} — {lead.full_name}"
    body = (
        f"A new {lead.get_lead_type_display().lower()} came in on the AUTOMEX site.\n\n"
        f"Name: {lead.full_name}\n"
        f"Email: {lead.email}\n"
        f"Phone: {lead.phone or '-'}\n"
        f"Company: {lead.company or '-'}\n"
        f"Service interest: {lead.service_interest or '-'}\n"
        f"Priority: {lead.get_priority_display()}\n"
        f"Source channel: {lead.get_source_channel_display() if lead.source_channel else '-'}\n"
        f"Tags: {tags_str}\n"
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
        "priority": lead.priority,
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


def notify_admins_of_status_change(lead, old_status: str, new_status: str) -> list[Notification]:
    """Alert admins when a lead moves through the pipeline."""
    subject = f"Lead status changed — {lead.full_name}"
    body = (
        f"Lead '{lead.full_name}' ({lead.email}) status changed:\n\n"
        f"  From: {old_status}\n"
        f"  To:   {new_status}\n\n"
        f"View in admin: {settings.FRONTEND_BASE_URL}/admin/crm/lead/{lead.id}/change/"
    )
    context = {
        "lead_id": str(lead.id),
        "full_name": lead.full_name,
        "old_status": old_status,
        "new_status": new_status,
    }

    notifications = []
    for recipient_email in settings.ADMIN_NOTIFICATION_EMAILS:
        notifications.append(
            notify(
                event_type=NotificationEventType.REQUEST_STATUS_CHANGED,
                channel=NotificationChannel.EMAIL,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                context=context,
                related_object=lead,
                priority=NotificationPriority.NORMAL,
            )
        )
    return notifications


def notify_admins_of_new_ticket(ticket) -> list[Notification]:
    """Alert admins when a new support ticket is created."""
    owner = ticket.user or ticket.guest_email or "Unknown"
    subject = f"New support ticket — {ticket.title}"
    body = (
        f"A new support ticket has been created.\n\n"
        f"Title: {ticket.title}\n"
        f"Type: {ticket.get_ticket_type_display()}\n"
        f"Priority: {ticket.get_priority_display()}\n"
        f"From: {owner}\n"
        f"Description:\n{ticket.description[:500]}\n\n"
        f"View in admin: {settings.FRONTEND_BASE_URL}/admin/crm/supportticket/{ticket.id}/change/"
    )
    context = {
        "ticket_id": str(ticket.id),
        "title": ticket.title,
        "ticket_type": ticket.ticket_type,
    }

    notifications = []
    for recipient_email in settings.ADMIN_NOTIFICATION_EMAILS:
        notifications.append(
            notify(
                event_type=NotificationEventType.TICKET_CREATED,
                channel=NotificationChannel.EMAIL,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                context=context,
                related_object=ticket,
                priority=NotificationPriority.HIGH,
            )
        )
    return notifications


def notify_admins_of_ticket_message(ticket, message) -> list[Notification]:
    """Alert admins when a customer sends a ticket message."""
    author = message.author_name or (str(message.author_user) if message.author_user else "Unknown")
    subject = f"New ticket message — {ticket.title}"
    body = (
        f"A new message was posted on ticket '{ticket.title}'.\n\n"
        f"Author: {author}\n"
        f"Message:\n{message.body[:500]}\n\n"
        f"View in admin: {settings.FRONTEND_BASE_URL}/admin/crm/supportticket/{ticket.id}/change/"
    )
    context = {
        "ticket_id": str(ticket.id),
        "title": ticket.title,
        "author": author,
    }

    notifications = []
    for recipient_email in settings.ADMIN_NOTIFICATION_EMAILS:
        notifications.append(
            notify(
                event_type=NotificationEventType.TICKET_MESSAGE,
                channel=NotificationChannel.EMAIL,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                context=context,
                related_object=ticket,
                priority=NotificationPriority.NORMAL,
            )
        )
    return notifications


# ──────────────────────────────────────────────────────────────────────────────
# Business-facing helpers — User email notifications
# ──────────────────────────────────────────────────────────────────────────────


def _get_recipient_email(lead) -> str:
    """Get the best email for a lead (user email or lead email)."""
    if lead.user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(pk=lead.user_id).email
        except User.DoesNotExist:
            pass
    return lead.email


def notify_user_of_request_submitted(lead) -> Notification | None:
    """Send confirmation email to the user/guest after request submission."""
    recipient = _get_recipient_email(lead)
    if not recipient:
        return None

    token = lead.guest_token or ""
    subject = f"We received your request — Reference #{str(lead.id)[:8]}"
    body = (
        f"Hi {lead.full_name},\n\n"
        f"Thank you for your {lead.get_lead_type_display().lower()} request. "
        f"We've received it and our team will review it shortly.\n\n"
        f"Your reference ID: {lead.id}\n"
    )
    if token:
        body += f"Your tracking token: {token}\n"
    body += (
        f"\nWe'll keep you updated on the progress.\n\n"
        f"Best regards,\nThe AUTOMEX Team"
    )

    return notify(
        event_type=NotificationEventType.REQUEST_SUBMITTED,
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient,
        recipient_user=lead.user,
        subject=subject,
        body=body,
        context={"lead_id": str(lead.id), "full_name": lead.full_name},
        related_object=lead,
        priority=NotificationPriority.NORMAL,
        language=getattr(lead, "language", "en"),
    )


def notify_user_of_status_change(lead) -> Notification | None:
    """Notify user when their request status changes."""
    recipient = _get_recipient_email(lead)
    if not recipient:
        return None

    subject = f"Your request has been updated — #{str(lead.id)[:8]}"
    body = (
        f"Hi {lead.full_name},\n\n"
        f"Your request status has been updated to: {lead.get_status_display()}.\n\n"
        f"We'll keep you informed of any further changes.\n\n"
        f"Best regards,\nThe AUTOMEX Team"
    )

    return notify(
        event_type=NotificationEventType.REQUEST_STATUS_CHANGED,
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient,
        recipient_user=lead.user,
        subject=subject,
        body=body,
        context={"lead_id": str(lead.id), "status": lead.status},
        related_object=lead,
        priority=NotificationPriority.NORMAL,
        language=getattr(lead, "language", "en"),
    )


def notify_user_of_ticket_update(ticket, message=None) -> Notification | None:
    """Notify user of ticket update or new message."""
    recipient = ticket.guest_email
    if not recipient and ticket.user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            recipient = User.objects.get(pk=ticket.user_id).email
        except User.DoesNotExist:
            return None

    if not recipient:
        return None

    event_type = NotificationEventType.TICKET_MESSAGE if message else NotificationEventType.TICKET_UPDATED
    subject = f"Update on your ticket — {ticket.title}"
    body = f"Hi,\n\nYour support ticket '{ticket.title}' has been updated.\n"
    body += f"Status: {ticket.get_status_display()}\n"
    if message:
        body += f"\nNew message:\n{message.body[:500]}\n"
    body += f"\nBest regards,\nThe AUTOMEX Team"

    return notify(
        event_type=event_type,
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient,
        recipient_user=ticket.user,
        subject=subject,
        body=body,
        context={"ticket_id": str(ticket.id), "title": ticket.title},
        related_object=ticket,
        priority=NotificationPriority.NORMAL,
    )


def notify_user_of_quote_ready(lead) -> Notification | None:
    """Notify user that their quote has been prepared."""
    recipient = _get_recipient_email(lead)
    if not recipient:
        return None

    detail = getattr(lead, "quote_detail", None)
    price_info = ""
    if detail and detail.quoted_price_min:
        price_info = (
            f"\nQuoted price range: {detail.quoted_price_min} - {detail.quoted_price_max} "
            f"{detail.quoted_currency or 'USD'}"
        )

    subject = f"Your quote is ready — #{str(lead.id)[:8]}"
    body = (
        f"Hi {lead.full_name},\n\n"
        f"Great news! Your quote has been prepared."
        f"{price_info}\n\n"
        f"Our team will be in touch to discuss the details.\n\n"
        f"Best regards,\nThe AUTOMEX Team"
    )

    return notify(
        event_type=NotificationEventType.QUOTE_RECEIVED,
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient,
        recipient_user=lead.user,
        subject=subject,
        body=body,
        context={"lead_id": str(lead.id)},
        related_object=lead,
        priority=NotificationPriority.NORMAL,
    )


def notify_user_of_booking_confirmation(booking) -> Notification | None:
    """Notify user of booking confirmation with meeting link."""
    recipient = _get_recipient_email(booking.lead)
    if not recipient:
        return None

    meeting_info = ""
    if booking.meeting_link:
        meeting_info = f"\nMeeting link: {booking.meeting_link}"

    subject = f"Your consultation is confirmed — {booking.scheduled_date}"
    body = (
        f"Hi {booking.lead.full_name},\n\n"
        f"Your consultation has been confirmed.\n\n"
        f"Date: {booking.scheduled_date}\n"
        f"Time: {booking.scheduled_time} ({booking.timezone})\n"
        f"Type: {booking.get_meeting_type_display()}"
        f"{meeting_info}\n\n"
        f"We look forward to speaking with you!\n\n"
        f"Best regards,\nThe AUTOMEX Team"
    )

    return notify(
        event_type=NotificationEventType.BOOKING_CONFIRMED,
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient,
        recipient_user=booking.user,
        subject=subject,
        body=body,
        context={"booking_id": str(booking.id)},
        related_object=booking,
        priority=NotificationPriority.NORMAL,
    )


def notify_user_of_booking_reminder(booking) -> Notification | None:
    """Send a reminder email 24h before the booking."""
    recipient = _get_recipient_email(booking.lead)
    if not recipient:
        return None

    meeting_info = ""
    if booking.meeting_link:
        meeting_info = f"\nMeeting link: {booking.meeting_link}"

    subject = f"Reminder: Your consultation is tomorrow — {booking.scheduled_date}"
    body = (
        f"Hi {booking.lead.full_name},\n\n"
        f"This is a friendly reminder that you have a consultation scheduled for tomorrow.\n\n"
        f"Date: {booking.scheduled_date}\n"
        f"Time: {booking.scheduled_time} ({booking.timezone})\n"
        f"Type: {booking.get_meeting_type_display()}"
        f"{meeting_info}\n\n"
        f"Best regards,\nThe AUTOMEX Team"
    )

    return notify(
        event_type=NotificationEventType.BOOKING_REMINDER,
        channel=NotificationChannel.EMAIL,
        recipient_email=recipient,
        recipient_user=booking.user,
        subject=subject,
        body=body,
        context={"booking_id": str(booking.id)},
        related_object=booking,
        priority=NotificationPriority.NORMAL,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Digest
# ──────────────────────────────────────────────────────────────────────────────


def send_digest_notifications(frequency: str = "daily") -> list[Notification]:
    """
    Gather unread notifications for users with digest preferences and
    send them as a single batched email.
    """
    from .models import NotificationPreference

    batch_id = f"digest-{frequency}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    notifications_sent = []

    # Get users with this digest frequency
    prefs = NotificationPreference.objects.filter(
        digest_frequency=frequency,
        is_enabled=True,
    ).select_related("user")

    user_ids = set(prefs.values_list("user_id", flat=True))

    for user_id in user_ids:
        # Gather unread notifications for this user
        unread = Notification.objects.filter(
            recipient_user_id=user_id,
            is_read=False,
            channel=NotificationChannel.IN_APP,
        ).order_by("-created_at")[:50]

        if not unread.exists():
            continue

        # Build digest body
        lines = [f"Hi,\n\nHere's your {frequency} notification digest:\n"]
        for n in unread:
            lines.append(f"- [{n.get_event_type_display()}] {n.subject or '(no subject)'}")
        lines.append(f"\nYou have {unread.count()} unread notification(s) in total.")
        lines.append(f"\nBest regards,\nThe AUTOMEX Team")

        body = "\n".join(lines)

        # Get user email
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            continue

        notification = notify(
            event_type=NotificationEventType.CUSTOM,
            channel=NotificationChannel.EMAIL,
            recipient_email=user.email,
            recipient_user=user,
            subject=f"Your {frequency} digest — {unread.count()} notifications",
            body=body,
            batch_id=batch_id,
            priority=NotificationPriority.LOW,
        )
        notifications_sent.append(notification)

    return notifications_sent
