from __future__ import annotations

from apps.assistant.extraction import extract_email, extract_phone


def test_extract_email_finds_valid_email():
    assert extract_email("You can reach me at jane@example.com anytime") == "jane@example.com"


def test_extract_email_returns_none_when_absent():
    assert extract_email("I don't want to share contact info yet") is None


def test_extract_email_handles_empty_string():
    assert extract_email("") is None
    assert extract_email(None) is None


def test_extract_phone_finds_valid_number():
    assert extract_phone("Call me at +1 415-555-0134 please") is not None


def test_extract_phone_ignores_short_numbers():
    assert extract_phone("We've helped over 50 clients") is None


def test_extract_phone_ignores_years():
    assert extract_phone("We were founded in 2019") is None


def test_extract_phone_returns_none_when_absent():
    assert extract_phone("Just curious about pricing") is None
