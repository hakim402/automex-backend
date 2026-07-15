from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.content.tests.factories import create_blog_post, create_case_study, create_service
from apps.core.models import APIKey, SEOSettings

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_with_key() -> APIClient:
    _, raw_key = APIKey.generate(name="test-frontend")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=raw_key)
    return client


# ──────────────────────────────────────────────────────────────────────────────
# SEOSettingsView
# ──────────────────────────────────────────────────────────────────────────────

def test_seo_settings_requires_api_key():
    client = APIClient()
    response = client.get("/api/v1/seo/settings/")
    assert response.status_code == 403


def test_seo_settings_returns_singleton_defaults(client_with_key):
    response = client_with_key.get("/api/v1/seo/settings/")
    assert response.status_code == 200
    assert "site_name" in response.data
    assert "organization" in response.data
    assert response.data["organization"]["legal_name"]


def test_seo_settings_reflects_saved_values(client_with_key):
    settings_obj = SEOSettings.get_solo()
    settings_obj.site_name = "AUTOMEX Custom"
    settings_obj.contact_email = "hello@automex.tech"
    settings_obj.save()

    response = client_with_key.get("/api/v1/seo/settings/")
    assert response.data["site_name"] == "AUTOMEX Custom"
    assert response.data["organization"]["contact_email"] == "hello@automex.tech"


# ──────────────────────────────────────────────────────────────────────────────
# SitemapURLsView
# ──────────────────────────────────────────────────────────────────────────────

def test_sitemap_urls_requires_api_key():
    client = APIClient()
    response = client.get("/api/v1/seo/sitemap-urls/")
    assert response.status_code == 403


def test_sitemap_urls_includes_published_content(client_with_key):
    create_service(slug="ai-development")
    create_case_study(slug="acme-rebuild")
    create_blog_post(slug="scaling-our-platform")

    response = client_with_key.get("/api/v1/seo/sitemap-urls/")
    paths = [entry["path"] for entry in response.data]

    assert "/services/ai-development/" in paths
    assert "/case-studies/acme-rebuild/" in paths
    assert "/blog/scaling-our-platform/" in paths


def test_sitemap_urls_excludes_unpublished(client_with_key):
    from apps.core.models import PublishableModel
    create_service(slug="draft-service", status=PublishableModel.Status.DRAFT, published=False)

    response = client_with_key.get("/api/v1/seo/sitemap-urls/")
    paths = [entry["path"] for entry in response.data]
    assert "/services/draft-service/" not in paths


def test_sitemap_urls_entry_shape(client_with_key):
    create_service(slug="ai-development")
    response = client_with_key.get("/api/v1/seo/sitemap-urls/")
    entry = response.data[0]
    assert set(entry.keys()) == {"path", "lastmod", "priority", "changefreq"}
