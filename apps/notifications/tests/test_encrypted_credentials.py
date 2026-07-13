from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.notifications.models import NotificationChannel, NotificationProviderConfig

pytestmark = pytest.mark.django_db


def test_credentials_round_trip_through_database():
    secret_payload = {"api_key": "sk_live_super_secret_12345", "region": "us-east-1"}
    config = NotificationProviderConfig.objects.create(
        channel=NotificationChannel.EMAIL,
        provider_name="sendgrid",
        credentials=secret_payload,
    )

    reloaded = NotificationProviderConfig.objects.get(pk=config.pk)
    assert reloaded.credentials == secret_payload


def test_credentials_are_actually_encrypted_in_the_database_column():
    """The raw DB value must never contain the plaintext secret."""
    from django.db import connection

    secret_payload = {"api_key": "sk_live_should_never_appear_in_plaintext"}
    NotificationProviderConfig.objects.create(
        channel=NotificationChannel.SLACK,
        provider_name="slack_webhook",
        credentials=secret_payload,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT credentials FROM notifications_notificationproviderconfig WHERE provider_name = %s",
            ["slack_webhook"],
        )
        raw_value = cursor.fetchone()[0]

    assert "sk_live_should_never_appear_in_plaintext" not in raw_value


def test_empty_credentials_round_trip_as_empty_dict():
    config = NotificationProviderConfig.objects.create(
        channel=NotificationChannel.SMS, provider_name="twilio", credentials={},
    )
    reloaded = NotificationProviderConfig.objects.get(pk=config.pk)
    assert reloaded.credentials == {}


@override_settings(DEBUG=False, FIELD_ENCRYPTION_KEY="")
def test_missing_encryption_key_in_production_raises_instead_of_silently_storing_plaintext():
    with pytest.raises(ImproperlyConfigured):
        NotificationProviderConfig.objects.create(
            channel=NotificationChannel.WHATSAPP, provider_name="whatsapp_cloud_api",
            credentials={"token": "should-never-be-stored-unencrypted"},
        )


@override_settings(DEBUG=False, FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
def test_explicit_key_works_fine_outside_debug():
    config = NotificationProviderConfig.objects.create(
        channel=NotificationChannel.EMAIL, provider_name="ses", credentials={"key": "value"},
    )
    reloaded = NotificationProviderConfig.objects.get(pk=config.pk)
    assert reloaded.credentials == {"key": "value"}
