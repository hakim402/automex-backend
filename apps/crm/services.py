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
- capture_ai_assistant_lead()   → Lead(type=ai_assistant)
- create_support_ticket()       → SupportTicket (+ optional guest token)
- add_ticket_message()          → SupportTicketMessage
- get_user_dashboard_summary()  → aggregated stats for user dashboard
- convert_estimate_to_lead()    → CalculatorSubmission → Lead conversion
"""
from __future__ import annotations

import logging
import secrets

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.notifications.services import notify_admins_of_new_lead

from .models import (
    AvailabilitySlot,
    CalculatorSubmission,
    ConsultationBooking,
    Lead,
    LeadActivity,
    NewsletterSubscriber,
    QuoteRequestDetail,
    SupportTicket,
    SupportTicketMessage,
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


def _log_activity(lead: Lead, activity_type: str, description: str, **kwargs) -> None:
    LeadActivity.objects.create(
        lead=lead, activity_type=activity_type, description=description, **kwargs,
    )


def _notify(lead: Lead) -> None:
    try:
        notify_admins_of_new_lead(lead)
    except Exception:  # noqa: BLE001 — a notification failure must never fail the user-facing request
        logger.exception("Failed to enqueue admin notification for lead %s", lead.id)


def _notify_user_request_submitted(lead: Lead) -> None:
    """Send confirmation email to the user/guest after request submission."""
    try:
        from apps.notifications.services import notify_user_of_request_submitted
        notify_user_of_request_submitted(lead)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send request-submitted notification for lead %s", lead.id)


def _generate_unique_slug(base: str, model_class, field: str = "slug") -> str:
    """Generate a unique slug for the given model class."""
    slug = slugify(base)[:250]
    if not slug:
        slug = "item"
    candidate = slug
    counter = 1
    while model_class.objects.filter(**{field: candidate}).exists():
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


# ──────────────────────────────────────────────────────────────────────────────
# CONTACT FORM
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def capture_contact_lead(*, request, validated_data: dict, user=None) -> Lead:
    lead = Lead.objects.create(
        lead_type=Lead.LeadType.CONTACT,
        status=Lead.Status.NEW,
        user=user,
        **validated_data,
        **_client_meta(request),
    )
    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via contact form.")
    _notify(lead)
    _notify_user_request_submitted(lead)
    return lead


# ──────────────────────────────────────────────────────────────────────────────
# QUOTE REQUEST
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def capture_quote_lead(*, request, validated_data: dict, user=None) -> Lead:
    requested_services = validated_data.pop("requested_services", [])
    quote_fields = {
        key: validated_data.pop(key)
        for key in ("project_description", "estimated_budget_min", "estimated_budget_max", "currency")
        if key in validated_data
    }

    lead = Lead.objects.create(
        lead_type=Lead.LeadType.QUOTE,
        status=Lead.Status.NEW,
        user=user,
        **validated_data,
        **_client_meta(request),
    )
    detail = QuoteRequestDetail.objects.create(lead=lead, **quote_fields)
    if requested_services:
        detail.requested_services.set(requested_services)

    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via quote request.")
    _notify(lead)
    _notify_user_request_submitted(lead)
    return lead


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTATION BOOKING
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def book_consultation(*, request, validated_data: dict, user=None) -> ConsultationBooking:
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
        user=user,
        **lead_data,
        **_client_meta(request),
    )

    booking = ConsultationBooking.objects.create(
        lead=lead,
        user=user,
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
    _notify_user_request_submitted(lead)
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
    user=None,
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
        user=user,
        **_client_meta(request),
    )
    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via AI Sales Assistant conversation.")
    _notify(lead)
    _notify_user_request_submitted(lead)
    return lead


# ──────────────────────────────────────────────────────────────────────────────
# NEWSLETTER
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def subscribe_newsletter(*, request, validated_data: dict, user=None) -> NewsletterSubscriber:
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
            user=user,
            **_client_meta(request),
        )
        _log_activity(lead, LeadActivity.ActivityType.OTHER, "Subscribed to the newsletter.")
        _notify(lead)

    return subscriber


# ──────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKETS
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def create_support_ticket(
    *,
    title: str,
    description: str,
    ticket_type: str,
    user=None,
    guest_email: str = "",
    priority: str = SupportTicket.Priority.NORMAL,
    related_lead=None,
    related_service=None,
) -> SupportTicket:
    """Create a support ticket for an authenticated user or a guest."""
    slug = _generate_unique_slug(title, SupportTicket)
    ticket = SupportTicket.objects.create(
        title=title,
        slug=slug,
        description=description,
        ticket_type=ticket_type,
        priority=priority,
        user=user,
        guest_email=guest_email,
        related_lead=related_lead,
        related_service=related_service,
    )

    # Trigger admin notification for new tickets
    try:
        from apps.notifications.services import notify_admins_of_new_ticket
        notify_admins_of_new_ticket(ticket)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to notify admins of new ticket %s", ticket.id)

    return ticket


@transaction.atomic
def add_ticket_message(
    *,
    ticket: SupportTicket,
    body: str,
    author_user=None,
    author_name: str = "",
    author_is_staff: bool = False,
    attachment=None,
) -> SupportTicketMessage:
    """Add a message to a support ticket thread."""
    message = SupportTicketMessage.objects.create(
        ticket=ticket,
        body=body,
        author_user=author_user,
        author_name=author_name or (str(author_user) if author_user else ""),
        author_is_staff=author_is_staff,
        attachment=attachment,
    )

    # Trigger notification for ticket message
    try:
        from apps.notifications.services import notify_user_of_ticket_update
        notify_user_of_ticket_update(ticket, message=message)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send ticket message notification for ticket %s", ticket.id)

    return message


# ──────────────────────────────────────────────────────────────────────────────
# USER DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────


def get_user_dashboard_summary(user) -> dict:
    """Return aggregated stats for the authenticated user's dashboard."""
    leads = Lead.objects.filter(user=user)
    return {
        "total_requests": leads.count(),
        "active_requests": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST, Lead.Status.SPAM]).count(),
        "total_bookings": ConsultationBooking.objects.filter(user=user).count(),
        "upcoming_bookings": ConsultationBooking.objects.filter(
            user=user,
            status__in=[ConsultationBooking.Status.PENDING, ConsultationBooking.Status.CONFIRMED],
            scheduled_date__gte=timezone.localdate(),
        ).count(),
        "total_tickets": SupportTicket.objects.filter(user=user).count(),
        "open_tickets": SupportTicket.objects.filter(
            user=user,
        ).exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]).count(),
        "total_calculations": CalculatorSubmission.objects.filter(user=user).count(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# ESTIMATE → LEAD CONVERSION
# ──────────────────────────────────────────────────────────────────────────────


@transaction.atomic
def convert_estimate_to_lead(*, submission: CalculatorSubmission, user=None) -> Lead:
    """Convert a CalculatorSubmission into a qualified Lead."""
    if submission.converted_to_lead:
        raise ValidationError("This estimate has already been converted to a lead.")

    lead = Lead.objects.create(
        lead_type=Lead.LeadType.QUOTE,
        status=Lead.Status.NEW,
        full_name=submission.lead.full_name if submission.lead else (str(user) if user else "Estimate User"),
        email=submission.lead.email if submission.lead else (user.email if user else ""),
        phone=submission.lead.phone if submission.lead else "",
        company=submission.lead.company if submission.lead else "",
        message=f"Converted from cost calculator estimate. "
                f"Estimated price: {submission.estimated_price_min}-{submission.estimated_price_max} {submission.currency}.",
        service_interest=submission.selected_service,
        user=user or (submission.lead.user if submission.lead else None),
    )

    QuoteRequestDetail.objects.create(
        lead=lead,
        project_description=f"Auto-generated from calculator submission {submission.id}.",
        estimated_budget_min=submission.estimated_price_min,
        estimated_budget_max=submission.estimated_price_max,
        currency=submission.currency,
    )

    submission.converted_to_lead = True
    submission.converted_lead = lead
    submission.save(update_fields=["converted_to_lead", "converted_lead", "updated_at"])

    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Converted from cost calculator estimate.")
    _notify(lead)
    return lead
