"""
apps/notifications/tasks.py
────────────────────────────────
Delivers a single Notification. EMAIL channel uses dynamic SMTP dispatch
via ThirdPartyIntegration when available, falling back to Django's
default settings. SMS/WhatsApp/Slack record the attempt and fail clearly
rather than pretending to succeed.

Also includes Celery beat tasks for booking reminders and digest emails.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import (
    Notification,
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationProviderConfig,
    NotificationStatus,
    ThirdPartyIntegration,
)

logger = logging.getLogger("apps.notifications")

_TERMINAL_STATUSES = {
    NotificationStatus.SENT,
    NotificationStatus.DELIVERED,
    NotificationStatus.READ,
    NotificationStatus.CANCELLED,
}


@shared_task(name="apps.notifications.tasks.send_notification_task", bind=True, max_retries=3, default_retry_delay=60)
def send_notification_task(self, notification_id: str) -> None:
    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.warning("send_notification_task: Notification %s no longer exists", notification_id)
        return

    if notification.status in _TERMINAL_STATUSES:
        return  # already delivered/read/cancelled — idempotency guard against duplicate enqueues

    attempt_number = notification.delivery_attempts.count() + 1
    started_at = timezone.now()

    try:
        _dispatch(notification)
    except Exception as exc:  # noqa: BLE001 — deliberately broad: any provider failure must be recorded, not crash the worker
        duration_ms = int((timezone.now() - started_at).total_seconds() * 1000)
        error_message = str(exc)[:2000]

        notification.status = NotificationStatus.FAILED
        notification.failed_reason = error_message
        notification.retry_count += 1
        notification.save(update_fields=["status", "failed_reason", "retry_count", "updated_at"])

        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            attempt_number=attempt_number,
            provider_name=_provider_name(notification.channel),
            status=NotificationStatus.FAILED,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        logger.error("send_notification_task: failed to send %s — %s", notification.id, error_message)

        if notification.retry_count < notification.max_retries and notification.channel == NotificationChannel.EMAIL:
            raise self.retry(exc=exc)
        return

    duration_ms = int((timezone.now() - started_at).total_seconds() * 1000)

    notification.status = NotificationStatus.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=["status", "sent_at", "updated_at"])

    NotificationDeliveryAttempt.objects.create(
        notification=notification,
        attempt_number=attempt_number,
        provider_name=_provider_name(notification.channel),
        status=NotificationStatus.SENT,
        duration_ms=duration_ms,
    )


def _provider_name(channel: str) -> str:
    return {
        NotificationChannel.EMAIL: "smtp",
        NotificationChannel.SMS: "unconfigured",
        NotificationChannel.WHATSAPP: "unconfigured",
        NotificationChannel.SLACK: "unconfigured",
        NotificationChannel.IN_APP: "in_app",
    }.get(channel, "unknown")


def _get_smtp_connection_and_from_email(notification: Notification):
    """
    Build an SMTP connection for the notification. Looks up the linked
    ThirdPartyIntegration via NotificationProviderConfig, or falls back
    to Django's default settings.

    Returns (connection, from_email) tuple to avoid querying twice.
    """
    from django.core.mail import get_connection

    # Try to find a linked integration via provider config (single query)
    provider_config = NotificationProviderConfig.objects.filter(
        channel=NotificationChannel.EMAIL,
        is_active=True,
    ).select_related("integration").first()

    integration = None
    if provider_config and provider_config.integration_id:
        integration = provider_config.integration
    else:
        # Fall back to default SMTP integration
        integration = ThirdPartyIntegration.objects.filter(
            provider_type=ThirdPartyIntegration.ProviderType.SMTP,
            is_active=True,
            is_default_for_type=True,
        ).first()

    if integration is None:
        # Use Django's default SMTP settings
        return get_connection(), settings.DEFAULT_FROM_EMAIL

    creds = integration.credentials or {}
    connection = get_connection(
        host=creds.get("host", settings.EMAIL_HOST),
        port=int(creds.get("port", settings.EMAIL_PORT)),
        use_tls=creds.get("use_tls", settings.EMAIL_USE_TLS),
        username=creds.get("username", settings.EMAIL_HOST_USER),
        password=creds.get("password", settings.EMAIL_HOST_PASSWORD),
    )
    from_email = creds.get("from_email", settings.DEFAULT_FROM_EMAIL)
    return connection, from_email


def _dispatch(notification: Notification) -> None:
    """Raises on failure; callers handle the exception uniformly."""
    if notification.channel == NotificationChannel.EMAIL:
        if not notification.recipient_email:
            raise ValueError("Notification has no recipient_email")

        connection, from_email = _get_smtp_connection_and_from_email(notification)

        send_mail(
            subject=notification.subject or "(no subject)",
            message=notification.body,
            from_email=from_email,
            recipient_list=[notification.recipient_email],
            connection=connection,
            fail_silently=False,
        )
        return

    if notification.channel == NotificationChannel.IN_APP:
        # In-app notifications don't need external delivery — the row itself
        # IS the notification; the frontend/admin reads Notification directly.
        return

    # SMS / WhatsApp / Slack: no provider wired yet.
    raise NotImplementedError(f"No provider configured for channel '{notification.channel}' yet")


# ──────────────────────────────────────────────────────────────────────────────
# Celery Beat tasks
# ──────────────────────────────────────────────────────────────────────────────


@shared_task(name="apps.notifications.tasks.send_booking_reminder_task")
def send_booking_reminder_task() -> int:
    """
    Hourly Celery beat task: finds bookings in the next 24 hours that
    haven't had a reminder sent yet, and sends reminder emails.
    Returns the number of reminders sent.
    """
    from apps.crm.models import ConsultationBooking
    from .services import notify_user_of_booking_reminder

    now = timezone.now()
    reminder_window_start = now
    reminder_window_end = now + timedelta(hours=24)

    bookings = ConsultationBooking.objects.filter(
        status__in=[
            ConsultationBooking.Status.PENDING,
            ConsultationBooking.Status.CONFIRMED,
        ],
        scheduled_date__gte=reminder_window_start.date(),
        scheduled_date__lte=reminder_window_end.date(),
        reminder_sent_at__isnull=True,
    ).select_related("lead", "user")

    count = 0
    for booking in bookings:
        notification = notify_user_of_booking_reminder(booking)
        if notification:
            booking.reminder_sent_at = timezone.now()
            booking.save(update_fields=["reminder_sent_at", "updated_at"])
            count += 1

    logger.info("send_booking_reminder_task: sent %d reminders", count)
    return count


@shared_task(name="apps.notifications.tasks.send_digest_task")
def send_digest_task(frequency: str = "daily") -> int:
    """
    Celery beat task: sends digest notifications to users who have
    opted in. Run daily for 'daily' digest, weekly for 'weekly'.
    Returns the number of digest emails sent.
    """
    from .services import send_digest_notifications

    notifications = send_digest_notifications(frequency=frequency)
    count = len(notifications)
    logger.info("send_digest_task(%s): sent %d digest emails", frequency, count)
    return count
