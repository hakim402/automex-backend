"""
apps/content/models/case_studies.py
───────────────────────────────────────
Client project case studies — Project Image, Client Industry, Overview,
Technologies Used, Business Challenge, Solution, Results, CTA — per the
AUTOMEX MVP doc, with the same PublishableModel + SEO stack as Service.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import (
    OrderableModel,
    PublishableModel,
    PublishableTranslatableManager,
    SEOFieldsMixin,
    TimeStampedModel,
    UUIDModel,
    seo_translated_fields,
)

from .taxonomy import Industry, Technology
from .services import Service


class CaseStudy(
    TranslatableModel, UUIDModel, TimeStampedModel,
    OrderableModel, PublishableModel, SEOFieldsMixin,
):
    translations = TranslatedFields(
        title     = models.CharField(_("title"), max_length=250),
        slug      = models.SlugField(_("slug"), max_length=270, db_index=True),
        overview  = models.TextField(_("overview"), blank=True),
        challenge = models.TextField(_("business challenge"), blank=True),
        solution  = models.TextField(_("solution"), blank=True),
        results   = models.TextField(_("results"), blank=True),
        **seo_translated_fields(),
        meta={"unique_together": [("language_code", "slug")]},
    )

    client_name     = models.CharField(_("client name"), max_length=200, blank=True)
    client_industry = models.ForeignKey(
        Industry,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="case_studies", verbose_name=_("client industry"),
    )
    client_logo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("client logo"),
    )
    thumbnail = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("thumbnail"),
    )

    technologies = models.ManyToManyField(
        Technology, blank=True, related_name="case_studies", verbose_name=_("technologies"),
    )
    related_services = models.ManyToManyField(
        Service, blank=True, related_name="case_studies", verbose_name=_("related services"),
    )

    project_url             = models.URLField(_("live project URL"), blank=True)
    project_duration_weeks  = models.PositiveIntegerField(_("project duration (weeks)"), null=True, blank=True)
    is_featured             = models.BooleanField(_("featured"), default=False, db_index=True)

    objects = PublishableTranslatableManager()

    class Meta:
        verbose_name        = _("case study")
        verbose_name_plural = _("case studies")
        ordering             = ["order", "-published_at"]

    def __str__(self) -> str:
        return self.safe_translation_getter("title", any_language=True) or str(self.id)

    def save(self, *args, **kwargs):
        if not self.structured_data_type:
            self.structured_data_type = "Article"
        super().save(*args, **kwargs)


class CaseStudyGalleryImage(UUIDModel, TimeStampedModel, OrderableModel):
    """Additional project screenshots/photos beyond the main thumbnail."""

    case_study = models.ForeignKey(
        CaseStudy, on_delete=models.CASCADE,
        related_name="gallery", verbose_name=_("case study"),
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE,
        related_name="+", verbose_name=_("media"),
    )
    caption = models.CharField(_("caption"), max_length=300, blank=True)

    class Meta:
        ordering             = ["order"]
        verbose_name        = _("case study gallery image")
        verbose_name_plural = _("case study gallery images")

    def __str__(self) -> str:
        return f"{self.case_study} — image {self.order}"
