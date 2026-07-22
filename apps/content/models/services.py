"""
apps/content/models/services.py
───────────────────────────────────
A single AUTOMEX service and its dedicated landing page (Custom Software
Development, AI, Data Engineering, ERP & CRM, Cloud & DevOps, UI/UX Design,
IT Staff Augmentation, ...) — the primary revenue-driving content type.

Full editorial workflow (PublishableModel) + full SEO stack
(seo_translated_fields for per-language meta, SEOFieldsMixin for OG/robots/
sitemap/structured-data controls).

Enterprise enhancements:
- Multiple hero images via ServiceHeroImage gallery
- Thumbnail for cards/listings
- Service tiering (standard / premium / enterprise)
- Pricing display (starting price, model, currency)
- Video presentation & downloadable brochure
- Related services cross-linking
- Key metrics (projects delivered, team size, satisfaction rate)
- Translated CTA controls
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
    """
    Primary service offering page. Supports multi-language content,
    editorial workflow, full SEO, hero image gallery, pricing display,
    and enterprise-tier feature gating.
    """

    # ── Translated content ────────────────────────────────────────────────────
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
        # ── Translated CTA ────────────────────────────────────────────────────
        cta_text = models.CharField(
            _("CTA text"), max_length=100, blank=True,
            help_text=_("Call-to-action button label, e.g. 'Get a Quote', 'Start Your Project'."),
        ),
        cta_url = models.URLField(
            _("CTA URL"), max_length=500, blank=True,
            help_text=_("Override the CTA destination per language. Leave blank for default contact form."),
        ),
        **seo_translated_fields(),
        meta={"unique_together": [("language_code", "slug")]},
    )

    # ── Classification ────────────────────────────────────────────────────────
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="services", verbose_name=_("category"),
    )

    class ServiceLevel(models.TextChoices):
        STANDARD  = "standard",  _("Standard")
        PREMIUM   = "premium",   _("Premium")
        ENTERPRISE = "enterprise", _("Enterprise")

    service_level = models.CharField(
        _("service level"), max_length=20,
        choices=ServiceLevel.choices, default=ServiceLevel.STANDARD,
        db_index=True,
        help_text=_("Tier used for filtering and pricing display."),
    )
    is_enterprise = models.BooleanField(
        _("enterprise service"), default=False, db_index=True,
        help_text=_("Flag for dedicated enterprise-grade service pages."),
    )

    # ── Media / Images ────────────────────────────────────────────────────────
    icon = models.CharField(
        _("icon"), max_length=100, blank=True,
        help_text=_("Icon identifier used by the frontend, e.g. 'lucide:code'."),
    )
    thumbnail_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("thumbnail image"),
        help_text=_("Small image used in cards, grids, and listing pages."),
    )
    hero_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("primary hero image"),
        help_text=_("Main hero image (used as fallback if no gallery images are set)."),
    )
    video_presentation = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("video presentation"),
        help_text=_("Service overview video or demo reel."),
    )
    brochure = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("brochure / datasheet"),
        help_text=_("Downloadable PDF brochure or service datasheet."),
    )

    # ── Pricing & Engagement ──────────────────────────────────────────────────
    class PricingModel(models.TextChoices):
        FIXED       = "fixed",       _("Fixed Price")
        HOURLY      = "hourly",      _("Hourly Rate")
        QUOTE       = "quote",       _("Custom Quote")
        SUBSCRIPTION = "subscription", _("Subscription")
        RETAINER    = "retainer",    _("Retainer")

    pricing_model = models.CharField(
        _("pricing model"), max_length=20,
        choices=PricingModel.choices, default=PricingModel.QUOTE,
        blank=True,
    )
    starting_price = models.DecimalField(
        _("starting price"), max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text=_("Indicative starting price for display purposes."),
    )
    currency = models.CharField(
        _("currency"), max_length=3, blank=True, default="USD",
        help_text=_("ISO 4217 currency code, e.g. 'USD', 'EUR'."),
    )
    delivery_time_estimate = models.CharField(
        _("delivery time estimate"), max_length=100, blank=True,
        help_text=_("e.g. '4-6 weeks', '2-3 months'. Shown on the service page."),
    )
    team_size_range = models.CharField(
        _("team size range"), max_length=100, blank=True,
        help_text=_("e.g. '3-8 engineers', 'Dedicated team of 5+'."),
    )

    # ── Key Metrics ───────────────────────────────────────────────────────────
    key_metrics = models.JSONField(
        _("key metrics"), default=dict, blank=True,
        help_text=_(
            "Structured metrics for display, e.g. "
            '{"projects_delivered": 150, "client_satisfaction": 98, "years_experience": 12}.'
        ),
    )

    # ── Enterprise Features ───────────────────────────────────────────────────
    enterprise_features = models.JSONField(
        _("enterprise features"), default=list, blank=True,
        help_text=_(
            "List of enterprise-tier capabilities, e.g. "
            '["Dedicated team", "SLA guarantee", "24/7 support", "Custom integrations"].'
        ),
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    technologies = models.ManyToManyField(
        Technology, blank=True, related_name="services", verbose_name=_("technologies"),
    )
    tech_stack_grouped = models.JSONField(
        _("grouped tech stack"), default=dict, blank=True,
        help_text=_(
            'Structured technology groups for display, e.g. '
            '{"Frontend": ["React", "Next.js"], "Backend": ["Django", "Node.js"], '
            '"Cloud": ["AWS", "GCP"]}.'
        ),
    )
    industries = models.ManyToManyField(
        Industry, blank=True, related_name="services", verbose_name=_("industries"),
    )
    related_services = models.ManyToManyField(
        "self", blank=True, symmetrical=True,
        verbose_name=_("related services"),
        help_text=_("Cross-linked services shown as 'You might also need'."),
    )

    # ── Flags ─────────────────────────────────────────────────────────────────
    is_featured = models.BooleanField(_("featured"), default=False, db_index=True)

    objects = PublishableTranslatableManager()

    class Meta:
        verbose_name        = _("service")
        verbose_name_plural = _("services")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service_level", "is_enterprise"], name="idx_service_level_enterprise"),
            models.Index(fields=["is_featured", "status"], name="idx_service_featured_status"),
        ]

    def __str__(self) -> str:
        return self.safe_translation_getter("name", any_language=True) or str(self.id)

    def save(self, *args, **kwargs):
        if not self.structured_data_type:
            self.structured_data_type = "Service"
        super().save(*args, **kwargs)


class ServiceHeroImage(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Additional hero images for a service page gallery / carousel.
    Allows multiple hero images per service with individual captions
    and ordering, replacing the single hero_image limitation.
    """

    translations = TranslatedFields(
        title   = models.CharField(_("title"), max_length=200, blank=True),
        caption = models.CharField(
            _("caption"), max_length=255, blank=True,
            help_text=_("Optional caption or overlay text displayed on the hero image."),
        ),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="hero_images",
        verbose_name=_("service"),
    )
    image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("image"),
    )
    is_cover = models.BooleanField(
        _("cover image"), default=False,
        help_text=_("If set, this image is used as the primary cover/first slide."),
    )

    class Meta:
        verbose_name        = _("service hero image")
        verbose_name_plural = _("service hero images")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_servicehero_service_order"),
        ]

    def __str__(self) -> str:
        return f"Hero image for {self.service} (order={self.order})"


class ServiceProcessStep(UUIDModel, TimeStampedModel, OrderableModel):
    """
    Service-specific development process / workflow steps.
    Links a global ProcessStep to a Service with optional custom title/description
    overrides, allowing each service to show its own tailored workflow.
    """

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="process_steps",
        verbose_name=_("service"),
    )
    process_step = models.ForeignKey(
        "content.ProcessStep",
        on_delete=models.CASCADE,
        related_name="service_links",
        verbose_name=_("process step"),
    )
    custom_title = models.CharField(
        _("custom title"), max_length=150, blank=True,
        help_text=_("Override the global process step title for this service."),
    )
    custom_description = models.TextField(
        _("custom description"), blank=True,
        help_text=_("Override the global process step description for this service."),
    )

    class Meta:
        verbose_name        = _("service process step")
        verbose_name_plural = _("service process steps")
        ordering            = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "process_step"],
                name="uq_service_process_step",
            ),
        ]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svcprocstep_service_order"),
        ]

    def __str__(self) -> str:
        title = self.custom_title or str(self.process_step)
        return f"{self.service} — {title}"


class ServiceDeliverable(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Concrete output/deliverable the client receives upon engagement.
    e.g. 'Source code repository', 'Technical documentation', 'CI/CD pipeline'.
    """

    translations = TranslatedFields(
        title       = models.CharField(_("title"), max_length=200),
        description = models.TextField(_("description"), blank=True),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="deliverables",
        verbose_name=_("service"),
    )
    icon = models.CharField(
        _("icon"), max_length=100, blank=True,
        help_text=_("Icon identifier for the frontend, e.g. 'lucide:file-code'."),
    )

    class Meta:
        verbose_name        = _("service deliverable")
        verbose_name_plural = _("service deliverables")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svcdeliv_svc_order"),
        ]

    def __str__(self) -> str:
        t = self.safe_translation_getter("title", any_language=True) or "Unnamed"
        return f"{self.service} — {t}"


class ServiceAddOn(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Optional upsell package / add-on service a client can purchase
    in addition to the base service. e.g. '24/7 Monitoring', 'Priority Support'.
    """

    translations = TranslatedFields(
        name        = models.CharField(_("name"), max_length=200),
        description = models.TextField(_("description"), blank=True),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="add_ons",
        verbose_name=_("service"),
    )
    price = models.DecimalField(
        _("price"), max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text=_("Indicative price for this add-on. Leave blank for 'on request'."),
    )
    is_included_in_enterprise = models.BooleanField(
        _("included in enterprise"), default=False,
        help_text=_("If True, this add-on is bundled with the enterprise tier at no extra cost."),
    )

    class Meta:
        verbose_name        = _("service add-on")
        verbose_name_plural = _("service add-ons")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svcaddon_service_order"),
        ]

    def __str__(self) -> str:
        name = self.safe_translation_getter("name", any_language=True) or "Unnamed"
        return f"{self.service} — {name}"


class ServiceComparisonRow(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Single row in a feature-comparison pricing table across service tiers.
    Renders as a row: Feature | Standard | Premium | Enterprise.
    """

    translations = TranslatedFields(
        feature_name = models.CharField(
            _("feature name"), max_length=200,
            help_text=_("The feature or capability being compared."),
        ),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="comparison_rows",
        verbose_name=_("service"),
    )
    standard_value = models.CharField(
        _("standard"), max_length=100, blank=True,
        help_text=_("Value shown in the Standard column, e.g. '5 users', '✓', '—'."),
    )
    premium_value = models.CharField(
        _("premium"), max_length=100, blank=True,
        help_text=_("Value shown in the Premium column."),
    )
    enterprise_value = models.CharField(
        _("enterprise"), max_length=100, blank=True,
        help_text=_("Value shown in the Enterprise column."),
    )
    is_highlighted = models.BooleanField(
        _("highlighted"), default=False,
        help_text=_("If True, this row is visually emphasized on the frontend."),
    )

    class Meta:
        verbose_name        = _("service comparison row")
        verbose_name_plural = _("service comparison rows")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svccompare_svc_order"),
        ]

    def __str__(self) -> str:
        feature = self.safe_translation_getter("feature_name", any_language=True) or ""
        return f"{self.service} — {feature}"


class ServiceClientLogo(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Client logo displayed in the 'Trusted By' / 'Our Clients' section
    of a service page. Uses MediaAsset for centralized asset management.
    """

    translations = TranslatedFields(
        client_name = models.CharField(
            _("client name"), max_length=200, blank=True,
            help_text=_("Displayed on hover or as alt text for the logo."),
        ),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="client_logos",
        verbose_name=_("service"),
    )
    logo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("logo"),
    )
    client_url = models.URLField(
        _("client URL"), max_length=500, blank=True,
        help_text=_("Optional link to the client's website."),
    )

    class Meta:
        verbose_name        = _("service client logo")
        verbose_name_plural = _("service client logos")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svccllogo_svc_order"),
        ]

    def __str__(self) -> str:
        name = self.safe_translation_getter("client_name", any_language=True) or "Unnamed client"
        return f"{self.service} — {name}"


class ServiceTestimonial(UUIDModel, TimeStampedModel, OrderableModel):
    """
    Curated through-model linking a Testimonial to a Service with
    per-service ordering and featured flag. Allows the same testimonial
    to appear on multiple services with different display priorities.
    """

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="service_testimonials",
        verbose_name=_("service"),
    )
    testimonial = models.ForeignKey(
        "content.Testimonial",
        on_delete=models.CASCADE,
        related_name="service_links",
        verbose_name=_("testimonial"),
    )
    is_featured = models.BooleanField(
        _("featured"), default=False, db_index=True,
        help_text=_("Pin this testimonial to the top of the service's testimonial section."),
    )

    class Meta:
        verbose_name        = _("service testimonial")
        verbose_name_plural = _("service testimonials")
        ordering            = ["-is_featured", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "testimonial"],
                name="uq_service_testimonial",
            ),
        ]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svctest_svc_order"),
        ]

    def __str__(self) -> str:
        name = self.testimonial.safe_translation_getter("client_name", any_language=True) or "Unnamed"
        return f"{self.service} — {name}"


class ServiceDocument(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Downloadable resource linked to a service page.
    e.g. whitepapers, detailed datasheets, technical specifications.
    """

    class DocumentType(models.TextChoices):
        DATASHEET   = "datasheet",   _("Datasheet")
        WHITEPAPER  = "whitepaper",  _("Whitepaper")
        CASE_STUDY  = "case_study",  _("Case Study")
        SPECIFICATION = "specification", _("Specification")
        PROPOSAL    = "proposal",    _("Proposal Template")
        OTHER       = "other",       _("Other")

    translations = TranslatedFields(
        title       = models.CharField(_("title"), max_length=255),
        description = models.TextField(_("description"), blank=True),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("service"),
    )
    file = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("file"),
        help_text=_("Upload the document to the media library, then link it here."),
    )
    document_type = models.CharField(
        _("document type"), max_length=20,
        choices=DocumentType.choices, default=DocumentType.DATASHEET,
        db_index=True,
    )
    is_public = models.BooleanField(
        _("public download"), default=True,
        help_text=_("If False, only authenticated users can download."),
    )

    class Meta:
        verbose_name        = _("service document")
        verbose_name_plural = _("service documents")
        ordering            = ["order"]
        indexes = [
            models.Index(
                fields=["service", "document_type"],
                name="idx_svcdocument_service_type",
            ),
        ]

    def __str__(self) -> str:
        t = self.safe_translation_getter("title", any_language=True) or ""
        return f"{self.service} — {t}"


class ServiceSLA(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    """
    Service-Level Agreement guarantee for enterprise-tier services.
    Displayed as trust signals on the service page to reassure
    enterprise clients about support commitments.
    """

    translations = TranslatedFields(
        guarantee_name = models.CharField(
            _("guarantee name"), max_length=200,
            help_text=_("e.g. 'Uptime Guarantee', 'Response Time SLA', '24/7 Support'."),
        ),
        value = models.CharField(
            _("value"), max_length=100,
            help_text=_("e.g. '99.9%', '< 4 hours', 'Always available'."),
        ),
        description = models.TextField(
            _("description"), blank=True,
            help_text=_("Detailed explanation of this SLA guarantee."),
        ),
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="slas",
        verbose_name=_("service"),
    )
    icon = models.CharField(
        _("icon"), max_length=100, blank=True,
        help_text=_("Icon identifier for the frontend, e.g. 'lucide:shield-check'."),
    )

    class Meta:
        verbose_name        = _("service SLA")
        verbose_name_plural = _("service SLAs")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["service", "order"], name="idx_svcsla_service_order"),
        ]

    def __str__(self) -> str:
        name = self.safe_translation_getter("guarantee_name", any_language=True) or ""
        val = self.safe_translation_getter("value", any_language=True) or ""
        return f"{self.service} — {name}: {val}"
