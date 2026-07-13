"""
apps/core/models/media.py
────────────────────────────
Centralized media asset library. Every image/video/document used across
Content and SEO (OG images, hero images, galleries, logos) is uploaded once
here and referenced by FK, instead of each model managing its own
ImageField — avoids duplicate uploads and gives editors one place to manage
assets (alt text, captions, replacements).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimeStampedModel, UUIDModel
from apps.core.validators import validate_media_file_extension, validate_media_file_size


class MediaAsset(UUIDModel, TimeStampedModel):
    class FileType(models.TextChoices):
        IMAGE    = "image",    _("Image")
        VIDEO    = "video",    _("Video")
        DOCUMENT = "document", _("Document")
        AUDIO    = "audio",    _("Audio")
        OTHER    = "other",    _("Other")

    title      = models.CharField(_("title"), max_length=255, blank=True)
    file       = models.FileField(
        _("file"), upload_to="media_library/%Y/%m/",
        validators=[validate_media_file_extension, validate_media_file_size],
    )
    file_type  = models.CharField(
        _("file type"), max_length=20, choices=FileType.choices, db_index=True,
    )
    mime_type  = models.CharField(_("MIME type"), max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(_("size (bytes)"), null=True, blank=True)

    # Populated on upload for images only.
    width  = models.PositiveIntegerField(_("width (px)"), null=True, blank=True)
    height = models.PositiveIntegerField(_("height (px)"), null=True, blank=True)

    alt_text = models.CharField(_("alt text"), max_length=255, blank=True)
    caption  = models.CharField(_("caption"), max_length=500, blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_media", verbose_name=_("uploaded by"),
    )
    tags = models.JSONField(_("tags"), default=list, blank=True)

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("media asset")
        verbose_name_plural = _("media assets")
        indexes = [
            models.Index(fields=["file_type"], name="idx_media_file_type"),
        ]

    def __str__(self) -> str:
        return self.title or self.file.name
