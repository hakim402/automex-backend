"""
apps/core/models/revision.py
────────────────────────────────
Generic revision history for any PublishableModel, written by the service
layer on every status transition (submit, approve, reject, publish, edit).
Enables diffing between versions and rollback from the admin.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import TimeStampedModel, UUIDModel


class ContentRevision(UUIDModel, TimeStampedModel):
    """
    `object_id` is a UUIDField (not the generic PositiveIntegerField default)
    because every content model in this project uses a UUID primary key.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("content type"),
    )
    object_id      = models.UUIDField(_("object id"))
    content_object = GenericForeignKey("content_type", "object_id")

    version            = models.PositiveIntegerField(_("version"))
    status_at_snapshot = models.CharField(_("status at snapshot"), max_length=20)
    snapshot           = models.JSONField(_("snapshot data"), default=dict, blank=True)
    change_summary     = models.CharField(_("change summary"), max_length=500, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("created by"),
    )

    class Meta:
        ordering            = ["-created_at"]
        verbose_name        = _("content revision")
        verbose_name_plural = _("content revisions")
        indexes = [
            models.Index(fields=["content_type", "object_id"], name="idx_revision_object"),
            models.Index(fields=["content_type", "object_id", "version"], name="idx_revision_obj_version"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "version"],
                name="uq_revision_object_version",
            ),
        ]

    def __str__(self) -> str:
        return f"Revision v{self.version} of {self.content_type}({self.object_id})"
