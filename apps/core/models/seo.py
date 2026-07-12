"""
apps/core/models/seo.py
──────────────────────────
Production SEO infrastructure shared by every public-facing content model
(Service, CaseStudy, BlogPost, Industry, ...).

Three layers, used together:

1. seo_translated_fields()  — per-language fields (meta title/description/
   keywords, canonical URL) spliced into a django-parler TranslatedFields()
   block, since search snippets must be written per language, not shared.

2. SEOFieldsMixin            — language-independent SEO controls: Open Graph
   image/type, Twitter card type, robots directives (index/follow), and
   sitemap hints (priority/changefreq). These don't vary per translation.

3. SEOSettings (singleton)  + Redirect — site-wide defaults consumed when
   building <head> tags, robots.txt, sitemap.xml, and the JSON-LD
   Organization schema, plus a 301/302 redirect table for retired URLs.

Usage on a content model
-------------------------
    class Service(TranslatableModel, UUIDModel, TimeStampedModel,
                   OrderableModel, PublishableModel, SEOFieldsMixin):
        translations = TranslatedFields(
            name=models.CharField(max_length=200),
            slug=models.SlugField(max_length=220, db_index=True),
            **seo_translated_fields(),
        )
        structured_data_type = "Service"   # schema.org type, see SEOFieldsMixin
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimeStampedModel, UUIDModel


# ──────────────────────────────────────────────────────────────────────────────
# 1. PER-LANGUAGE META FIELDS (for django-parler TranslatedFields)
# ──────────────────────────────────────────────────────────────────────────────

def seo_translated_fields() -> dict:
    """
    Returns a dict of freshly-instantiated SEO field objects to splice into a
    django-parler TranslatedFields() call. Must be called fresh per model —
    never reuse a single dict/field instance across two different models.
    """
    return dict(
        meta_title=models.CharField(
            _("meta title"), max_length=70, blank=True,
            help_text=_("Falls back to the page title if blank. Keep under 60 characters."),
        ),
        meta_description=models.CharField(
            _("meta description"), max_length=160, blank=True,
            help_text=_("Shown in search results. Keep under 155 characters."),
        ),
        meta_keywords=models.CharField(_("meta keywords"), max_length=255, blank=True),
        canonical_url=models.URLField(
            _("canonical URL"), max_length=500, blank=True,
            help_text=_("Leave blank to use this page's own URL."),
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# 2. LANGUAGE-INDEPENDENT SEO CONTROLS
# ──────────────────────────────────────────────────────────────────────────────

class SEOFieldsMixin(models.Model):
    """
    Mix into any publishable content model alongside seo_translated_fields()
    for full SEO coverage: social previews, robots directives, sitemap hints,
    and structured-data typing.
    """

    class OGType(models.TextChoices):
        WEBSITE = "website", _("Website")
        ARTICLE = "article", _("Article")
        PRODUCT = "product", _("Product")
        PROFILE = "profile", _("Profile")

    class TwitterCard(models.TextChoices):
        SUMMARY              = "summary",              _("Summary")
        SUMMARY_LARGE_IMAGE  = "summary_large_image",  _("Summary Large Image")

    class ChangeFreq(models.TextChoices):
        ALWAYS  = "always",  _("Always")
        HOURLY  = "hourly",  _("Hourly")
        DAILY   = "daily",   _("Daily")
        WEEKLY  = "weekly",  _("Weekly")
        MONTHLY = "monthly", _("Monthly")
        YEARLY  = "yearly",  _("Yearly")
        NEVER   = "never",   _("Never")

    og_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("Open Graph image"),
        help_text=_(
            "Social share preview image. Falls back to the page's own hero/"
            "cover image at serialization time, then SEOSettings.default_og_image."
        ),
    )
    og_type = models.CharField(
        _("Open Graph type"), max_length=20, choices=OGType.choices, default=OGType.WEBSITE,
    )
    twitter_card = models.CharField(
        _("Twitter card type"), max_length=30,
        choices=TwitterCard.choices, default=TwitterCard.SUMMARY_LARGE_IMAGE,
    )

    robots_index  = models.BooleanField(_("allow indexing"), default=True)
    robots_follow = models.BooleanField(_("allow following links"), default=True)

    sitemap_priority = models.DecimalField(
        _("sitemap priority"), max_digits=2, decimal_places=1, default=0.5,
        help_text=_("0.0 to 1.0 — relative importance for sitemap.xml."),
    )
    sitemap_changefreq = models.CharField(
        _("sitemap change frequency"), max_length=10,
        choices=ChangeFreq.choices, default=ChangeFreq.MONTHLY,
    )
    structured_data_type = models.CharField(
        _("structured data (JSON-LD) type"), max_length=50, blank=True,
        help_text=_("schema.org type used when rendering JSON-LD, e.g. 'Service', 'Article', 'FAQPage'."),
    )

    class Meta:
        abstract = True

    @property
    def robots_meta_content(self) -> str:
        """e.g. 'index, follow' — ready to drop into <meta name="robots">."""
        index  = "index" if self.robots_index else "noindex"
        follow = "follow" if self.robots_follow else "nofollow"
        return f"{index}, {follow}"


# ──────────────────────────────────────────────────────────────────────────────
# 3. SITE-WIDE SEO DEFAULTS + REDIRECTS
# ──────────────────────────────────────────────────────────────────────────────

class SEOSettings(UUIDModel, TimeStampedModel):
    """
    Singleton row of site-wide SEO/Organization defaults, consumed by the
    sitemap builder, robots.txt view, and the JSON-LD Organization schema
    injected on every page.

    Enforced as a true singleton via the unique `is_singleton` flag (the
    standard Django pattern) rather than pk juggling — the second insert
    attempt will fail the unique constraint at the database level.
    Use `SEOSettings.get_solo()` to fetch-or-create the one row.
    """

    is_singleton = models.BooleanField(default=True, unique=True, editable=False)

    site_name                  = models.CharField(_("site name"), max_length=150, default="AUTOMEX")
    default_meta_title_suffix  = models.CharField(
        _("default title suffix"), max_length=100, blank=True, default=" | AUTOMEX",
    )
    default_meta_description   = models.CharField(_("default meta description"), max_length=160, blank=True)
    default_og_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("default OG image"),
    )

    organization_legal_name = models.CharField(_("organization legal name"), max_length=200, default="AUTOMEX")
    organization_logo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("organization logo"),
    )
    organization_url = models.URLField(_("organization URL"), max_length=500, default="https://automex.tech")
    organization_social_profiles = models.JSONField(
        _("social profile URLs"), default=list, blank=True,
        help_text=_("List of profile URLs (LinkedIn, X, GitHub, ...) used in JSON-LD 'sameAs'."),
    )
    contact_email = models.EmailField(_("public contact email"), blank=True)
    contact_phone = models.CharField(_("public contact phone"), max_length=30, blank=True)

    google_site_verification = models.CharField(_("Google site verification code"), max_length=255, blank=True)
    google_analytics_id      = models.CharField(_("Google Analytics ID"), max_length=50, blank=True)
    google_tag_manager_id    = models.CharField(_("Google Tag Manager ID"), max_length=50, blank=True)

    class Meta:
        verbose_name        = _("SEO settings")
        verbose_name_plural = _("SEO settings")

    def __str__(self) -> str:
        return "SEO Settings"

    @classmethod
    def get_solo(cls) -> "SEOSettings":
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class Redirect(UUIDModel, TimeStampedModel):
    """301/302 redirect table for retired or restructured URLs (SEO-critical when migrating a site)."""

    old_path     = models.CharField(_("old path"), max_length=500, unique=True, db_index=True)
    new_path     = models.CharField(_("new path"), max_length=500)
    is_permanent = models.BooleanField(_("permanent (301)"), default=True)
    is_active    = models.BooleanField(_("active"), default=True, db_index=True)
    hit_count    = models.PositiveIntegerField(_("hit count"), default=0)

    class Meta:
        ordering            = ["old_path"]
        verbose_name        = _("redirect")
        verbose_name_plural = _("redirects")

    def __str__(self) -> str:
        return f"{self.old_path} → {self.new_path}"
