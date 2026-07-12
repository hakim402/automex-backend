from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.core.models import APIKey

from .factories import FakeAIProvider

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_with_key() -> APIClient:
    _, raw_key = APIKey.generate(name="test-frontend")
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=raw_key)
    return client


def test_chat_requires_api_key():
    client = APIClient()
    response = client.post("/api/v1/assistant/chat/", {"message": "hi"})
    assert response.status_code == 403


@patch("apps.assistant.services.get_default_provider")
def test_chat_returns_reply_and_session_id(mock_get_provider, client_with_key):
    mock_get_provider.return_value = FakeAIProvider(reply="Hello! How can I help?")

    response = client_with_key.post("/api/v1/assistant/chat/", {"message": "Hi there"})

    assert response.status_code == 200
    assert response.data["reply"] == "Hello! How can I help?"
    assert response.data["session_id"]
    assert response.data["lead_captured"] is False


@patch("apps.assistant.services.get_default_provider")
def test_chat_rejects_empty_message(mock_get_provider, client_with_key):
    mock_get_provider.return_value = FakeAIProvider()
    response = client_with_key.post("/api/v1/assistant/chat/", {"message": "   "})
    assert response.status_code == 400


@patch("apps.assistant.services.get_default_provider")
def test_chat_reuses_session_id_across_requests(mock_get_provider, client_with_key):
    mock_get_provider.return_value = FakeAIProvider()

    first = client_with_key.post("/api/v1/assistant/chat/", {"message": "First message"})
    session_id = first.data["session_id"]

    second = client_with_key.post(
        "/api/v1/assistant/chat/", {"message": "Second message", "session_id": session_id},
    )
    assert second.data["session_id"] == session_id


@patch("apps.assistant.services.get_default_provider")
def test_chat_captures_lead_end_to_end(mock_get_provider, client_with_key):
    mock_get_provider.return_value = FakeAIProvider(lead_info={"full_name": "API Test"})

    response = client_with_key.post(
        "/api/v1/assistant/chat/", {"message": "Reach me at apitest@example.com"},
    )

    assert response.status_code == 200
    assert response.data["lead_captured"] is True

    from apps.crm.models import Lead
    assert Lead.objects.filter(email="apitest@example.com", lead_type=Lead.LeadType.AI_ASSISTANT).exists()
