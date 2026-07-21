"""
apps/content/models/portfolio.py
────────────────────────────────────
Visual project portfolio for showcasing completed work with rich media
galleries, linked services/technologies, and industry categorization.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel


class PortfolioProject(UUIDModel, TimeStampedModel, OrderableModel):
    title = models.CharField(_("title"), max_length=250)
    slug = models.SlugField(_("slug"), max_length=270, unique=True)
    short_description = models.TextField(_("short description"), blank=True)

    cover_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("cover image"),
    )

    services = models.ManyToManyField(
        "content.Service", blank=True,
        related_name="portfolio_projects", verbose_name=_("services"),
    )
    technologies = models.ManyToManyField(
        "content.Technology", blank=True,
        related_name="portfolio_projects", verbose_name=_("technologies"),
    )
    industry = models.ForeignKey(
        "content.Industry",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="portfolio_projects", verbose_name=_("industry"),
    )

    project_url = models.URLField(_("project URL"), blank=True)
    client_name = models.CharField(_("client name"), max_length=200, blank=True)
    completion_year = models.PositiveIntegerField(_("completion year"), null=True, blank=True)

    is_featured = models.BooleanField(_("featured"), default=False, db_index=True)
    is_published = models.BooleanField(_("published"), default=True, db_index=True)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = _("portfolio project")
        verbose_name_plural = _("portfolio projects")

    def __str__(self) -> str:
        return self.title


class PortfolioGalleryImage(UUIDModel, TimeStampedModel, OrderableModel):
    project = models.ForeignKey(
        PortfolioProject,
        on_delete=models.CASCADE,
        related_name="gallery_images", verbose_name=_("project"),
    )
    image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("image"),
    )
    caption = models.CharField(_("caption"), max_length=300, blank=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("portfolio gallery image")
        verbose_name_plural = _("portfolio gallery images")

    def __str__(self) -> str:
        return f"{self.project.title} – image #{self.order}"
