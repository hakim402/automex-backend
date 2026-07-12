from __future__ import annotations

import pytest
from django.test import RequestFactory
from django.utils import timezone
from datetime import timedelta

from apps.core.models import APIKey
from apps.core.permissions import HasValidAPIKey
from apps.core.utils.language import resolve_language

pytestmark = pytest.mark.django_db


# ──────────────────────────────────────────────────────────────────────────────
# APIKey.generate() / hashing
# ──────────────────────────────────────────────────────────────────────────────

def test_generate_returns_instance_and_raw_key_and_only_hash_is_stored():
    instance, raw_key = APIKey.generate(name="test-frontend")

    assert instance.key_hash == APIKey.hash_raw_key(raw_key)
    assert instance.prefix == raw_key[:8]
    assert instance.is_active is True
    # The raw key itself must never be persisted anywhere on the row.
    assert raw_key not in instance.__dict__.values()


def test_hash_raw_key_is_deterministic():
    assert APIKey.hash_raw_key("same-value") == APIKey.hash_raw_key("same-value")


def test_hash_raw_key_differs_for_different_input():
    assert APIKey.hash_raw_key("value-a") != APIKey.hash_raw_key("value-b")


# ──────────────────────────────────────────────────────────────────────────────
# HasValidAPIKey permission
# ──────────────────────────────────────────────────────────────────────────────

def _request_with_header(raw_key: str | None):
    rf = RequestFactory()
    headers = {"HTTP_X_API_KEY": raw_key} if raw_key else {}
    return rf.get("/api/v1/services/", **headers)


def test_permission_denies_when_header_missing():
    request = _request_with_header(None)
    assert HasValidAPIKey().has_permission(request, None) is False


def test_permission_denies_invalid_key():
    request = _request_with_header("not-a-real-key")
    assert HasValidAPIKey().has_permission(request, None) is False


def test_permission_allows_valid_active_key():
    _, raw_key = APIKey.generate(name="test-frontend")
    request = _request_with_header(raw_key)
    assert HasValidAPIKey().has_permission(request, None) is True


def test_permission_denies_inactive_key():
    instance, raw_key = APIKey.generate(name="test-frontend")
    instance.is_active = False
    instance.save(update_fields=["is_active"])

    request = _request_with_header(raw_key)
    assert HasValidAPIKey().has_permission(request, None) is False


def test_permission_denies_expired_key():
    instance, raw_key = APIKey.generate(name="test-frontend")
    instance.expires_at = timezone.now() - timedelta(days=1)
    instance.save(update_fields=["expires_at"])

    request = _request_with_header(raw_key)
    assert HasValidAPIKey().has_permission(request, None) is False


def test_permission_updates_last_used_at_on_success():
    instance, raw_key = APIKey.generate(name="test-frontend")
    assert instance.last_used_at is None

    request = _request_with_header(raw_key)
    HasValidAPIKey().has_permission(request, None)

    instance.refresh_from_db()
    assert instance.last_used_at is not None


# ──────────────────────────────────────────────────────────────────────────────
# resolve_language()
# ──────────────────────────────────────────────────────────────────────────────

def _drf_style_request(query: dict | None = None, accept_language: str = ""):
    """Mimic the minimal interface resolve_language() needs from a DRF Request."""

    class _FakeRequest:
        def __init__(self, query_params, meta):
            self.query_params = query_params
            self.META = meta

    return _FakeRequest(query or {}, {"HTTP_ACCEPT_LANGUAGE": accept_language} if accept_language else {})


def test_resolve_language_prefers_query_param_over_header():
    request = _drf_style_request(query={"lang": "fr"}, accept_language="es")
    assert resolve_language(request) == "fr"


def test_resolve_language_falls_back_to_accept_language_header():
    request = _drf_style_request(accept_language="de,en;q=0.8")
    assert resolve_language(request) == "de"


def test_resolve_language_matches_region_qualified_header():
    request = _drf_style_request(accept_language="zh-CN,en;q=0.5")
    assert resolve_language(request) == "zh-hans"


def test_resolve_language_ignores_invalid_query_param():
    request = _drf_style_request(query={"lang": "xx"}, accept_language="")
    assert resolve_language(request) == "en"


def test_resolve_language_defaults_to_english_when_nothing_matches():
    request = _drf_style_request()
    assert resolve_language(request) == "en"
