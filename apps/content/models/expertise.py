"""
apps/content/models/expertise.py
────────────────────────────────────
AI capabilities and technical expertise areas that showcase the company's
core competencies, linked to services, technologies, and case studies.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel


class AICapability(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    class Category(models.TextChoices):
        NLP                 = "nlp",                 _("NLP")
        COMPUTER_VISION     = "computer_vision",     _("Computer Vision")
        PREDICTIVE_ANALYTICS = "predictive_analytics", _("Predictive Analytics")
        GENERATIVE_AI       = "generative_ai",       _("Generative AI")
        AUTOMATION          = "automation",          _("Automation")
        RAG_AGENTS          = "rag_agents",          _("RAG & Agents")
        MLOPS               = "mlops",               _("MLOps")

    class MaturityLevel(models.TextChoices):
        RESEARCH     = "research",     _("Research")
        PRODUCTION   = "production",   _("Production")
        EXPERIMENTAL = "experimental", _("Experimental")

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=200),
        description = models.TextField(_("description"), blank=True),
    )
    slug = models.SlugField(_("slug"), max_length=220, unique=True)

    category = models.CharField(
        _("category"), max_length=30, choices=Category.choices, db_index=True,
    )
    maturity_level = models.CharField(
        _("maturity level"), max_length=20,
        choices=MaturityLevel.choices, default=MaturityLevel.PRODUCTION,
    )

    icon = models.CharField(_("icon"), max_length=100, blank=True, help_text=_("Icon class or emoji."))
    demo_url = models.URLField(_("demo URL"), blank=True)
    cover_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("cover image"),
    )

    related_services = models.ManyToManyField(
        "content.Service", blank=True,
        related_name="ai_capabilities", verbose_name=_("related services"),
    )
    technologies = models.ManyToManyField(
        "content.Technology", blank=True,
        related_name="ai_capabilities", verbose_name=_("technologies"),
    )

    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("AI capability")
        verbose_name_plural = _("AI capabilities")

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or self.slug


class TechExpertiseArea(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    class Category(models.TextChoices):
        ARCHITECTURE   = "architecture",    _("Architecture")
        CLOUD          = "cloud",           _("Cloud")
        DATA_ENGINEERING = "data_engineering", _("Data Engineering")
        AI             = "ai",              _("AI")
        SECURITY       = "security",        _("Security")
        MOBILE         = "mobile",          _("Mobile")
        DEVOPS         = "devops",          _("DevOps")
        QA             = "qa",              _("QA")

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=200),
        description = models.TextField(_("description"), blank=True),
    )
    slug = models.SlugField(_("slug"), max_length=220, unique=True)
    icon = models.CharField(_("icon"), max_length=100, blank=True, help_text=_("Icon class or emoji."))

    category = models.CharField(
        _("category"), max_length=30, choices=Category.choices, db_index=True,
    )

    technologies = models.ManyToManyField(
        "content.Technology", blank=True,
        related_name="expertise_areas", verbose_name=_("technologies"),
    )
    case_studies = models.ManyToManyField(
        "content.CaseStudy", blank=True,
        related_name="expertise_areas", verbose_name=_("case studies"),
    )

    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("tech expertise area")
        verbose_name_plural = _("tech expertise areas")

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or self.slug
