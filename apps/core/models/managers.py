"""
apps/core/models/managers.py
─────────────────────────────────
Combines django-parler's TranslatableManager/QuerySet with a `.published()`
scope, for content models that are both TranslatableModel and
PublishableModel (Service, CaseStudy, BlogPost).

Usage
-----
    class Service(TranslatableModel, UUIDModel, TimeStampedModel,
                   OrderableModel, PublishableModel, SEOFieldsMixin):
        ...
        objects = PublishableTranslatableManager()

    Service.objects.published().language("fr")
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone
from parler.managers import TranslatableQuerySet

from .base import PublishableModel


class PublishableTranslatableQuerySet(TranslatableQuerySet):
    def published(self):
        return self.filter(
            status=PublishableModel.Status.PUBLISHED,
            published_at__lte=timezone.now(),
        )


# Built the same way parler builds its own TranslatableManager (Manager.from_queryset),
# so every public TranslatableQuerySet method (.language(), .translated(), ...) is
# proxied onto the manager automatically, alongside our own .published().
PublishableTranslatableManager = models.Manager.from_queryset(PublishableTranslatableQuerySet)
