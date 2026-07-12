from __future__ import annotations

from datetime import time, timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.content.tests.factories import create_industry, create_service
from apps.core.models import APIKey
from apps.crm.models import ConsultationBooking, Lead, NewsletterSubscriber

from .factories import create_availability_slot

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_with_key() -> APIClient:
    _, raw_key = APIKey.generate(name="test-frontend")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=raw_key)
    return client


def _next_monday():
    today = timezone.localdate()
    days_ahead = (0 - today.weekday()) % 7
    days_ahead = days_ahead or 7
    return today + timedelta(days=days_ahead)


# ──────────────────────────────────────────────────────────────────────────────
# API key enforcement (same posture as the content API)
# ──────────────────────────────────────────────────────────────────────────────

def test_contact_lead_requires_api_key():
    client = APIClient()
    response = client.post("/api/v1/crm/leads/contact/", {"full_name": "X", "email": "x@example.com"})
    assert response.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# CONTACT FORM
# ──────────────────────────────────────────────────────────────────────────────

def test_contact_lead_create_success(client_with_key):
    response = client_with_key.post("/api/v1/crm/leads/contact/", {
        "full_name": "Jane Prospect",
        "email": "jane@example.com",
        "message": "Interested in an MVP build.",
    })

    assert response.status_code == 201
    assert response.data["lead_type"] == "contact"
    assert response.data["status"] == "new"
    assert "score" not in response.data  # internal pipeline field must never leak
    assert Lead.objects.filter(email="jane@example.com").exists()
    assert len(mail.outbox) == len(settings.ADMIN_NOTIFICATION_EMAILS)


def test_contact_lead_rejects_missing_required_fields(client_with_key):
    response = client_with_key.post("/api/v1/crm/leads/contact/", {"message": "no name or email"})
    assert response.status_code == 400
    assert "full_name" in response.data
    assert "email" in response.data


def test_contact_lead_rejects_invalid_email(client_with_key):
    response = client_with_key.post("/api/v1/crm/leads/contact/", {"full_name": "X", "email": "not-an-email"})
    assert response.status_code == 400


def test_contact_lead_captures_service_interest(client_with_key):
    service = create_service(slug="ai-services", name="AI Services")
    response = client_with_key.post("/api/v1/crm/leads/contact/", {
        "full_name": "Jane",
        "email": "jane2@example.com",
        "service_interest": str(service.id),
    })
    assert response.status_code == 201
    lead = Lead.objects.get(email="jane2@example.com")
    assert lead.service_interest_id == service.id


def test_contact_lead_rejects_unpublished_service_interest(client_with_key):
    from apps.core.models import PublishableModel
    draft_service = create_service(slug="draft-service", status=PublishableModel.Status.DRAFT, published=False)

    response = client_with_key.post("/api/v1/crm/leads/contact/", {
        "full_name": "Jane",
        "email": "jane3@example.com",
        "service_interest": str(draft_service.id),
    })
    assert response.status_code == 400


def test_contact_lead_ignores_client_supplied_internal_fields(client_with_key):
    """score/assigned_to/status must never be settable from the public payload."""
    response = client_with_key.post("/api/v1/crm/leads/contact/", {
        "full_name": "Sneaky",
        "email": "sneaky@example.com",
        "score": 999,
        "status": "won",
    })
    assert response.status_code == 201
    lead = Lead.objects.get(email="sneaky@example.com")
    assert lead.score == 0
    assert lead.status == Lead.Status.NEW


# ──────────────────────────────────────────────────────────────────────────────
# QUOTE REQUEST
# ──────────────────────────────────────────────────────────────────────────────

def test_quote_request_create_success(client_with_key):
    service = create_service(slug="custom-dev", name="Custom Development")
    response = client_with_key.post("/api/v1/crm/leads/quote/", {
        "full_name": "Quote Person",
        "email": "quote@example.com",
        "requested_services": [str(service.id)],
        "project_description": "Building an internal tool.",
        "estimated_budget_min": "10000.00",
        "estimated_budget_max": "30000.00",
    }, format="json")

    assert response.status_code == 201
    lead = Lead.objects.get(email="quote@example.com")
    assert lead.lead_type == "quote"
    assert lead.quote_detail.requested_services.count() == 1


def test_quote_request_rejects_max_budget_below_min(client_with_key):
    response = client_with_key.post("/api/v1/crm/leads/quote/", {
        "full_name": "Quote Person",
        "email": "quote2@example.com",
        "estimated_budget_min": "50000.00",
        "estimated_budget_max": "10000.00",
    }, format="json")
    assert response.status_code == 400


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTATION BOOKING
# ──────────────────────────────────────────────────────────────────────────────

def test_availability_endpoint_requires_date_param(client_with_key):
    response = client_with_key.get("/api/v1/crm/bookings/availability/")
    assert response.status_code == 400


def test_availability_endpoint_returns_open_slots(client_with_key):
    create_availability_slot(weekday=0, max_bookings=3)
    target_date = _next_monday()

    response = client_with_key.get(f"/api/v1/crm/bookings/availability/?date={target_date.isoformat()}")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["remaining_capacity"] == 3


def test_consultation_booking_create_success(client_with_key):
    slot = create_availability_slot(weekday=0, start_time=time(9, 0), end_time=time(17, 0), max_bookings=2)
    target_date = _next_monday()

    response = client_with_key.post("/api/v1/crm/bookings/consultations/", {
        "full_name": "Booker",
        "email": "booker@example.com",
        "slot": str(slot.id),
        "scheduled_date": target_date.isoformat(),
        "scheduled_time": "10:00:00",
    }, format="json")

    assert response.status_code == 201
    assert response.data["status"] == "pending"
    assert ConsultationBooking.objects.filter(lead__email="booker@example.com").exists()


def test_consultation_booking_rejects_fully_booked_slot(client_with_key):
    slot = create_availability_slot(weekday=0, max_bookings=1)
    target_date = _next_monday()
    payload = {
        "full_name": "First", "email": "first@example.com",
        "slot": str(slot.id), "scheduled_date": target_date.isoformat(), "scheduled_time": "10:00:00",
    }
    first = client_with_key.post("/api/v1/crm/bookings/consultations/", payload, format="json")
    assert first.status_code == 201

    payload["full_name"], payload["email"] = "Second", "second@example.com"
    second = client_with_key.post("/api/v1/crm/bookings/consultations/", payload, format="json")
    assert second.status_code == 400


# ──────────────────────────────────────────────────────────────────────────────
# NEWSLETTER
# ──────────────────────────────────────────────────────────────────────────────

def test_newsletter_subscribe_success(client_with_key):
    response = client_with_key.post("/api/v1/crm/newsletter/subscribe/", {"email": "sub@example.com"})
    assert response.status_code == 201
    assert NewsletterSubscriber.objects.filter(email="sub@example.com", is_active=True).exists()


def test_newsletter_subscribe_idempotent_on_repeat(client_with_key):
    client_with_key.post("/api/v1/crm/newsletter/subscribe/", {"email": "sub2@example.com"})
    response = client_with_key.post("/api/v1/crm/newsletter/subscribe/", {"email": "sub2@example.com"})
    assert response.status_code == 201
    assert NewsletterSubscriber.objects.filter(email="sub2@example.com").count() == 1
