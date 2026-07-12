"""
apps/crm/tests/factories.py
────────────────────────────────
"""
from __future__ import annotations

from datetime import time

from apps.crm.models import AvailabilitySlot, ConsultationBooking, Lead, NewsletterSubscriber


def create_lead(**kwargs) -> Lead:
    defaults = dict(
        full_name="Jane Prospect",
        email="jane@example.com",
        lead_type=Lead.LeadType.CONTACT,
        status=Lead.Status.NEW,
    )
    defaults.update(kwargs)
    return Lead.objects.create(**defaults)


def create_availability_slot(**kwargs) -> AvailabilitySlot:
    defaults = dict(
        weekday=0,  # Monday
        start_time=time(9, 0),
        end_time=time(17, 0),
        timezone="UTC",
        max_bookings=2,
        is_active=True,
    )
    defaults.update(kwargs)
    return AvailabilitySlot.objects.create(**defaults)


def create_consultation_booking(*, lead=None, slot=None, **kwargs) -> ConsultationBooking:
    lead = lead or create_lead(lead_type=Lead.LeadType.CONSULTATION)
    slot = slot or create_availability_slot()
    defaults = dict(
        lead=lead,
        slot=slot,
        scheduled_date=kwargs.pop("scheduled_date", None),
        scheduled_time=kwargs.pop("scheduled_time", time(10, 0)),
        status=ConsultationBooking.Status.PENDING,
    )
    defaults.update(kwargs)
    return ConsultationBooking.objects.create(**defaults)


def create_newsletter_subscriber(**kwargs) -> NewsletterSubscriber:
    defaults = dict(email="subscriber@example.com", is_active=True)
    defaults.update(kwargs)
    return NewsletterSubscriber.objects.create(**defaults)
