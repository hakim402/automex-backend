"""
apps/core/models/__init__.py
────────────────────────────────
Re-exports every shared abstraction so other apps can do:

    from apps.core.models import UUIDModel, TimeStampedModel, PublishableModel
"""
from .base import (
    OrderableModel,
    PublishableModel,
    SoftDeleteManager,
    SoftDeleteModel,
    SoftDeleteQuerySet,
    TimeStampedModel,
    UUIDModel,
    uuid_pk,
)
from .api_key import APIKey
from .managers import PublishableTranslatableManager, PublishableTranslatableQuerySet
from .media import MediaAsset
from .revision import ContentRevision
from .seo import Redirect, SEOFieldsMixin, SEOSettings, seo_translated_fields

__all__ = [
    "uuid_pk",
    "UUIDModel",
    "TimeStampedModel",
    "SoftDeleteModel",
    "SoftDeleteManager",
    "SoftDeleteQuerySet",
    "OrderableModel",
    "PublishableModel",
    "PublishableTranslatableManager",
    "PublishableTranslatableQuerySet",
    "ContentRevision",
    "MediaAsset",
    "APIKey",
    "seo_translated_fields",
    "SEOFieldsMixin",
    "SEOSettings",
    "Redirect",
]
