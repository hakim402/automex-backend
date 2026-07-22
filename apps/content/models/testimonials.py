"""
apps/content/models/testimonials.py
───────────────────────────────────────
Client testimonials/reviews, optionally sourced from Clutch, linkable to a
specific case study or service for contextual display on those pages.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel

from .case_studies import CaseStudy
from .services import Service
from .taxonomy import Industry


class Testimonial(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    class Source(models.TextChoices):
        MANUAL     = "manual",     _("Manual")
        CLUTCH     = "clutch",     _("Clutch")
        GOOGLE     = "google",     _("Google")
        LINKEDIN   = "linkedin",   _("LinkedIn")
        TRUSTPILOT = "trustpilot", _("Trustpilot")

    translations = TranslatedFields(
        client_name    = models.CharField(_("client name"), max_length=200),
        client_role    = models.CharField(_("client role"), max_length=200, blank=True),
        client_company = models.CharField(_("client company"), max_length=200, blank=True),
        quote          = models.TextField(_("quote")),
    )
    client_avatar  = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("client avatar"),
    )

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

    # ── Enterprise fields ──────────────────────────────────────────
    video_url = models.URLField(_("video URL"), blank=True)
    video_thumbnail = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("video thumbnail"),
    )
    project_impact = models.JSONField(
        _("project impact"), default=dict, blank=True,
        help_text=_("Key impact metrics, e.g. {\"revenue_increase\": \"40%\", \"cost_savings\": \"$2M\"}"),
    )
    client_industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testimonials", verbose_name=_("client industry"),
    )
    is_video_testimonial = models.BooleanField(
        _("video testimonial"), default=False, db_index=True,
    )

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
        name = self.safe_translation_getter("client_name", any_language=True) or "Unknown"
        company = self.safe_translation_getter("client_company", any_language=True) or "N/A"
        return f"{name} — {company}"
