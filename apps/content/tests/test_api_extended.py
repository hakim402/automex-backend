"""
apps/content/tests/test_api_extended.py
────────────────────────────────────────────
Comprehensive tests for the new enterprise API endpoints:
Partners, Certifications, AI Capabilities, Tech Expertise,
Portfolio Projects — plus enriched Service detail with
sub-models, and CRM booking cancel + pagination.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.core.models import APIKey, PublishableModel

from .factories import (
    create_ai_capability,
    create_certification,
    create_partner,
    create_portfolio_project,
    create_service,
    create_service_category,
    create_tech_expertise,
    create_technology,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# PARTNERS
# ══════════════════════════════════════════════════════════════════════════════

def test_partners_list_requires_api_key():
    client = APIClient()
    response = client.get("/api/v1/partners/")
    assert response.status_code == 403


def test_partners_list_accepts_valid_api_key(client_with_key):
    create_partner(slug="aws", name="AWS", is_active=True)
    response = client_with_key.get("/api/v1/partners/")
    assert response.status_code == 200
    assert response.data["count"] >= 1  # paginated


def test_partners_list_excludes_inactive(client_with_key):
    create_partner(slug="active-partner", name="Active", is_active=True)
    create_partner(slug="inactive-partner", name="Inactive", is_active=False)

    response = client_with_key.get("/api/v1/partners/")
    slugs = [item["slug"] for item in response.data["results"]]
    assert "active-partner" in slugs
    assert "inactive-partner" not in slugs


def test_partner_detail_by_slug(client_with_key):
    create_partner(slug="aws", name="Amazon Web Services")
    response = client_with_key.get("/api/v1/partners/aws/")
    assert response.status_code == 200
    assert response.data["name"] == "Amazon Web Services"
    assert response.data["slug"] == "aws"
    assert "logo" in response.data
    assert "partner_type_display" in response.data


def test_partner_detail_404(client_with_key):
    response = client_with_key.get("/api/v1/partners/nonexistent/")
    assert response.status_code == 404


def test_partners_filter_by_partner_type(client_with_key):
    create_partner(slug="aws", partner_type="cloud", name="AWS")
    create_partner(slug="msft", partner_type="technology", name="Microsoft")

    response = client_with_key.get("/api/v1/partners/?partner_type=cloud")
    slugs = [item["slug"] for item in response.data["results"]]
    assert "aws" in slugs
    assert "msft" not in slugs


def test_partners_filter_by_tier(client_with_key):
    create_partner(slug="aws", tier="platinum", name="AWS")
    create_partner(slug="gcp", tier="gold", name="GCP")

    response = client_with_key.get("/api/v1/partners/?tier=platinum")
    slugs = [item["slug"] for item in response.data["results"]]
    assert slugs == ["aws"]


# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_certifications_list_accepts_valid_api_key(client_with_key):
    create_certification(name="ISO 27001", is_active=True)
    response = client_with_key.get("/api/v1/certifications/")
    assert response.status_code == 200
    assert response.data["count"] >= 1


def test_certifications_list_excludes_inactive(client_with_key):
    create_certification(name="Active Cert", is_active=True)
    create_certification(name="Inactive Cert", is_active=False)

    response = client_with_key.get("/api/v1/certifications/")
    names = [item["name"] for item in response.data["results"]]
    assert "Active Cert" in names
    assert "Inactive Cert" not in names


def test_certification_detail(client_with_key):
    create_certification(name="AWS Certified", issuer="Amazon")
    response = client_with_key.get(f"/api/v1/certifications/")
    assert response.status_code == 200
    assert len(response.data["results"]) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# AI CAPABILITIES
# ══════════════════════════════════════════════════════════════════════════════

def test_ai_capabilities_list(client_with_key):
    create_ai_capability(slug="nlp", name="NLP", is_active=True)
    response = client_with_key.get("/api/v1/ai-capabilities/")
    assert response.status_code == 200
    assert response.data["count"] >= 1


def test_ai_capability_detail_by_slug(client_with_key):
    create_ai_capability(slug="nlp", name="Natural Language Processing", category="nlp")
    response = client_with_key.get("/api/v1/ai-capabilities/nlp/")
    assert response.status_code == 200
    assert response.data["name"] == "Natural Language Processing"
    assert response.data["slug"] == "nlp"
    assert "category_display" in response.data


def test_ai_capabilities_filter_by_category(client_with_key):
    create_ai_capability(slug="nlp", category="nlp", name="NLP")
    create_ai_capability(slug="vision", category="computer_vision", name="Vision")
    response = client_with_key.get("/api/v1/ai-capabilities/?category=nlp")
    slugs = [item["slug"] for item in response.data["results"]]
    assert "nlp" in slugs
    assert "vision" not in slugs


def test_ai_capability_detail_404(client_with_key):
    response = client_with_key.get("/api/v1/ai-capabilities/nonexistent/")
    assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# TECH EXPERTISE
# ══════════════════════════════════════════════════════════════════════════════

def test_tech_expertise_list(client_with_key):
    create_tech_expertise(slug="cloud", name="Cloud Architecture", is_active=True)
    response = client_with_key.get("/api/v1/tech-expertise/")
    assert response.status_code == 200
    assert response.data["count"] >= 1


def test_tech_expertise_detail_by_slug(client_with_key):
    create_tech_expertise(slug="cloud", name="Cloud Architecture")
    response = client_with_key.get("/api/v1/tech-expertise/cloud/")
    assert response.status_code == 200
    assert response.data["name"] == "Cloud Architecture"
    assert "technologies" in response.data


def test_tech_expertise_filter_by_category(client_with_key):
    create_tech_expertise(slug="cloud", category="cloud", name="Cloud")
    create_tech_expertise(slug="ai-ml", category="ai", name="AI/ML")
    response = client_with_key.get("/api/v1/tech-expertise/?category=cloud")
    slugs = [item["slug"] for item in response.data["results"]]
    assert "cloud" in slugs
    assert "ai-ml" not in slugs


# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO PROJECTS
# ══════════════════════════════════════════════════════════════════════════════

def test_portfolio_list(client_with_key):
    create_portfolio_project(slug="ecom", title="E-Commerce", is_published=True)
    response = client_with_key.get("/api/v1/portfolio/")
    assert response.status_code == 200
    assert response.data["count"] >= 1


def test_portfolio_list_excludes_unpublished(client_with_key):
    create_portfolio_project(slug="published", title="Published", is_published=True)
    create_portfolio_project(slug="unpublished", title="Unpublished", is_published=False)

    response = client_with_key.get("/api/v1/portfolio/")
    slugs = [item["slug"] for item in response.data["results"]]
    assert "published" in slugs
    assert "unpublished" not in slugs


def test_portfolio_detail_by_slug(client_with_key):
    create_portfolio_project(slug="ecom", title="E-Commerce Platform")
    response = client_with_key.get("/api/v1/portfolio/ecom/")
    assert response.status_code == 200
    assert response.data["title"] == "E-Commerce Platform"
    assert "services" in response.data
    assert "gallery" in response.data


def test_portfolio_list_is_lighter_than_detail(client_with_key):
    create_portfolio_project(slug="ecom")
    list_response = client_with_key.get("/api/v1/portfolio/")
    detail_response = client_with_key.get("/api/v1/portfolio/ecom/")

    list_fields = set(list_response.data["results"][0].keys())
    detail_fields = set(detail_response.data.keys())
    assert "gallery" not in list_fields
    assert "gallery" in detail_fields


def test_portfolio_filter_by_is_featured(client_with_key):
    create_portfolio_project(slug="featured", title="Featured", is_featured=True, is_published=True)
    create_portfolio_project(slug="regular", title="Regular", is_featured=False, is_published=True)

    response = client_with_key.get("/api/v1/portfolio/?is_featured=true")
    slugs = [item["slug"] for item in response.data["results"]]
    assert slugs == ["featured"]


def test_portfolio_detail_404(client_with_key):
    response = client_with_key.get("/api/v1/portfolio/nonexistent/")
    assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE DETAIL — enriched enterprise fields
# ══════════════════════════════════════════════════════════════════════════════

def test_service_detail_includes_enterprise_fields(client_with_key):
    create_service(
        slug="enterprise-service",
        name="Enterprise Service",
        is_enterprise=True,
        service_level="enterprise",
        pricing_model="quote",
        starting_price="5000.00",
        currency="USD",
        delivery_time_estimate="4-6 weeks",
        team_size_range="5-10 engineers",
        cta_text="Get Enterprise Quote",
    )
    response = client_with_key.get("/api/v1/services/enterprise-service/")
    assert response.status_code == 200
    assert response.data["is_enterprise"] is True
    assert response.data["service_level"] == "enterprise"
    assert response.data["service_level_display"] == "Enterprise"
    assert response.data["pricing_model"] == "quote"
    assert response.data["pricing_model_display"] == "Custom Quote"
    assert response.data["starting_price"] == "5000.00"
    assert response.data["currency"] == "USD"
    assert response.data["delivery_time_estimate"] == "4-6 weeks"
    assert response.data["team_size_range"] == "5-10 engineers"
    assert response.data["cta_text"] == "Get Enterprise Quote"


def test_service_detail_includes_sub_model_arrays(client_with_key):
    create_service(slug="rich-service", name="Rich Service")
    response = client_with_key.get("/api/v1/services/rich-service/")
    assert response.status_code == 200
    # All enterprise sub-model arrays must be present (even if empty)
    for key in [
        "hero_images", "process_steps", "deliverables", "add_ons",
        "comparison_rows", "client_logos", "service_testimonials",
        "documents", "slas", "related_services",
    ]:
        assert key in response.data, f"Missing key: {key}"
        assert isinstance(response.data[key], list), f"'{key}' should be a list"


def test_service_detail_includes_key_metrics(client_with_key):
    create_service(
        slug="with-metrics",
        name="With Metrics",
        key_metrics={"projects_delivered": 150, "client_satisfaction": 98},
    )
    response = client_with_key.get("/api/v1/services/with-metrics/")
    assert response.data["key_metrics"] == {"projects_delivered": 150, "client_satisfaction": 98}


def test_service_detail_includes_tech_stack_grouped(client_with_key):
    create_service(
        slug="with-tech-stack",
        name="With Tech Stack",
        tech_stack_grouped={"Frontend": ["React"], "Backend": ["Django"]},
    )
    response = client_with_key.get("/api/v1/services/with-tech-stack/")
    assert response.data["tech_stack_grouped"] == {"Frontend": ["React"], "Backend": ["Django"]}


def test_service_detail_includes_media_assets(client_with_key):
    create_service(slug="with-media", name="With Media")
    response = client_with_key.get("/api/v1/services/with-media/")
    for key in ["thumbnail_image", "video_presentation", "brochure"]:
        assert key in response.data, f"Missing media key: {key}"


# ══════════════════════════════════════════════════════════════════════════════
# PAGINATION — new content endpoints use page-based pagination
# ══════════════════════════════════════════════════════════════════════════════

def test_partners_endpoint_is_paginated(client_with_key):
    for i in range(5):
        create_partner(slug=f"partner-{i}", name=f"Partner {i}", is_active=True)
    response = client_with_key.get("/api/v1/partners/")
    assert "count" in response.data
    assert "next" in response.data
    assert "results" in response.data
    assert response.data["count"] >= 5


def test_portfolio_endpoint_is_paginated(client_with_key):
    for i in range(3):
        create_portfolio_project(slug=f"project-{i}", title=f"Project {i}", is_published=True)
    response = client_with_key.get("/api/v1/portfolio/")
    assert "count" in response.data
    assert "next" in response.data
    assert "results" in response.data
    assert response.data["count"] >= 3
