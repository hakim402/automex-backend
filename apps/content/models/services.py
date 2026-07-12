"""
apps/content/models/services.py
───────────────────────────────────
A single AUTOMEX service and its dedicated landing page (Custom Software
Development, AI, Data Engineering, ERP & CRM, Cloud & DevOps, UI/UX Design,
IT Staff Augmentation, ...) — the primary revenue-driving content type.

Full editorial workflow (PublishableModel) + full SEO stack
(seo_translated_fields for per-language meta, SEOFieldsMixin for OG/robots/
sitemap/structured-data controls).
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

from .taxonomy import ServiceCategory, Technology, Industry


class Service(
    TranslatableModel, UUIDModel, TimeStampedModel,
    OrderableModel, PublishableModel, SEOFieldsMixin,
):
    translations = TranslatedFields(
        name               = models.CharField(_("name"), max_length=200),
        slug               = models.SlugField(_("slug"), max_length=220, db_index=True),
        short_description  = models.CharField(_("short description"), max_length=300, blank=True),
        overview           = models.TextField(_("overview"), blank=True),
        problems_we_solve  = models.TextField(_("problems we solve"), blank=True),
        features = models.TextField(
            _("features"), blank=True,
            help_text=_("One feature per line; rendered as a bullet list by the frontend."),
        ),
        benefits = models.TextField(
            _("benefits"), blank=True,
            help_text=_("One benefit per line; rendered as a bullet list by the frontend."),
        ),
        **seo_translated_fields(),
        meta={"unique_together": [("language_code", "slug")]},
    )

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="services", verbose_name=_("category"),
    )
    icon       = models.CharField(_("icon"), max_length=100, blank=True)
    hero_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("hero image"),
    )

    technologies = models.ManyToManyField(
        Technology, blank=True, related_name="services", verbose_name=_("technologies"),
    )
    industries = models.ManyToManyField(
        Industry, blank=True, related_name="services", verbose_name=_("industries"),
    )

    is_featured = models.BooleanField(_("featured"), default=False, db_index=True)

    objects = PublishableTranslatableManager()

    class Meta:
        verbose_name        = _("service")
        verbose_name_plural = _("services")
        ordering             = ["order"]

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or str(self.id)

    def save(self, *args, **kwargs):
        if not self.structured_data_type:
            self.structured_data_type = "Service"
        super().save(*args, **kwargs)
