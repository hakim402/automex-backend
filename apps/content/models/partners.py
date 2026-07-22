"""
apps/content/models/partners.py
────────────────────────────────────
Technology partners and certifications that demonstrate the company's
ecosystem relationships and validated competencies.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel


class Partner(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    class PartnerType(models.TextChoices):
        TECHNOLOGY     = "technology",     _("Technology")
        IMPLEMENTATION = "implementation", _("Implementation")
        CLOUD          = "cloud",          _("Cloud")
        INTEGRATION    = "integration",    _("Integration")
        RESELLER       = "reseller",       _("Reseller")

    class Tier(models.TextChoices):
        SILVER    = "silver",    _("Silver")
        GOLD      = "gold",      _("Gold")
        PLATINUM  = "platinum",  _("Platinum")
        DIAMOND   = "diamond",   _("Diamond")

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=200),
        description = models.TextField(_("description"), blank=True),
    )
    slug = models.SlugField(_("slug"), max_length=220, unique=True)
    logo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("logo"),
    )
    website_url = models.URLField(_("website URL"), blank=True)

    partner_type = models.CharField(
        _("partner type"), max_length=20, choices=PartnerType.choices, db_index=True,
    )
    tier = models.CharField(
        _("tier"), max_length=20, choices=Tier.choices, blank=True,
    )

    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("partner")
        verbose_name_plural = _("partners")

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or self.slug


class Certification(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    translations = TranslatedFields(
        name   = models.CharField(_("name"), max_length=250),
        issuer = models.CharField(_("issuer"), max_length=200),
    )
    badge_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("badge image"),
    )

    credential_url = models.URLField(_("credential URL"), blank=True)
    credential_id = models.CharField(_("credential ID"), max_length=100, blank=True)

    issue_date = models.DateField(_("issue date"), null=True, blank=True)
    expiry_date = models.DateField(_("expiry date"), null=True, blank=True)

    related_services = models.ManyToManyField(
        "content.Service", blank=True,
        related_name="certifications", verbose_name=_("related services"),
    )

    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("certification")
        verbose_name_plural = _("certifications")

    def __str__(self) -> str:
        name = self.safe_translation_getter("name", any_language=True) or "Unknown"
        issuer = self.safe_translation_getter("issuer", any_language=True) or ""
        return f"{name} — {issuer}"
