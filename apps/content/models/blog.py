"""
apps/content/models/blog.py
───────────────────────────────
Blog / Insights content — thought leadership platform for AUTOMEX.
Supports multiple content types, hero image galleries, video embeds,
premium gated content, dedicated author profiles, and cross-linking
to services and case studies.
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
    icon        = models.CharField(
        _("icon"), max_length=100, blank=True,
        help_text=_("Icon identifier for the frontend, e.g. 'lucide:book-open'."),
    )
    is_active   = models.BooleanField(_("active"), default=True, db_index=True)

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


class BlogAuthor(UUIDModel, TimeStampedModel):
    """
    Dedicated author profile for blog posts. Separate from the User model
    to support external contributors, guest writers, and public-facing
    bylines with rich profile data.
    """

    full_name = models.CharField(_("full name"), max_length=200)
    slug      = models.SlugField(_("slug"), max_length=220, unique=True)
    bio       = models.TextField(_("bio"), blank=True)
    avatar    = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("avatar"),
    )
    role_title = models.CharField(_("role title"), max_length=200, blank=True)
    email      = models.EmailField(_("email"), blank=True)
    linkedin_url = models.URLField(_("LinkedIn URL"), blank=True)
    github_url   = models.URLField(_("GitHub URL"), blank=True)
    is_active    = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering            = ["full_name"]
        verbose_name        = _("blog author")
        verbose_name_plural = _("blog authors")

    def __str__(self) -> str:
        return self.full_name


class BlogPost(TranslatableModel, UUIDModel, TimeStampedModel, PublishableModel, SEOFieldsMixin):
    class ContentType(models.TextChoices):
        ARTICLE    = "article",    _("Article")
        TUTORIAL   = "tutorial",   _("Tutorial")
        CASE_STUDY = "case_study", _("Case Study Summary")
        WHITEPAPER = "whitepaper", _("Whitepaper")
        NEWS       = "news",       _("News")
        VIDEO_POST = "video_post", _("Video Post")

    translations = TranslatedFields(
        title    = models.CharField(_("title"), max_length=250),
        slug     = models.SlugField(_("slug"), max_length=270, db_index=True),
        excerpt  = models.CharField(_("excerpt"), max_length=400, blank=True),
        content  = models.TextField(_("content")),
        **seo_translated_fields(),
        meta={"unique_together": [("language_code", "slug")]},
    )

    # ── Author ────────────────────────────────────────────────────────────────
    author = models.ForeignKey(
        BlogAuthor,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="blog_posts", verbose_name=_("author"),
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="posts", verbose_name=_("category"),
    )
    tags = models.ManyToManyField(BlogTag, blank=True, related_name="posts", verbose_name=_("tags"))

    # ── Media ─────────────────────────────────────────────────────────────────
    cover_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("cover image"),
    )
    thumbnail_image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("thumbnail image"),
        help_text=_("Small image used in cards, grids, and listing pages."),
    )
    video_embed_url = models.URLField(
        _("video embed URL"), blank=True,
        help_text=_("YouTube or Vimeo embed URL for video posts."),
    )

    # ── Content classification ────────────────────────────────────────────────
    content_type = models.CharField(
        _("content type"), max_length=20,
        choices=ContentType.choices, default=ContentType.ARTICLE,
        db_index=True,
    )
    is_premium = models.BooleanField(
        _("premium content"), default=False, db_index=True,
        help_text=_("If True, this content is gated for lead generation."),
    )

    # ── Cross-linking ─────────────────────────────────────────────────────────
    related_case_studies = models.ManyToManyField(
        "content.CaseStudy", blank=True,
        related_name="related_blog_posts", verbose_name=_("related case studies"),
    )
    related_services = models.ManyToManyField(
        "content.Service", blank=True,
        related_name="related_blog_posts", verbose_name=_("related services"),
    )

    # ── External / Syndication ────────────────────────────────────────────────
    external_url = models.URLField(
        _("external URL"), blank=True,
        help_text=_("For Medium/LinkedIn cross-posts — the original article URL."),
    )

    # ── Analytics ─────────────────────────────────────────────────────────────
    reading_time_minutes = models.PositiveSmallIntegerField(_("reading time (minutes)"), null=True, blank=True)
    views_count           = models.PositiveIntegerField(_("views count"), default=0)
    is_featured            = models.BooleanField(_("featured"), default=False, db_index=True)

    objects = PublishableTranslatableManager()

    class Meta:
        verbose_name        = _("blog post")
        verbose_name_plural = _("blog posts")
        ordering             = ["-published_at"]
        indexes = [
            models.Index(fields=["content_type", "is_premium"], name="idx_blogpost_type_premium"),
        ]

    def __str__(self) -> str:
        return self.safe_translation_getter("title", any_language=True) or str(self.id)

    def save(self, *args, **kwargs):
        if not self.structured_data_type:
            self.structured_data_type = "BlogPosting"
        super().save(*args, **kwargs)


class BlogHeroImage(UUIDModel, TimeStampedModel, OrderableModel):
    """
    Multiple hero/hero-section images for a blog post.
    Supports a gallery/carousel at the top of the article.
    """

    blog_post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="hero_images",
        verbose_name=_("blog post"),
    )
    image = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("image"),
    )
    caption = models.CharField(
        _("caption"), max_length=255, blank=True,
        help_text=_("Optional caption or overlay text."),
    )
    is_cover = models.BooleanField(
        _("cover image"), default=False,
        help_text=_("If set, this image is the primary cover for the post."),
    )

    class Meta:
        verbose_name        = _("blog hero image")
        verbose_name_plural = _("blog hero images")
        ordering            = ["order"]
        indexes = [
            models.Index(fields=["blog_post", "order"], name="idx_bloghero_post_order"),
        ]

    def __str__(self) -> str:
        return f"Hero image for '{self.blog_post}' (order={self.order})"
