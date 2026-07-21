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
    class ProjectType(models.TextChoices):
        WEB_APP              = "web_app",              _("Web Application")
        MOBILE               = "mobile",               _("Mobile App")
        AI_ML                = "ai_ml",                _("AI / Machine Learning")
        ENTERPRISE_INTEGRATION = "enterprise_integration", _("Enterprise Integration")
        DATA_ENGINEERING     = "data_engineering",     _("Data Engineering")
        CONSULTING           = "consulting",           _("Consulting")

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
    client_website = models.URLField(
        _("client website"), blank=True,
        help_text=_("Link to the client's website."),
    )
    thumbnail = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("thumbnail"),
    )

    # ── Project classification ────────────────────────────────────────────────
    project_type = models.CharField(
        _("project type"), max_length=30,
        choices=ProjectType.choices, blank=True, db_index=True,
    )
    team_size = models.PositiveIntegerField(
        _("team size"), null=True, blank=True,
        help_text=_("Number of people who delivered this project."),
    )
    project_year = models.PositiveIntegerField(
        _("project year"), null=True, blank=True,
        help_text=_("Year the project was delivered."),
    )
    project_duration_display = models.CharField(
        _("project duration"), max_length=100, blank=True,
        help_text=_("Human-readable duration, e.g. '6 months', '12 weeks'."),
    )

    # ── Business impact metrics ───────────────────────────────────────────────
    key_metrics = models.JSONField(
        _("key metrics"), default=dict, blank=True,
        help_text=_(
            'Structured business impact data, e.g. '
            '{"roi_increase": 340, "cost_reduction": "45%", "performance_gain": "10x"}.'
        ),
    )

    # ── AI project flags ──────────────────────────────────────────────────────
    is_ai_project = models.BooleanField(
        _("AI/ML project"), default=False, db_index=True,
        help_text=_("Flag for AI/ML specific projects."),
    )
    ai_models_used = models.JSONField(
        _("AI models used"), default=list, blank=True,
        help_text=_(
            'List of AI/ML models or techniques used, e.g. '
            '["GPT-4", "Computer Vision", "RAG", "Fine-tuning"].'
        ),
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    technologies = models.ManyToManyField(
        Technology, blank=True, related_name="case_studies", verbose_name=_("technologies"),
    )
    related_services = models.ManyToManyField(
        Service, blank=True, related_name="case_studies", verbose_name=_("related services"),
    )
    testimonial = models.ForeignKey(
        "content.Testimonial",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="featured_in_case_studies", verbose_name=_("client testimonial"),
        help_text=_("Direct link to the client quote for this project."),
    )

    project_url             = models.URLField(_("live project URL"), blank=True)
    project_duration_weeks  = models.PositiveIntegerField(_("project duration (weeks)"), null=True, blank=True)
    is_featured             = models.BooleanField(_("featured"), default=False, db_index=True)

    objects = PublishableTranslatableManager()

    class Meta:
        verbose_name        = _("case study")
        verbose_name_plural = _("case studies")
        ordering             = ["order", "-published_at"]
        indexes = [
            models.Index(fields=["project_type", "is_ai_project"], name="idx_casestudy_type_ai"),
        ]

    def __str__(self) -> str:
        return self.safe_translation_getter("title", any_language=True) or str(self.id)

    def save(self, *args, **kwargs):
        if not self.structured_data_type:
            self.structured_data_type = "Article"
        super().save(*args, **kwargs)


class CaseStudyGalleryImage(UUIDModel, TimeStampedModel, OrderableModel):
    """Additional project screenshots/photos beyond the main thumbnail."""

    class ImageType(models.TextChoices):
        SCREENSHOT   = "screenshot",   _("Screenshot")
        DESIGN       = "design",       _("Design Mockup")
        DEMO         = "demo",         _("Demo")
        ARCHITECTURE = "architecture", _("Architecture Diagram")

    case_study = models.ForeignKey(
        CaseStudy, on_delete=models.CASCADE,
        related_name="gallery", verbose_name=_("case study"),
    )
    media = models.ForeignKey(
        "core.MediaAsset", on_delete=models.CASCADE,
        related_name="+", verbose_name=_("media"),
    )
    caption = models.CharField(_("caption"), max_length=300, blank=True)
    is_before_after = models.BooleanField(
        _("before/after image"), default=False,
        help_text=_("If True, this image is part of a before/after comparison slider."),
    )
    image_type = models.CharField(
        _("image type"), max_length=20,
        choices=ImageType.choices, default=ImageType.SCREENSHOT,
        db_index=True,
    )

    class Meta:
        ordering             = ["order"]
        verbose_name        = _("case study gallery image")
        verbose_name_plural = _("case study gallery images")

    def __str__(self) -> str:
        return f"{self.case_study} — image {self.order}"
