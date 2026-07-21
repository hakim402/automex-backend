"""
apps/crm/models/calculator.py
─────────────────────────────────
Cost Calculator — admins define pricing rules per service/complexity tier;
the public widget submits a selection and gets an instant estimate, logged
as a CalculatorSubmission and optionally linked to a captured Lead.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, UUIDModel

from .leads import Lead


class ComplexityTier(models.TextChoices):
    BASIC      = "basic",      _("Basic")
    STANDARD   = "standard",   _("Standard")
    ADVANCED   = "advanced",   _("Advanced")
    ENTERPRISE = "enterprise", _("Enterprise")


class CostCalculatorRule(UUIDModel, TimeStampedModel):
    """Admin-defined price range + duration estimate for one (service, tier) pair."""

    service = models.ForeignKey(
        "content.Service", on_delete=models.CASCADE,
        related_name="calculator_rules", verbose_name=_("service"),
    )
    complexity_tier = models.CharField(
        _("complexity tier"), max_length=20, choices=ComplexityTier.choices, db_index=True,
    )

    base_price_min = models.DecimalField(_("base price (min)"), max_digits=12, decimal_places=2)
    base_price_max = models.DecimalField(_("base price (max)"), max_digits=12, decimal_places=2)
    currency       = models.CharField(_("currency"), max_length=3, default="USD")

    estimated_duration_weeks_min = models.PositiveSmallIntegerField(_("estimated duration (min weeks)"), default=1)
    estimated_duration_weeks_max = models.PositiveSmallIntegerField(_("estimated duration (max weeks)"), default=4)

    factors = models.JSONField(
        _("pricing factors"), default=dict, blank=True,
        help_text=_("Feature-based multipliers, e.g. {'ai_integration': 1.3}."),
    )
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering            = ["service", "complexity_tier"]
        verbose_name        = _("cost calculator rule")
        verbose_name_plural = _("cost calculator rules")
        constraints = [
            models.UniqueConstraint(fields=["service", "complexity_tier"], name="uq_calc_rule_service_tier"),
            models.CheckConstraint(
                condition=models.Q(base_price_max__gte=models.F("base_price_min")), name="chk_calc_price_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service} — {self.get_complexity_tier_display()}"


class CalculatorSubmission(UUIDModel, TimeStampedModel):
    """Log of every estimate a visitor generated, for lead-scoring and analytics."""

    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calculator_submissions", verbose_name=_("lead"),
    )
    selected_service = models.ForeignKey(
        "content.Service",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calculator_submissions", verbose_name=_("selected service"),
    )
    complexity_tier   = models.CharField(_("complexity tier"), max_length=20, choices=ComplexityTier.choices)
    selected_features = models.JSONField(_("selected features"), default=list, blank=True)

    estimated_price_min = models.DecimalField(
        _("estimated price (min)"), max_digits=12, decimal_places=2, null=True, blank=True,
    )
    estimated_price_max = models.DecimalField(
        _("estimated price (max)"), max_digits=12, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField(_("currency"), max_length=3, default="USD")

    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)

    # ── Enterprise fields ────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="calculator_submissions", verbose_name=_("linked user"),
    )
    converted_to_lead = models.BooleanField(_("converted to lead"), default=False)
    converted_lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("converted lead"),
    )

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("calculator submission")
        verbose_name_plural = _("calculator submissions")

    def __str__(self) -> str:
        return f"Estimate for {self.selected_service} ({self.created_at:%Y-%m-%d})"
