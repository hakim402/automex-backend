from __future__ import annotations

from datetime import date, time, timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.crm import services
from apps.crm.models import ConsultationBooking, Lead, NewsletterSubscriber
from apps.notifications.models import Notification

from .factories import create_availability_slot, create_lead

pytestmark = pytest.mark.django_db

rf = RequestFactory()


def _next_weekday(weekday: int) -> date:
    today = timezone.localdate()
    days_ahead = (weekday - today.weekday()) % 7
    days_ahead = days_ahead or 7  # always return a future date, never today
    return today + timedelta(days=days_ahead)


# ──────────────────────────────────────────────────────────────────────────────
# capture_contact_lead
# ──────────────────────────────────────────────────────────────────────────────

def test_capture_contact_lead_creates_lead_and_logs_activity():
    request = rf.post("/api/v1/crm/leads/contact/", HTTP_USER_AGENT="pytest-agent", REMOTE_ADDR="1.2.3.4")
    lead = services.capture_contact_lead(
        request=request,
        validated_data={"full_name": "Jane Prospect", "email": "jane@example.com"},
    )

    assert lead.lead_type == Lead.LeadType.CONTACT
    assert lead.status == Lead.Status.NEW
    assert lead.ip_address == "1.2.3.4"
    assert lead.user_agent == "pytest-agent"
    assert lead.activities.count() == 1


def test_capture_contact_lead_enqueues_admin_notification():
    request = rf.post("/api/v1/crm/leads/contact/")
    lead = services.capture_contact_lead(
        request=request,
        validated_data={"full_name": "Jane Prospect", "email": "jane@example.com"},
    )

    assert Notification.objects.filter(object_id=lead.id).exists()
    assert len(mail.outbox) == len(settings.ADMIN_NOTIFICATION_EMAILS)
    assert "Jane Prospect" in mail.outbox[0].subject or "Contact" in mail.outbox[0].subject


# ──────────────────────────────────────────────────────────────────────────────
# capture_quote_lead
# ──────────────────────────────────────────────────────────────────────────────

def test_capture_quote_lead_creates_lead_and_quote_detail():
    request = rf.post("/api/v1/crm/leads/quote/")
    lead = services.capture_quote_lead(
        request=request,
        validated_data={
            "full_name": "Quote Requester",
            "email": "quote@example.com",
            "project_description": "Need an MVP built.",
            "estimated_budget_min": 10000,
            "estimated_budget_max": 50000,
            "currency": "USD",
        },
    )

    assert lead.lead_type == Lead.LeadType.QUOTE
    assert lead.quote_detail.project_description == "Need an MVP built."
    assert lead.quote_detail.estimated_budget_min == 10000


# ──────────────────────────────────────────────────────────────────────────────
# book_consultation
# ──────────────────────────────────────────────────────────────────────────────

def test_book_consultation_creates_lead_and_booking():
    slot = create_availability_slot(weekday=0, max_bookings=2)  # Monday
    target_date = _next_weekday(0)
    request = rf.post("/api/v1/crm/bookings/consultations/")

    booking = services.book_consultation(
        request=request,
        validated_data={
            "full_name": "Book Requester",
            "email": "book@example.com",
            "slot": slot,
            "scheduled_date": target_date,
            "scheduled_time": time(10, 0),
        },
    )

    assert booking.status == ConsultationBooking.Status.PENDING
    assert booking.lead.lead_type == Lead.LeadType.CONSULTATION


def test_book_consultation_rejects_past_date():
    slot = create_availability_slot(weekday=0)
    request = rf.post("/api/v1/crm/bookings/consultations/")

    with pytest.raises(ValidationError):
        services.book_consultation(
            request=request,
            validated_data={
                "full_name": "X", "email": "x@example.com",
                "slot": slot, "scheduled_date": date(2020, 1, 1), "scheduled_time": time(10, 0),
            },
        )


def test_book_consultation_rejects_weekday_mismatch():
    slot = create_availability_slot(weekday=0)  # Monday
    tuesday = _next_weekday(1)
    request = rf.post("/api/v1/crm/bookings/consultations/")

    with pytest.raises(ValidationError):
        services.book_consultation(
            request=request,
            validated_data={
                "full_name": "X", "email": "x@example.com",
                "slot": slot, "scheduled_date": tuesday, "scheduled_time": time(10, 0),
            },
        )


def test_book_consultation_rejects_time_outside_slot_window():
    slot = create_availability_slot(weekday=0, start_time=time(9, 0), end_time=time(12, 0))
    target_date = _next_weekday(0)
    request = rf.post("/api/v1/crm/bookings/consultations/")

    with pytest.raises(ValidationError):
        services.book_consultation(
            request=request,
            validated_data={
                "full_name": "X", "email": "x@example.com",
                "slot": slot, "scheduled_date": target_date, "scheduled_time": time(14, 0),
            },
        )


def test_book_consultation_rejects_when_slot_fully_booked():
    slot = create_availability_slot(weekday=0, max_bookings=1)
    target_date = _next_weekday(0)
    request = rf.post("/api/v1/crm/bookings/consultations/")

    # Fill the only available spot
    services.book_consultation(
        request=request,
        validated_data={
            "full_name": "First", "email": "first@example.com",
            "slot": slot, "scheduled_date": target_date, "scheduled_time": time(10, 0),
        },
    )

    with pytest.raises(ValidationError):
        services.book_consultation(
            request=request,
            validated_data={
                "full_name": "Second", "email": "second@example.com",
                "slot": slot, "scheduled_date": target_date, "scheduled_time": time(11, 0),
            },
        )


def test_available_slots_for_date_reports_remaining_capacity():
    slot = create_availability_slot(weekday=0, max_bookings=2)
    target_date = _next_weekday(0)
    request = rf.post("/api/v1/crm/bookings/consultations/")

    services.book_consultation(
        request=request,
        validated_data={
            "full_name": "First", "email": "first@example.com",
            "slot": slot, "scheduled_date": target_date, "scheduled_time": time(10, 0),
        },
    )

    results = services.available_slots_for_date(target_date)
    assert len(results) == 1
    assert results[0]["remaining_capacity"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# subscribe_newsletter
# ──────────────────────────────────────────────────────────────────────────────

def test_subscribe_newsletter_creates_subscriber_and_lead_on_first_signup():
    request = rf.post("/api/v1/crm/newsletter/subscribe/")
    subscriber = services.subscribe_newsletter(
        request=request, validated_data={"email": "new@example.com"},
    )

    assert subscriber.is_active is True
    assert Lead.objects.filter(email="new@example.com", lead_type=Lead.LeadType.NEWSLETTER).exists()


def test_subscribe_newsletter_does_not_duplicate_lead_on_resubscribe():
    request = rf.post("/api/v1/crm/newsletter/subscribe/")
    services.subscribe_newsletter(request=request, validated_data={"email": "repeat@example.com"})
    services.subscribe_newsletter(request=request, validated_data={"email": "repeat@example.com"})

    assert Lead.objects.filter(email="repeat@example.com", lead_type=Lead.LeadType.NEWSLETTER).count() == 1
    assert NewsletterSubscriber.objects.filter(email="repeat@example.com").count() == 1


def test_subscribe_newsletter_reactivates_unsubscribed_email():
    request = rf.post("/api/v1/crm/newsletter/subscribe/")
    subscriber = services.subscribe_newsletter(request=request, validated_data={"email": "reactivate@example.com"})
    subscriber.is_active = False
    subscriber.save(update_fields=["is_active"])

    reactivated = services.subscribe_newsletter(request=request, validated_data={"email": "reactivate@example.com"})
    assert reactivated.is_active is True
