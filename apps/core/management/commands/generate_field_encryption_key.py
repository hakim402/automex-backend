"""
apps/core/management/commands/generate_field_encryption_key.py
─────────────────────────────────────────────────────────────────────
Usage:
    python manage.py generate_field_encryption_key

Prints a new Fernet key for FIELD_ENCRYPTION_KEY. Add it to your .env
before storing any real NotificationProviderConfig credentials — losing
this key makes existing encrypted rows unrecoverable, and rotating it
requires re-encrypting existing rows (decrypt with the old key, save with
the new one) rather than just swapping the setting.
"""
from __future__ import annotations

from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a new FIELD_ENCRYPTION_KEY for apps.core.fields.EncryptedJSONField."

    def handle(self, *args, **options) -> None:
        key = Fernet.generate_key().decode()
        self.stdout.write(self.style.SUCCESS("Generated FIELD_ENCRYPTION_KEY:"))
        self.stdout.write("")
        self.stdout.write(key)
        self.stdout.write("")
        self.stdout.write("Add this to your .env as FIELD_ENCRYPTION_KEY=<value above>.")
        self.stdout.write(self.style.WARNING(
            "Back this key up somewhere safe (e.g. your secrets manager) — losing it "
            "makes any existing encrypted NotificationProviderConfig rows unrecoverable."
        ))
