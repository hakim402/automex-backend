"""
apps/crm/models/leads.py
────────────────────────────
The conversion layer. Every contact form, quote request, consultation
booking (see booking.py), newsletter signup, and AI-assistant capture
(see apps.assistant) funnels into a Lead here, so sales/admin has one
pipeline to work regardless of entry channel.

Design notes
------------
- Lead is NOT a PublishableModel — it has its own sales-pipeline status
  machine (new → contacted → qualified → won/lost), not an editorial one.
- Full UTM + attribution capture is included from day one since lead
  source analysis is one of the MVP's stated Success Metrics.
- QuoteRequestDetail is a 1:1 extension rather than a separate top-level
  model so quote requests stay in the same pipeline/reporting as every
  other lead, while still capturing quote-specific structured data.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, UUIDModel


class Lead(UUIDModel, TimeStampedModel):
    class LeadType(models.TextChoices):
        CONTACT      = "contact",      _("Contact Form")
        QUOTE        = "quote",        _("Quote Request")
        CONSULTATION = "consultation", _("Consultation Booking")
        NEWSLETTER   = "newsletter",   _("Newsletter Signup")
        AI_ASSISTANT = "ai_assistant", _("AI Assistant")
        CAREER       = "career",       _("Careers")

    class Status(models.TextChoices):
        NEW           = "new",           _("New")
        CONTACTED     = "contacted",     _("Contacted")
        QUALIFIED     = "qualified",     _("Qualified")
        PROPOSAL_SENT = "proposal_sent", _("Proposal Sent")
        NEGOTIATION   = "negotiation",   _("Negotiation")
        WON           = "won",           _("Won")
        LOST          = "lost",          _("Lost")
        SPAM          = "spam",          _("Spam")

    class BudgetRange(models.TextChoices):
        UNDER_10K     = "under_10k",     _("Under $10,000")
        R10K_50K      = "10k_50k",       _("$10,000 – $50,000")
        R50K_150K     = "50k_150k",      _("$50,000 – $150,000")
        R150K_PLUS    = "150k_plus",     _("$150,000+")
        NOT_SPECIFIED = "not_specified", _("Not Specified")

    class Timeline(models.TextChoices):
        ASAP            = "asap",            _("ASAP")
        WITHIN_1_MONTH  = "within_1_month",  _("Within 1 month")
        WITHIN_3_MONTHS = "within_3_months", _("Within 3 months")
        WITHIN_6_MONTHS = "within_6_months", _("Within 6 months")
        FLEXIBLE        = "flexible",         _("Flexible")

    # ── Contact info ─────────────────────────────────────────────────────
    full_name = models.CharField(_("full name"), max_length=200)
    email     = models.EmailField(_("email"), db_index=True)
    phone     = models.CharField(_("phone"), max_length=30, blank=True)
    company   = models.CharField(_("company"), max_length=200, blank=True)
    job_title = models.CharField(_("job title"), max_length=150, blank=True)
    message   = models.TextField(_("message"), blank=True)

    # ── Classification ───────────────────────────────────────────────────
    lead_type = models.CharField(_("lead type"), max_length=20, choices=LeadType.choices, db_index=True)
    status    = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True,
    )

    service_interest = models.ForeignKey(
        "content.Service",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leads", verbose_name=_("service of interest"),
    )
    industry = models.ForeignKey(
        "content.Industry",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leads", verbose_name=_("industry"),
    )
    budget_range = models.CharField(
        _("budget range"), max_length=20, choices=BudgetRange.choices, default=BudgetRange.NOT_SPECIFIED,
    )
    timeline = models.CharField(_("project timeline"), max_length=20, choices=Timeline.choices, blank=True)

    # ── Attribution ───────────────────────────────────────────────────────
    source_page  = models.CharField(_("source page URL"), max_length=500, blank=True)
    referrer_url = models.CharField(_("referrer URL"), max_length=500, blank=True)
    utm_source   = models.CharField(_("UTM source"), max_length=150, blank=True)
    utm_medium   = models.CharField(_("UTM medium"), max_length=150, blank=True)
    utm_campaign = models.CharField(_("UTM campaign"), max_length=150, blank=True)
    utm_term     = models.CharField(_("UTM term"), max_length=150, blank=True)
    utm_content  = models.CharField(_("UTM content"), max_length=150, blank=True)
    ip_address   = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent   = models.TextField(_("user agent"), blank=True)
    country      = models.CharField(_("country"), max_length=2, blank=True)
    language     = models.CharField(_("preferred language"), max_length=10, default="en")

    # ── Scoring & assignment ─────────────────────────────────────────────
    score       = models.PositiveSmallIntegerField(_("lead score"), default=0)
    is_spam     = models.BooleanField(_("marked as spam"), default=False, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_leads", verbose_name=_("assigned to"),
    )

    lost_reason  = models.CharField(_("lost reason"), max_length=255, blank=True)
    converted_at = models.DateTimeField(_("converted at"), null=True, blank=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("lead")
        verbose_name_plural = _("leads")
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_lead_status_created"),
            models.Index(fields=["lead_type", "status"], name="idx_lead_type_status"),
            models.Index(fields=["email"], name="idx_lead_email"),
            models.Index(fields=["assigned_to", "status"], name="idx_lead_assigned_status"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}> — {self.get_lead_type_display()}"


class QuoteRequestDetail(UUIDModel, TimeStampedModel):
    """Structured data captured only when lead_type == Lead.LeadType.QUOTE."""

    lead = models.OneToOneField(
        Lead, on_delete=models.CASCADE, related_name="quote_detail", verbose_name=_("lead"),
    )
    requested_services = models.ManyToManyField(
        "content.Service", blank=True,
        related_name="quote_requests", verbose_name=_("requested services"),
    )
    project_description  = models.TextField(_("project description"), blank=True)
    estimated_budget_min = models.DecimalField(
        _("estimated budget (min)"), max_digits=12, decimal_places=2, null=True, blank=True,
    )
    estimated_budget_max = models.DecimalField(
        _("estimated budget (max)"), max_digits=12, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(_("currency"), max_length=3, default="USD")

    class Meta:
        verbose_name        = _("quote request detail")
        verbose_name_plural = _("quote request details")

    def __str__(self) -> str:
        return f"Quote detail for {self.lead}"


class LeadActivity(UUIDModel, TimeStampedModel):
    """Timeline/audit log of everything that happens to a Lead."""

    class ActivityType(models.TextChoices):
        STATUS_CHANGE = "status_change", _("Status Change")
        NOTE          = "note",          _("Note")
        EMAIL_SENT    = "email_sent",    _("Email Sent")
        CALL          = "call",          _("Call")
        MEETING       = "meeting",       _("Meeting")
        ASSIGNED      = "assigned",      _("Assigned")
        OTHER         = "other",         _("Other")

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities", verbose_name=_("lead"))
    activity_type = models.CharField(
        _("activity type"), max_length=20, choices=ActivityType.choices, db_index=True,
    )
    description  = models.TextField(_("description"), blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("performed by"),
    )

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("lead activity")
        verbose_name_plural = _("lead activities")
        indexes = [models.Index(fields=["lead", "-created_at"], name="idx_leadactivity_lead_created")]

    def __str__(self) -> str:
        return f"{self.get_activity_type_display()} on {self.lead}"


class NewsletterSubscriber(UUIDModel, TimeStampedModel):
    email           = models.EmailField(_("email"), unique=True, db_index=True)
    language        = models.CharField(_("preferred language"), max_length=10, default="en")
    source          = models.CharField(_("source page"), max_length=500, blank=True)
    is_active       = models.BooleanField(_("active"), default=True, db_index=True)
    subscribed_at   = models.DateTimeField(_("subscribed at"), auto_now_add=True)
    unsubscribed_at = models.DateTimeField(_("unsubscribed at"), null=True, blank=True)

    class Meta:
        ordering            = ["-subscribed_at"]
        verbose_name        = _("newsletter subscriber")
        verbose_name_plural = _("newsletter subscribers")

    def __str__(self) -> str:
        return self.email
