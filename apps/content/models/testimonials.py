"""
apps/content/models/testimonials.py
───────────────────────────────────────
Client testimonials/reviews, optionally sourced from Clutch, linkable to a
specific case study or service for contextual display on those pages.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel

from .case_studies import CaseStudy
from .services import Service


class Testimonial(UUIDModel, TimeStampedModel, OrderableModel):
    class Source(models.TextChoices):
        MANUAL     = "manual",     _("Manual")
        CLUTCH     = "clutch",     _("Clutch")
        GOOGLE     = "google",     _("Google")
        LINKEDIN   = "linkedin",   _("LinkedIn")
        TRUSTPILOT = "trustpilot", _("Trustpilot")

    client_name    = models.CharField(_("client name"), max_length=200)
    client_role    = models.CharField(_("client role"), max_length=200, blank=True)
    client_company = models.CharField(_("client company"), max_length=200, blank=True)
    client_avatar  = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("client avatar"),
    )

    quote  = models.TextField(_("quote"))
    rating = models.PositiveSmallIntegerField(_("rating"), default=5, help_text=_("1 to 5 stars."))

    source     = models.CharField(_("source"), max_length=20, choices=Source.choices, default=Source.MANUAL)
    source_url = models.URLField(_("source URL"), blank=True)

    related_case_study = models.ForeignKey(
        CaseStudy,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testimonials", verbose_name=_("related case study"),
    )
    related_service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testimonials", verbose_name=_("related service"),
    )

    is_featured  = models.BooleanField(_("featured"), default=False, db_index=True)
    is_published = models.BooleanField(_("published"), default=True, db_index=True)

    class Meta:
        ordering            = ["order", "-created_at"]
        verbose_name        = _("testimonial")
        verbose_name_plural = _("testimonials")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="chk_testimonial_rating_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.client_name} — {self.client_company or 'N/A'}"
