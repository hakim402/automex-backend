"""
apps/notifications/tasks.py
────────────────────────────────
Delivers a single Notification. Only EMAIL is wired to a real provider
(Gmail SMTP via Django's send_mail, already configured in settings) —
SMS/WhatsApp/Slack record the attempt and fail clearly rather than
pretending to succeed, so nothing silently vanishes once those providers
are added later.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import (
    Notification,
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationStatus,
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


def _dispatch(notification: Notification) -> None:
    """Raises on failure; callers handle the exception uniformly."""
    if notification.channel == NotificationChannel.EMAIL:
        if not notification.recipient_email:
            raise ValueError("Notification has no recipient_email")
        send_mail(
            subject=notification.subject or "(no subject)",
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient_email],
            fail_silently=False,
        )
        return

    if notification.channel == NotificationChannel.IN_APP:
        # In-app notifications don't need external delivery — the row itself
        # IS the notification; the frontend/admin reads Notification directly.
        return

    # SMS / WhatsApp / Slack: no provider wired yet.
    raise NotImplementedError(f"No provider configured for channel '{notification.channel}' yet")
