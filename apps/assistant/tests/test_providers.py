from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from apps.assistant.providers import AIProviderError, GroqProvider


def test_complete_raises_when_api_key_missing():
    provider = GroqProvider(api_key="", base_url="https://api.groq.com/openai/v1", model="openai/gpt-oss-120b")
    with pytest.raises(AIProviderError, match="not configured"):
        provider.complete([{"role": "user", "content": "hi"}])


@patch("apps.assistant.providers.requests.post")
def test_complete_returns_content_on_success(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": "Hello there!"}}]}
    mock_post.return_value = mock_response

    provider = GroqProvider(api_key="test-key", base_url="https://api.groq.com/openai/v1", model="openai/gpt-oss-120b")
    result = provider.complete([{"role": "user", "content": "hi"}])

    assert result.content == "Hello there!"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert call_kwargs["json"]["model"] == "openai/gpt-oss-120b"


@patch("apps.assistant.providers.requests.post")
def test_complete_sets_json_response_format_when_json_mode_true(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
    mock_post.return_value = mock_response

    provider = GroqProvider(api_key="test-key")
    provider.complete([{"role": "user", "content": "hi"}], json_mode=True)

    assert mock_post.call_args.kwargs["json"]["response_format"] == {"type": "json_object"}


@patch("apps.assistant.providers.requests.post", side_effect=requests.exceptions.Timeout())
def test_complete_wraps_timeout_as_provider_error(mock_post):
    provider = GroqProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="timed out"):
        provider.complete([{"role": "user", "content": "hi"}])


@patch("apps.assistant.providers.requests.post", side_effect=requests.exceptions.ConnectionError("boom"))
def test_complete_wraps_connection_error_as_provider_error(mock_post):
    provider = GroqProvider(api_key="test-key")
    with pytest.raises(AIProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


@patch("apps.assistant.providers.requests.post")
def test_complete_raises_on_unexpected_response_shape(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"unexpected": "shape"}
    mock_post.return_value = mock_response

    provider = GroqProvider(api_key="test-key")
    with pytest.raises(AIProviderError, match="Unexpected Groq response shape"):
        provider.complete([{"role": "user", "content": "hi"}])


@patch("apps.assistant.providers.requests.post")
def test_complete_raises_on_http_error_status(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
    mock_post.return_value = mock_response

    provider = GroqProvider(api_key="bad-key")
    with pytest.raises(AIProviderError):
        provider.complete([{"role": "user", "content": "hi"}])
