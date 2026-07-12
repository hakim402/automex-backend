"""
apps/core/models/base.py
───────────────────────────
Shared abstract base models used across every AUTOMEX app. Mirrors the
conventions already established in apps.accounts (UUID primary keys,
timezone-aware timestamps, verbose_name everywhere) so the whole codebase
feels like one system.

Nothing here is tenant-scoped — AUTOMEX content is single-tenant by design
decision. apps.accounts.Tenant remains reserved for future white-label
reuse if ever needed.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def uuid_pk() -> models.UUIDField:
    """Shared UUID primary-key definition (mirrors apps.accounts convention)."""
    return models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)


class UUIDModel(models.Model):
    """Abstract base providing a UUID primary key."""

    id = uuid_pk()

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract base providing created_at / updated_at timestamps."""

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Default manager still returns everything; call .alive()/.dead() to scope explicitly."""

    def get_queryset(self) -> SoftDeleteQuerySet:
        return SoftDeleteQuerySet(self.model, using=self._db)

    def alive(self):
        return self.get_queryset().alive()

    def dead(self):
        return self.get_queryset().dead()


class SoftDeleteModel(models.Model):
    """Abstract base providing soft-delete semantics."""

    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+",
        verbose_name=_("deleted by"),
    )

    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, deleted_by=None) -> None:
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.save(update_fields=["deleted_at", "deleted_by"])

    def restore(self) -> None:
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["deleted_at", "deleted_by"])


class OrderableModel(models.Model):
    """Abstract base providing a manual display-order field."""

    order = models.PositiveIntegerField(_("display order"), default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["order"]


class PublishableModel(models.Model):
    """
    Full editorial workflow:

        draft → in_review → approved → published
                     │            │
                     └── rejected ┘  (sends back to draft for edits)

    Fields here are language-independent — translated content lives in each
    model's own `TranslatedFields(...)` block (see core.models.seo for the
    matching translated SEO fields).
    """

    class Status(models.TextChoices):
        DRAFT     = "draft",     _("Draft")
        IN_REVIEW = "in_review", _("In Review")
        APPROVED  = "approved",  _("Approved")
        PUBLISHED = "published", _("Published")
        REJECTED  = "rejected",  _("Rejected")
        ARCHIVED  = "archived",  _("Archived")

    status = models.CharField(
        _("status"), max_length=20,
        choices=Status.choices, default=Status.DRAFT, db_index=True,
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("submitted by"),
    )
    submitted_at = models.DateTimeField(_("submitted for review at"), null=True, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("reviewed by"),
    )
    reviewed_at      = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    rejection_reason = models.TextField(_("rejection reason"), blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("approved by"),
    )
    approved_at = models.DateTimeField(_("approved at"), null=True, blank=True)

    published_at = models.DateTimeField(_("published at"), null=True, blank=True, db_index=True)
    version      = models.PositiveIntegerField(_("version"), default=1)

    class Meta:
        abstract = True

    @property
    def is_published(self) -> bool:
        return (
            self.status == self.Status.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )
