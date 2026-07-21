"""
apps/crm/models/tickets.py
──────────────────────────────
Support / request tickets — persistent conversation threads between
customers (authenticated users or guests) and the sales/support team.
Every ticket can be linked to a Lead and/or Service for pipeline context.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, UUIDModel

from .leads import _generate_guest_token


class SupportTicket(UUIDModel, TimeStampedModel):
    class TicketType(models.TextChoices):
        GENERAL_INQUIRY  = "general_inquiry",  _("General Inquiry")
        TECHNICAL_SUPPORT = "technical_support", _("Technical Support")
        PROJECT_REQUEST  = "project_request",  _("Project Request")
        BUG_REPORT       = "bug_report",       _("Bug Report")
        FEEDBACK         = "feedback",         _("Feedback")
        PARTNERSHIP      = "partnership",      _("Partnership")

    class Status(models.TextChoices):
        OPEN             = "open",             _("Open")
        IN_PROGRESS      = "in_progress",      _("In Progress")
        WAITING_CUSTOMER = "waiting_customer", _("Waiting on Customer")
        WAITING_ADMIN    = "waiting_admin",    _("Waiting on Admin")
        RESOLVED         = "resolved",         _("Resolved")
        CLOSED           = "closed",           _("Closed")

    class Priority(models.TextChoices):
        LOW     = "low",     _("Low")
        NORMAL  = "normal",  _("Normal")
        HIGH    = "high",    _("High")
        URGENT  = "urgent",  _("Urgent")

    # ── Identity ─────────────────────────────────────────────────────────
    title = models.CharField(_("title"), max_length=250)
    slug = models.SlugField(_("slug"), max_length=270, unique=True)
    description = models.TextField(_("description"))

    # ── Ownership (authenticated user OR guest) ──────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="support_tickets", verbose_name=_("owner"),
    )
    guest_email = models.EmailField(_("guest email"), blank=True)
    guest_token = models.CharField(
        _("guest tracking token"), max_length=64, unique=True,
        null=True, blank=True, db_index=True,
    )

    # ── Classification ───────────────────────────────────────────────────
    ticket_type = models.CharField(
        _("ticket type"), max_length=25, choices=TicketType.choices, db_index=True,
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True,
    )
    priority = models.CharField(
        _("priority"), max_length=10, choices=Priority.choices, default=Priority.NORMAL, db_index=True,
    )

    # ── Assignment ───────────────────────────────────────────────────────
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_tickets", verbose_name=_("assigned to"),
    )

    # ── Relations ────────────────────────────────────────────────────────
    related_lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="support_tickets", verbose_name=_("related lead"),
    )
    related_service = models.ForeignKey(
        "content.Service",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="support_tickets", verbose_name=_("related service"),
    )

    # ── Resolution ───────────────────────────────────────────────────────
    resolution_summary = models.TextField(_("resolution summary"), blank=True)
    resolved_at = models.DateTimeField(_("resolved at"), null=True, blank=True)
    closed_at = models.DateTimeField(_("closed at"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("support ticket")
        verbose_name_plural = _("support tickets")
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_ticket_status_created"),
            models.Index(fields=["user", "status"], name="idx_ticket_user_status"),
            models.Index(fields=["assigned_to", "status"], name="idx_ticket_assigned_status"),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.guest_token and not self.user_id:
            self.guest_token = _generate_guest_token()
        super().save(*args, **kwargs)


class SupportTicketMessage(UUIDModel, TimeStampedModel):
    """Threaded message within a support ticket."""

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="messages", verbose_name=_("ticket"),
    )

    # ── Author ───────────────────────────────────────────────────────────
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ticket_messages", verbose_name=_("author"),
    )
    author_name = models.CharField(_("author name"), max_length=200, blank=True)
    author_is_staff = models.BooleanField(_("staff message"), default=False)

    # ── Content ──────────────────────────────────────────────────────────
    body = models.TextField(_("message"))
    attachment = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("attachment"),
    )

    # ── Read tracking ────────────────────────────────────────────────────
    is_read = models.BooleanField(_("read"), default=False, db_index=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("ticket message")
        verbose_name_plural = _("ticket messages")
        indexes = [
            models.Index(fields=["ticket", "created_at"], name="idx_ticketmsg_ticket_created"),
        ]

    def __str__(self) -> str:
        author = self.author_name or (str(self.author_user) if self.author_user_id else "Unknown")
        return f"Message by {author} on '{self.ticket}'"
