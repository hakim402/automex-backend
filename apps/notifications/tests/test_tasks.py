from __future__ import annotations

import pytest
from django.core import mail

from apps.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationDeliveryAttempt,
    NotificationEventType,
    NotificationStatus,
)
from apps.notifications.services import notify
from apps.notifications.tasks import send_notification_task

pytestmark = pytest.mark.django_db


def test_notify_creates_pending_notification_and_sends_via_eager_celery():
    notification = notify(
        event_type=NotificationEventType.LEAD_CREATED,
        channel=NotificationChannel.EMAIL,
        recipient_email="admin@example.com",
        subject="Test subject",
        body="Test body",
    )

    notification.refresh_from_db()
    # CELERY_TASK_ALWAYS_EAGER=True in settings_test means .delay() already ran synchronously.
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin@example.com"]
    assert mail.outbox[0].subject == "Test subject"


def test_notify_creates_delivery_attempt_record():
    notification = notify(
        event_type=NotificationEventType.LEAD_CREATED,
        recipient_email="admin@example.com",
        subject="S", body="B",
    )
    attempt = NotificationDeliveryAttempt.objects.get(notification=notification)
    assert attempt.status == NotificationStatus.SENT
    assert attempt.provider_name == "smtp"


def test_send_notification_task_fails_gracefully_for_unimplemented_channel():
    notification = Notification.objects.create(
        event_type=NotificationEventType.LEAD_CREATED,
        channel=NotificationChannel.SLACK,
        recipient_email="",
        subject="S", body="B",
        status=NotificationStatus.PENDING,
    )

    # Non-EMAIL channels intentionally don't retry (no provider configured
    # yet), so this returns normally rather than raising — it just marks
    # the notification FAILED with a clear reason instead of crashing.
    send_notification_task(str(notification.id))

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.FAILED
    assert "not implemented" in notification.failed_reason.lower() or "no provider" in notification.failed_reason.lower()


def test_send_notification_task_is_idempotent_for_already_sent_notification():
    notification = notify(
        event_type=NotificationEventType.LEAD_CREATED,
        recipient_email="admin@example.com",
        subject="S", body="B",
    )
    assert len(mail.outbox) == 1

    # Re-running the task for an already-SENT notification must not resend.
    send_notification_task(str(notification.id))
    assert len(mail.outbox) == 1


def test_send_notification_task_handles_missing_notification_gracefully():
    import uuid
    # Must not raise even if the row no longer exists.
    send_notification_task(str(uuid.uuid4()))


def test_notify_uses_active_template_when_available():
    from apps.notifications.models import NotificationTemplate

    NotificationTemplate.objects.create(
        key="lead_created.email.en",
        event_type=NotificationEventType.LEAD_CREATED,
        channel=NotificationChannel.EMAIL,
        language="en",
        subject="New lead: {full_name}",
        body="{full_name} <{email}> just reached out.",
        is_active=True,
    )

    notification = notify(
        event_type=NotificationEventType.LEAD_CREATED,
        recipient_email="admin@example.com",
        subject="fallback subject",
        body="fallback body",
        context={"full_name": "Jane Doe", "email": "jane@example.com"},
        language="en",
    )

    assert notification.subject == "New lead: Jane Doe"
    assert "Jane Doe <jane@example.com>" in notification.body
