from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.models import APIKey, PublishableModel

from .factories import (
    create_blog_post,
    create_case_study,
    create_faq,
    create_service,
    create_service_category,
    create_technology,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def raw_api_key() -> str:
    _, raw_key = APIKey.generate(name="test-frontend")
    return raw_key


@pytest.fixture
def client_with_key(raw_api_key) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=raw_api_key)
    return client


# ──────────────────────────────────────────────────────────────────────────────
# API key enforcement
# ──────────────────────────────────────────────────────────────────────────────

def test_services_list_requires_api_key():
    client = APIClient()  # no X-API-Key header
    response = client.get("/api/v1/services/")
    assert response.status_code == 403


def test_services_list_rejects_invalid_api_key():
    client = APIClient()
    client.credentials(HTTP_X_API_KEY="not-a-real-key")
    response = client.get("/api/v1/services/")
    assert response.status_code == 403


def test_services_list_accepts_valid_api_key(client_with_key):
    create_service()
    response = client_with_key.get("/api/v1/services/")
    assert response.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# Services — published-only, list vs. detail shape
# ──────────────────────────────────────────────────────────────────────────────

def test_services_list_only_returns_published(client_with_key):
    create_service(slug="published-service", status=PublishableModel.Status.PUBLISHED)
    create_service(slug="draft-service", status=PublishableModel.Status.DRAFT, published=False)

    response = client_with_key.get("/api/v1/services/")
    slugs = [item["slug"] for item in response.data["results"]]

    assert "published-service" in slugs
    assert "draft-service" not in slugs


def test_service_detail_by_slug(client_with_key):
    create_service(slug="ai-development", name="Artificial Intelligence")
    response = client_with_key.get("/api/v1/services/ai-development/")

    assert response.status_code == 200
    assert response.data["slug"] == "ai-development"
    assert response.data["name"] == "Artificial Intelligence"
    assert "seo" in response.data
    assert response.data["seo"]["structured_data_type"] == "Service"


def test_service_detail_404_for_unpublished(client_with_key):
    create_service(slug="hidden-service", status=PublishableModel.Status.DRAFT, published=False)
    response = client_with_key.get("/api/v1/services/hidden-service/")
    assert response.status_code == 404


def test_service_list_serializer_is_lighter_than_detail(client_with_key):
    create_service(slug="lightweight-check")
    list_response = client_with_key.get("/api/v1/services/")
    detail_response = client_with_key.get("/api/v1/services/lightweight-check/")

    list_fields = set(list_response.data["results"][0].keys())
    detail_fields = set(detail_response.data.keys())

    assert "overview" not in list_fields
    assert "overview" in detail_fields


def test_service_faqs_are_nested_in_detail(client_with_key):
    service = create_service(slug="service-with-faqs")
    create_faq(service=service, question="How long does it take?")
    create_faq(service=None, question="Global FAQ — should not appear here")

    response = client_with_key.get("/api/v1/services/service-with-faqs/")
    questions = [faq["question"] for faq in response.data["faqs"]]

    assert "How long does it take?" in questions
    assert "Global FAQ — should not appear here" not in questions


# ──────────────────────────────────────────────────────────────────────────────
# Filtering
# ──────────────────────────────────────────────────────────────────────────────

def test_services_filter_by_category(client_with_key):
    cat_a = create_service_category(name="AI", slug="ai")
    cat_b = create_service_category(name="Cloud", slug="cloud")
    create_service(slug="ai-service", category=cat_a)
    create_service(slug="cloud-service", category=cat_b)

    response = client_with_key.get("/api/v1/services/?category=ai")
    slugs = [item["slug"] for item in response.data["results"]]

    assert slugs == ["ai-service"]


def test_services_filter_by_technology(client_with_key):
    tech = create_technology(name="Kubernetes", slug="kubernetes")
    service = create_service(slug="devops-service")
    service.technologies.add(tech)
    create_service(slug="unrelated-service")

    response = client_with_key.get("/api/v1/services/?technology=kubernetes")
    slugs = [item["slug"] for item in response.data["results"]]

    assert slugs == ["devops-service"]


def test_services_filter_by_is_featured(client_with_key):
    create_service(slug="featured-service", is_featured=True)
    create_service(slug="regular-service", is_featured=False)

    response = client_with_key.get("/api/v1/services/?is_featured=true")
    slugs = [item["slug"] for item in response.data["results"]]

    assert slugs == ["featured-service"]


# ──────────────────────────────────────────────────────────────────────────────
# Language resolution end-to-end
# ──────────────────────────────────────────────────────────────────────────────

def test_service_detail_respects_lang_query_param(client_with_key):
    service = create_service(language_code="en", slug="multilingual-service", name="English Name")
    service.set_current_language("es")
    service.name = "Nombre en Espanol"
    service.slug = "multilingual-service"
    service.short_description = "Corto"
    service.save()

    response_en = client_with_key.get("/api/v1/services/multilingual-service/?lang=en")
    response_es = client_with_key.get("/api/v1/services/multilingual-service/?lang=es")

    assert response_en.data["name"] == "English Name"
    assert response_es.data["name"] == "Nombre en Espanol"


def test_service_list_lang_query_param_takes_priority_over_accept_language_header(client_with_key):
    service = create_service(language_code="en", slug="priority-check", name="English Name")
    service.set_current_language("de")
    service.name = "Deutscher Name"
    service.slug = "priority-check"
    service.short_description = "Kurz"
    service.save()

    response = client_with_key.get(
        "/api/v1/services/priority-check/?lang=de",
        HTTP_ACCEPT_LANGUAGE="en",
    )
    assert response.data["name"] == "Deutscher Name"


# ──────────────────────────────────────────────────────────────────────────────
# Case studies & blog — smoke tests (same pattern as services)
# ──────────────────────────────────────────────────────────────────────────────

def test_case_study_list_and_detail(client_with_key):
    create_case_study(slug="acme-rebuild", title="Acme Rebuild")

    list_response = client_with_key.get("/api/v1/case-studies/")
    assert list_response.status_code == 200
    assert len(list_response.data["results"]) == 1

    detail_response = client_with_key.get("/api/v1/case-studies/acme-rebuild/")
    assert detail_response.status_code == 200
    assert detail_response.data["title"] == "Acme Rebuild"
    assert detail_response.data["seo"]["structured_data_type"] == "Article"


def test_blog_post_list_and_detail(client_with_key):
    create_blog_post(slug="scaling-our-platform", title="Scaling Our Platform")

    list_response = client_with_key.get("/api/v1/blog/posts/")
    assert list_response.status_code == 200
    assert len(list_response.data["results"]) == 1

    detail_response = client_with_key.get("/api/v1/blog/posts/scaling-our-platform/")
    assert detail_response.status_code == 200
    assert detail_response.data["title"] == "Scaling Our Platform"
    assert "content" in detail_response.data


def test_blog_post_list_excludes_draft(client_with_key):
    create_blog_post(slug="published-post", status=PublishableModel.Status.PUBLISHED)
    create_blog_post(slug="draft-post", status=PublishableModel.Status.DRAFT, published=False)

    response = client_with_key.get("/api/v1/blog/posts/")
    slugs = [item["slug"] for item in response.data["results"]]

    assert "published-post" in slugs
    assert "draft-post" not in slugs
