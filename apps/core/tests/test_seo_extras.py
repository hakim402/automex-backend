from __future__ import annotations

import pytest
from django.test import Client

from apps.content.tests.factories import create_blog_post, create_case_study, create_service
from apps.core.models import Redirect

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> Client:
    return Client()


# ──────────────────────────────────────────────────────────────────────────────
# sitemap.xml
# ──────────────────────────────────────────────────────────────────────────────

def test_sitemap_returns_200_and_xml_content_type(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response["Content-Type"]


def test_sitemap_includes_published_service(client):
    create_service(slug="ai-development", name="Artificial Intelligence")
    response = client.get("/sitemap.xml")
    content = response.content.decode()
    assert "/services/ai-development/" in content


def test_sitemap_uses_frontend_domain_not_django_host(client, settings):
    create_service(slug="ai-development")
    response = client.get("/sitemap.xml")  # Django test client's default host is "testserver"
    content = response.content.decode()

    assert "testserver" not in content
    assert settings.FRONTEND_BASE_URL.split("//")[1] in content


def test_sitemap_excludes_unpublished_service(client):
    from apps.core.models import PublishableModel
    create_service(slug="draft-service", status=PublishableModel.Status.DRAFT, published=False)

    response = client.get("/sitemap.xml")
    assert "/services/draft-service/" not in response.content.decode()


def test_sitemap_includes_case_studies_and_blog_posts(client):
    create_case_study(slug="acme-rebuild")
    create_blog_post(slug="scaling-our-platform")

    content = client.get("/sitemap.xml").content.decode()
    assert "/case-studies/acme-rebuild/" in content
    assert "/blog/scaling-our-platform/" in content


def test_sitemap_includes_static_pages(client):
    content = client.get("/sitemap.xml").content.decode()
    assert "/services/</loc>" in content or "/services/\"" in content or "services/<" in content


# ──────────────────────────────────────────────────────────────────────────────
# robots.txt
# ──────────────────────────────────────────────────────────────────────────────

def test_robots_txt_returns_200_and_plain_text(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")


def test_robots_txt_disallows_admin_path(client, settings):
    content = client.get("/robots.txt").content.decode()
    assert f"Disallow: /{settings.ADMIN_URL_PATH}" in content


def test_robots_txt_references_sitemap(client):
    content = client.get("/robots.txt").content.decode()
    assert "Sitemap:" in content
    assert "/sitemap.xml" in content


# ──────────────────────────────────────────────────────────────────────────────
# Redirect middleware
# ──────────────────────────────────────────────────────────────────────────────

def test_permanent_redirect_returns_301(client):
    Redirect.objects.create(old_path="/old-page/", new_path="/new-page/", is_permanent=True, is_active=True)
    response = client.get("/old-page/")
    assert response.status_code == 301
    assert response["Location"] == "/new-page/"


def test_temporary_redirect_returns_302(client):
    Redirect.objects.create(old_path="/temp/", new_path="/somewhere/", is_permanent=False, is_active=True)
    response = client.get("/temp/")
    assert response.status_code == 302


def test_inactive_redirect_is_not_followed(client):
    Redirect.objects.create(old_path="/inactive/", new_path="/somewhere/", is_active=False)
    response = client.get("/inactive/")
    assert response.status_code == 404


def test_nonexistent_path_without_redirect_still_404s(client):
    response = client.get("/this-path-has-no-redirect-configured/")
    assert response.status_code == 404


def test_redirect_increments_hit_count(client):
    redirect = Redirect.objects.create(old_path="/counted/", new_path="/target/", is_active=True)
    assert redirect.hit_count == 0

    client.get("/counted/")
    client.get("/counted/")

    redirect.refresh_from_db()
    assert redirect.hit_count == 2


def test_successful_requests_are_not_affected_by_redirect_middleware(client):
    """A 200 response should never trigger a redirect lookup/rewrite."""
    Redirect.objects.create(old_path="/robots.txt", new_path="/somewhere-else/", is_active=True)
    response = client.get("/robots.txt")
    # /robots.txt resolves successfully (200), so the redirect must never apply
    # even though a matching row exists — middleware only acts on 404s.
    assert response.status_code == 200
