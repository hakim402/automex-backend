"""
apps/core/management/commands/create_api_key.py
─────────────────────────────────────────────────────
Usage:
    python manage.py create_api_key --name "automex-frontend-web"

Prints the raw key exactly once. Only its hash is stored — if it's lost,
generate a new one and deactivate the old row from the admin.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from apps.core.models import APIKey


class Command(BaseCommand):
    help = "Generate a new API key for a public content API consumer (e.g. the Next.js frontend)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--name", required=True, help="Human-readable label, e.g. 'automex-frontend-web'.")

    def handle(self, *args, **options) -> None:
        name = options["name"]
        instance, raw_key = APIKey.generate(name=name)

        self.stdout.write(self.style.SUCCESS(f"API key created: {instance.name} (id={instance.id})"))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Raw key (copy now — it will not be shown again):"))
        self.stdout.write(raw_key)
        self.stdout.write("")
        self.stdout.write("Send it as the 'X-API-Key' header on requests to the public content API.")
