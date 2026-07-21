"""
apps/crm/models/booking.py
────────────────────────────
Appointment/consultation booking, central to the "Book Free Consultation"
CTA used throughout the hero, service pages, and final CTA sections.
Every booking is attached to a Lead so the sales pipeline stays unified
regardless of entry channel.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, UUIDModel

from .leads import Lead


class AvailabilitySlot(UUIDModel, TimeStampedModel):
    """Recurring weekly availability window used to build the public booking calendar."""

    class Weekday(models.IntegerChoices):
        MONDAY    = 0, _("Monday")
        TUESDAY   = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY  = 3, _("Thursday")
        FRIDAY    = 4, _("Friday")
        SATURDAY  = 5, _("Saturday")
        SUNDAY    = 6, _("Sunday")

    weekday      = models.PositiveSmallIntegerField(_("weekday"), choices=Weekday.choices)
    start_time   = models.TimeField(_("start time"))
    end_time     = models.TimeField(_("end time"))
    timezone     = models.CharField(_("timezone"), max_length=64, default="UTC")
    max_bookings = models.PositiveSmallIntegerField(_("max bookings per slot"), default=1)
    is_active    = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering            = ["weekday", "start_time"]
        verbose_name        = _("availability slot")
        verbose_name_plural = _("availability slots")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")), name="chk_slot_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_weekday_display()} {self.start_time}–{self.end_time}"


class ConsultationBooking(UUIDModel, TimeStampedModel):
    class MeetingType(models.TextChoices):
        VIDEO     = "video",     _("Video Call")
        PHONE     = "phone",     _("Phone Call")
        IN_PERSON = "in_person", _("In Person")

    class Status(models.TextChoices):
        PENDING     = "pending",     _("Pending Confirmation")
        CONFIRMED   = "confirmed",   _("Confirmed")
        RESCHEDULED = "rescheduled", _("Rescheduled")
        COMPLETED   = "completed",   _("Completed")
        CANCELLED   = "cancelled",   _("Cancelled")
        NO_SHOW     = "no_show",     _("No Show")

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name="consultation_bookings", verbose_name=_("lead"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consultation_bookings", verbose_name=_("linked user"),
    )
    slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bookings", verbose_name=_("availability slot"),
    )

    scheduled_date = models.DateField(_("scheduled date"))
    scheduled_time = models.TimeField(_("scheduled time"))
    timezone       = models.CharField(_("timezone"), max_length=64, default="UTC")
    meeting_type   = models.CharField(
        _("meeting type"), max_length=20, choices=MeetingType.choices, default=MeetingType.VIDEO,
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True,
    )

    calendar_provider = models.CharField(
        _("calendar provider"), max_length=50, blank=True,
        help_text=_("e.g. 'google_calendar', 'calendly'."),
    )
    calendar_event_id   = models.CharField(_("calendar event id"), max_length=255, blank=True)
    calendar_event_link = models.URLField(_("calendar event link"), blank=True)

    notes               = models.TextField(_("internal notes"), blank=True)
    cancellation_reason = models.CharField(_("cancellation reason"), max_length=255, blank=True)

    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    # ── Enterprise fields ────────────────────────────────────────────────
    reschedule_count = models.PositiveIntegerField(_("reschedule count"), default=0)
    rescheduled_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reschedule_chain", verbose_name=_("rescheduled from"),
    )
    meeting_link = models.URLField(_("meeting link"), blank=True)
    reminder_sent_at = models.DateTimeField(_("reminder sent at"), null=True, blank=True)

    class Meta:
        ordering            = ["-scheduled_date", "-scheduled_time"]
        verbose_name        = _("consultation booking")
        verbose_name_plural = _("consultation bookings")
        indexes = [
            models.Index(fields=["scheduled_date", "status"], name="idx_booking_date_status"),
            models.Index(fields=["lead"], name="idx_booking_lead"),
        ]

    def __str__(self) -> str:
        return f"Consultation with {self.lead.full_name} on {self.scheduled_date}"
