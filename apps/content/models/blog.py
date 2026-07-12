"""
apps/content/models/blog.py
───────────────────────────────
Blog / Insights content, listed as a required Future in the AUTOMEX MVP doc.
"""
from __future__ import annotations

from django.conf import settings
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


class BlogCategory(UUIDModel, TimeStampedModel, OrderableModel):
    name        = models.CharField(_("name"), max_length=150)
    slug        = models.SlugField(_("slug"), max_length=170, unique=True)
    description = models.TextField(_("description"), blank=True)

    class Meta:
        ordering            = ["order", "name"]
        verbose_name        = _("blog category")
        verbose_name_plural = _("blog categories")

    def __str__(self) -> str:
        return self.name


class BlogTag(UUIDModel, TimeStampedModel):
    name = models.CharField(_("name"), max_length=80)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)

    class Meta:
        ordering            = ["name"]
        verbose_name        = _("blog tag")
        verbose_name_plural = _("blog tags")

    def __str__(self) -> str:
        return self.name


class BlogPost(TranslatableModel, UUIDModel, TimeStampedModel, PublishableModel, SEOFieldsMixin):
    translations = TranslatedFields(
        title    = models.CharField(_("title"), max_length=250),
        slug     = models.SlugField(_("slug"), max_length=270, db_index=True),
        excerpt  = models.CharField(_("excerpt"), max_length=400, blank=True),
        content  = models.TextField(_("content")),
        **seo_translated_fields(),
        meta={"unique_together": [("language_code", "slug")]},
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="blog_posts", verbose_name=_("author"),
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="posts", verbose_name=_("category"),
    )
    tags = models.ManyToManyField(BlogTag, blank=True, related_name="posts", verbose_name=_("tags"))

    cover_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("cover image"),
    )

    reading_time_minutes = models.PositiveSmallIntegerField(_("reading time (minutes)"), null=True, blank=True)
    views_count           = models.PositiveIntegerField(_("views count"), default=0)
    is_featured            = models.BooleanField(_("featured"), default=False, db_index=True)

    objects = PublishableTranslatableManager()

    class Meta:
        verbose_name        = _("blog post")
        verbose_name_plural = _("blog posts")
        ordering             = ["-published_at"]

    def __str__(self) -> str:
        return self.safe_translation_getter("title", any_language=True) or str(self.id)

    def save(self, *args, **kwargs):
        if not self.structured_data_type:
            self.structured_data_type = "BlogPosting"
        super().save(*args, **kwargs)
