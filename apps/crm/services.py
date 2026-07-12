"""
apps/crm/services.py
────────────────────────
CrmService — all lead-capture business logic. Keeps views thin; every
public method creates the right records, logs a LeadActivity, and fires
an admin notification. Mirrors the apps.accounts.services.AuthService
convention already established in this project.

Covers
------
- capture_contact_lead()        → Lead(type=contact)
- capture_quote_lead()          → Lead(type=quote) + QuoteRequestDetail
- book_consultation()           → Lead(type=consultation) + ConsultationBooking,
                                   validated against AvailabilitySlot capacity
- subscribe_newsletter()        → NewsletterSubscriber (+ Lead(type=newsletter)
                                   on first-time subscribe only)
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.notifications.services import notify_admins_of_new_lead

from .models import (
    AvailabilitySlot,
    ConsultationBooking,
    Lead,
    LeadActivity,
    NewsletterSubscriber,
    QuoteRequestDetail,
)

logger = logging.getLogger("apps.crm")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _client_meta(request) -> dict:
    """Server-side-captured attribution — never trust these from the request body."""
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    return {
        "ip_address": ip_address or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:1000],
        "referrer_url": request.META.get("HTTP_REFERER", "")[:500],
    }


def _log_activity(lead: Lead, activity_type: str, description: str) -> None:
    LeadActivity.objects.create(lead=lead, activity_type=activity_type, description=description)


def _notify(lead: Lead) -> None:
    try:
        notify_admins_of_new_lead(lead)
    except Exception:  # noqa: BLE001 — a notification failure must never fail the user-facing request
        logger.exception("Failed to enqueue admin notification for lead %s", lead.id)


# ──────────────────────────────────────────────────────────────────────────────
# CONTACT FORM
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def capture_contact_lead(*, request, validated_data: dict) -> Lead:
    lead = Lead.objects.create(
        lead_type=Lead.LeadType.CONTACT,
        status=Lead.Status.NEW,
        **validated_data,
        **_client_meta(request),
    )
    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via contact form.")
    _notify(lead)
    return lead


# ──────────────────────────────────────────────────────────────────────────────
# QUOTE REQUEST
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def capture_quote_lead(*, request, validated_data: dict) -> Lead:
    requested_services = validated_data.pop("requested_services", [])
    quote_fields = {
        key: validated_data.pop(key)
        for key in ("project_description", "estimated_budget_min", "estimated_budget_max", "currency")
        if key in validated_data
    }

    lead = Lead.objects.create(
        lead_type=Lead.LeadType.QUOTE,
        status=Lead.Status.NEW,
        **validated_data,
        **_client_meta(request),
    )
    detail = QuoteRequestDetail.objects.create(lead=lead, **quote_fields)
    if requested_services:
        detail.requested_services.set(requested_services)

    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via quote request.")
    _notify(lead)
    return lead


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTATION BOOKING
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def book_consultation(*, request, validated_data: dict) -> ConsultationBooking:
    slot: AvailabilitySlot = validated_data.pop("slot")
    scheduled_date = validated_data.pop("scheduled_date")
    scheduled_time = validated_data.pop("scheduled_time")
    meeting_type = validated_data.pop("meeting_type", ConsultationBooking.MeetingType.VIDEO)
    booking_timezone = validated_data.pop("timezone", slot.timezone)
    notes = validated_data.pop("notes", "")

    if scheduled_date < timezone.localdate():
        raise ValidationError({"scheduled_date": "Cannot book a consultation in the past."})

    if scheduled_date.weekday() != slot.weekday:
        raise ValidationError({"slot": "The selected slot does not match the requested date's weekday."})

    if not (slot.start_time <= scheduled_time < slot.end_time):
        raise ValidationError({"scheduled_time": "The selected time falls outside the chosen slot's window."})

    # Lock existing bookings for this slot+date to prevent a race between
    # two concurrent requests both seeing capacity available.
    existing_count = (
        ConsultationBooking.objects.select_for_update()
        .filter(
            slot=slot,
            scheduled_date=scheduled_date,
            status__in=[ConsultationBooking.Status.PENDING, ConsultationBooking.Status.CONFIRMED],
        )
        .count()
    )
    if existing_count >= slot.max_bookings:
        raise ValidationError({"slot": "This slot is fully booked for the selected date. Please choose another."})

    lead_data = validated_data  # whatever remains are Lead fields
    lead = Lead.objects.create(
        lead_type=Lead.LeadType.CONSULTATION,
        status=Lead.Status.NEW,
        **lead_data,
        **_client_meta(request),
    )

    booking = ConsultationBooking.objects.create(
        lead=lead,
        slot=slot,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        timezone=booking_timezone,
        meeting_type=meeting_type,
        notes=notes,
        status=ConsultationBooking.Status.PENDING,
    )

    _log_activity(lead, LeadActivity.ActivityType.OTHER, f"Consultation requested for {scheduled_date} {scheduled_time}.")
    _notify(lead)
    return booking


def available_slots_for_date(target_date) -> list[dict]:
    """
    Returns each active AvailabilitySlot matching target_date's weekday,
    with remaining capacity for that specific date.
    """
    weekday = target_date.weekday()
    slots = AvailabilitySlot.objects.filter(weekday=weekday, is_active=True).order_by("start_time")

    results = []
    for slot in slots:
        booked_count = ConsultationBooking.objects.filter(
            slot=slot,
            scheduled_date=target_date,
            status__in=[ConsultationBooking.Status.PENDING, ConsultationBooking.Status.CONFIRMED],
        ).count()
        results.append({
            "slot": slot,
            "remaining_capacity": max(slot.max_bookings - booked_count, 0),
        })
    return results


@transaction.atomic
def capture_ai_assistant_lead(
    *,
    request,
    email: str,
    full_name: str = "",
    phone: str = "",
    company: str = "",
    message: str = "",
    service_interest=None,
) -> Lead:
    """
    Called by apps.assistant when the deterministic email/phone extractor
    finds a real contact detail mid-conversation. `service_interest`, if
    provided, must already be a resolved Service instance (or None) —
    the assistant does best-effort name matching before calling this.
    """
    lead = Lead.objects.create(
        lead_type=Lead.LeadType.AI_ASSISTANT,
        status=Lead.Status.NEW,
        full_name=full_name or email.split("@")[0],
        email=email,
        phone=phone,
        company=company,
        message=message,
        service_interest=service_interest,
        **_client_meta(request),
    )
    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via AI Sales Assistant conversation.")
    _notify(lead)
    return lead


# ──────────────────────────────────────────────────────────────────────────────
# NEWSLETTER
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def subscribe_newsletter(*, request, validated_data: dict) -> NewsletterSubscriber:
    email = validated_data["email"]
    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={
            "language": validated_data.get("language", "en"),
            "source": validated_data.get("source", ""),
        },
    )

    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.unsubscribed_at = None
        subscriber.save(update_fields=["is_active", "unsubscribed_at"])

    if created:
        lead = Lead.objects.create(
            lead_type=Lead.LeadType.NEWSLETTER,
            status=Lead.Status.NEW,
            full_name=email.split("@")[0],
            email=email,
            source_page=validated_data.get("source", ""),
            language=validated_data.get("language", "en"),
            **_client_meta(request),
        )
        _log_activity(lead, LeadActivity.ActivityType.OTHER, "Subscribed to the newsletter.")
        _notify(lead)

    return subscriber
