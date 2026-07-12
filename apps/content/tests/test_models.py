from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.content.models import Service
from apps.core.models import PublishableModel

from .factories import create_case_study, create_faq, create_service, create_service_category

pytestmark = pytest.mark.django_db


# ──────────────────────────────────────────────────────────────────────────────
# PublishableModel.is_published
# ──────────────────────────────────────────────────────────────────────────────

def test_service_is_published_true_when_published_and_past():
    service = create_service()
    assert service.is_published is True


def test_service_is_published_false_when_status_is_draft():
    service = create_service(status=PublishableModel.Status.DRAFT, published=False)
    assert service.is_published is False


def test_service_is_published_false_when_published_at_in_future():
    service = create_service(
        status=PublishableModel.Status.PUBLISHED,
        published=False,
        published_at=timezone.now() + timedelta(days=1),
    )
    assert service.is_published is False


# ──────────────────────────────────────────────────────────────────────────────
# PublishableTranslatableManager.published()
# ──────────────────────────────────────────────────────────────────────────────

def test_published_manager_excludes_draft_services():
    create_service(slug="published-one", status=PublishableModel.Status.PUBLISHED)
    create_service(slug="draft-one", status=PublishableModel.Status.DRAFT, published=False)

    published_slugs = list(
        Service.objects.published().language("en").values_list("translations__slug", flat=True)
    )
    assert "published-one" in published_slugs
    assert "draft-one" not in published_slugs


def test_published_manager_excludes_future_scheduled_content():
    create_service(
        slug="future-service",
        status=PublishableModel.Status.PUBLISHED,
        published=False,
        published_at=timezone.now() + timedelta(days=7),
    )
    assert not Service.objects.published().filter(translations__slug="future-service").exists()


# ──────────────────────────────────────────────────────────────────────────────
# SEOFieldsMixin
# ──────────────────────────────────────────────────────────────────────────────

def test_robots_meta_content_default_is_index_follow():
    service = create_service()
    assert service.robots_meta_content == "index, follow"


def test_robots_meta_content_respects_noindex():
    service = create_service(robots_index=False, robots_follow=False)
    assert service.robots_meta_content == "noindex, nofollow"


def test_service_structured_data_type_auto_set_on_save():
    service = create_service()
    assert service.structured_data_type == "Service"


def test_case_study_structured_data_type_auto_set_on_save():
    case_study = create_case_study()
    assert case_study.structured_data_type == "Article"


# ──────────────────────────────────────────────────────────────────────────────
# Translations (django-parler)
# ──────────────────────────────────────────────────────────────────────────────

def test_service_supports_multiple_language_translations():
    service = create_service(language_code="en", name="Custom Software", slug="custom-software")
    service.set_current_language("es")
    service.name = "Software a Medida"
    service.slug = "software-a-medida"
    service.short_description = "Descripcion corta."
    service.save()

    service.set_current_language("en")
    assert service.name == "Custom Software"
    service.set_current_language("es")
    assert service.name == "Software a Medida"


def test_service_falls_back_to_default_language_when_translation_missing():
    service = create_service(language_code="en", name="Cloud & DevOps")
    # No French translation was ever created for this instance.
    fallback_name = service.safe_translation_getter("name", language_code="fr", any_language=True)
    assert fallback_name == "Cloud & DevOps"


# ──────────────────────────────────────────────────────────────────────────────
# FAQ scoping
# ──────────────────────────────────────────────────────────────────────────────

def test_faq_can_be_global_or_service_specific():
    category = create_service_category()
    service = create_service(category=category)
    global_faq = create_faq(service=None, question="Do you sign NDAs?")
    service_faq = create_faq(service=service, question="What does this service include?")

    assert global_faq.service is None
    assert service_faq.service_id == service.id
