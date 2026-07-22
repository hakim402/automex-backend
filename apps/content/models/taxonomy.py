"""
apps/content/models/taxonomy.py
───────────────────────────────────
Reference/lookup data shared across Services, Case Studies, Blog, and the
Cost Calculator: categories, technologies, industries, process steps, FAQs.

These use a simple is_active flag rather than the full PublishableModel
workflow — a one-line technology entry doesn't need draft/review/approve.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel


class ServiceCategory(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """Optional grouping for the Services Overview grid/nav."""

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=150),
        description = models.TextField(
            _("description"), blank=True,
            help_text=_("SEO-rich description for category landing pages."),
        ),
    )

    slug      = models.SlugField(_("slug"), max_length=170, unique=True)
    icon      = models.CharField(
        _("icon"), max_length=100, blank=True,
        help_text=_("Icon identifier used by the frontend, e.g. 'lucide:cpu'."),
    )
    icon_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("icon image"),
        help_text=_("Visual icon asset for this category."),
    )
    is_visible_on_nav = models.BooleanField(
        _("visible in navigation"), default=True, db_index=True,
        help_text=_("Control whether this category appears in the main navigation menu."),
    )
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering            = ["order"]
        verbose_name        = _("service category")
        verbose_name_plural = _("service categories")

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or self.slug


class Technology(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """Individual technology/tool shown in the Technologies grid and on service pages."""

    class Category(models.TextChoices):
        FRONTEND   = "frontend",   _("Frontend")
        BACKEND    = "backend",    _("Backend")
        DATABASE   = "database",   _("Database")
        CLOUD      = "cloud",      _("Cloud")
        AI         = "ai",         _("AI")
        ENTERPRISE = "enterprise", _("Enterprise")
        MOBILE     = "mobile",     _("Mobile")
        DEVOPS     = "devops",     _("DevOps")
        OTHER      = "other",      _("Other")

    class ProficiencyLevel(models.TextChoices):
        EXPERT       = "expert",       _("Expert")
        ADVANCED     = "advanced",     _("Advanced")
        INTERMEDIATE = "intermediate", _("Intermediate")

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=100),
        description = models.TextField(
            _("description"), blank=True,
            help_text=_("Detailed description for technology detail pages or tooltips."),
        ),
    )

    slug        = models.SlugField(_("slug"), max_length=120, unique=True)
    category    = models.CharField(_("category"), max_length=20, choices=Category.choices, db_index=True)
    icon        = models.CharField(_("icon"), max_length=100, blank=True)
    website_url = models.URLField(_("website URL"), blank=True)
    proficiency_level = models.CharField(
        _("proficiency level"), max_length=20,
        choices=ProficiencyLevel.choices, default=ProficiencyLevel.ADVANCED,
        db_index=True,
        help_text=_("AUTOMEX's expertise depth in this technology."),
    )
    logo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("logo"),
        help_text=_("Official technology logo asset."),
    )
    is_active   = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering            = ["category", "order"]
        verbose_name        = _("technology")
        verbose_name_plural = _("technologies")
        indexes = [models.Index(fields=["category", "is_active"], name="idx_tech_category_active")]

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or self.slug


class Industry(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """Industry vertical AUTOMEX serves (Healthcare, Finance, Retail, ...)."""

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=150),
        slug        = models.SlugField(_("slug"), max_length=170, db_index=True),
        description = models.TextField(_("description"), blank=True),
        meta={"unique_together": [("language_code", "slug")]},
    )

    icon      = models.CharField(_("icon"), max_length=100, blank=True)
    icon_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("icon image"),
        help_text=_("Visual icon asset for this industry."),
    )
    compliance_standards = models.JSONField(
        _("compliance standards"), default=list, blank=True,
        help_text=_(
            'List of compliance frameworks relevant to this industry, '
            'e.g. ["HIPAA", "SOC2", "PCI-DSS"].'
        ),
    )
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        verbose_name        = _("industry")
        verbose_name_plural = _("industries")
        ordering             = ["order"]

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or str(self.id)


class ProcessStep(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Global, reusable development-process step (Discovery → Planning →
    UI/UX Design → Development → QA → Deployment → Maintenance & Support).
    """

    translations = TranslatedFields(
        title       = models.CharField(_("title"), max_length=150),
        description = models.TextField(_("description"), blank=True),
    )

    icon      = models.CharField(_("icon"), max_length=100, blank=True)
    estimated_duration = models.CharField(
        _("estimated duration"), max_length=100, blank=True,
        help_text=_("e.g. '2-3 weeks', '1 sprint'."),
    )
    deliverables = models.JSONField(
        _("deliverables"), default=list, blank=True,
        help_text=_(
            'List of outputs from this step, e.g. '
            '["Requirements document", "Wireframes", "Technical spec"].'
        ),
    )
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        verbose_name        = _("process step")
        verbose_name_plural = _("process steps")
        ordering             = ["order"]

    def __str__(self) -> str:
        return self.safe_translation_getter("title", any_language=True) or str(self.id)


class FAQ(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """Global FAQ (service=None) or per-service FAQ, rendered on that service's detail page."""

    class Category(models.TextChoices):
        GENERAL = "general", _("General")
        PRICING = "pricing", _("Pricing")
        PROCESS = "process", _("Process")
        SERVICE = "service", _("Service-specific")

    translations = TranslatedFields(
        question = models.CharField(_("question"), max_length=300),
        answer   = models.TextField(_("answer")),
    )

    service   = models.ForeignKey(
        "content.Service",
        on_delete=models.CASCADE, null=True, blank=True,
        related_name="faqs", verbose_name=_("related service"),
    )
    category  = models.CharField(
        _("category"), max_length=20, choices=Category.choices, default=Category.GENERAL, db_index=True,
    )
    is_active   = models.BooleanField(_("active"), default=True, db_index=True)
    is_prominent = models.BooleanField(
        _("prominent"), default=False, db_index=True,
        help_text=_("If True, this FAQ is shown in the hero/above-fold area rather than at the bottom of the page."),
    )

    class Meta:
        verbose_name        = _("FAQ")
        verbose_name_plural = _("FAQs")
        ordering             = ["order"]
        indexes = [models.Index(fields=["service", "is_active"], name="idx_faq_service_active")]

    def __str__(self) -> str:
        return self.safe_translation_getter("question", any_language=True) or str(self.id)
