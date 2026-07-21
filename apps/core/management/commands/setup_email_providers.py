"""
Management command to configure SMTP email providers (Google Gmail, Hostinger)
as ThirdPartyIntegration records. Credentials are read from environment
variables and encrypted at rest via EncryptedJSONField.

Usage:
    # Create both providers (reads credentials from .env)
    docker compose exec web python manage.py setup_email_providers

    # Test connections after setup
    docker compose exec web python manage.py setup_email_providers --test

    # Set a specific provider as default
    docker compose exec web python manage.py setup_email_providers --default hostinger

    # Use an existing .env file on the host
    docker compose exec web python manage.py setup_email_providers --env-file /app/.env

.env variables expected (add to your .env file):
    ── Google Gmail (these already exist in your .env) ─────────────────────────
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER=your-app@gmail.com
    EMAIL_HOST_PASSWORD=your-16-char-app-password
    DEFAULT_FROM_EMAIL=noreply@automex.tech

    ── Hostinger Email (add these to .env) ─────────────────────────────────────
    HOSTINGER_SMTP_HOST=smtp.hostinger.com
    HOSTINGER_SMTP_PORT=587
    HOSTINGER_SMTP_USE_TLS=True
    HOSTINGER_SMTP_USER=noreply@automex.tech
    HOSTINGER_SMTP_PASSWORD=your-mailbox-password
    HOSTINGER_SMTP_FROM_EMAIL=noreply@automex.tech
"""
from __future__ import annotations

import os
import smtplib
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import ThirdPartyIntegration


class Command(BaseCommand):
    help = "Set up Google Gmail and Hostinger email as ThirdPartyIntegration SMTP providers."

    DEFAULTS = {
        "google": None,
        "hostinger": "google",  # default is google unless overridden
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--default",
            choices=["google", "hostinger"],
            help="Which provider to set as the default SMTP (default: google).",
        )
        parser.add_argument(
            "--test",
            action="store_true",
            help="Test SMTP connections after setup.",
        )
        parser.add_argument(
            "--env-file",
            help="Path to a .env file to load (auto-loaded in Docker via env_file).",
        )

    def handle(self, *args, **options):
        # ── Load .env file if specified (for outside-Docker usage) ──────
        if options["env_file"]:
            self._load_env_file(options["env_file"])

        default_provider = options["default"] or "google"
        both_providers = ["google", "hostinger"]

        # Clear all SMTP defaults first to avoid unique-constraint conflicts
        ThirdPartyIntegration.objects.filter(
            provider_type=ThirdPartyIntegration.ProviderType.SMTP,
            is_default_for_type=True,
        ).update(is_default_for_type=False)

        for provider in both_providers:
            data = self._get_credentials(provider)
            if data is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠  Skipped {provider}: missing credentials in environment."
                    )
                )
                continue

            is_default = provider == default_provider
            obj, created = ThirdPartyIntegration.objects.update_or_create(
                slug=f"{provider}-smtp",
                defaults={
                    "name": f"{'Google Gmail' if provider == 'google' else 'Hostinger'} SMTP",
                    "provider_type": ThirdPartyIntegration.ProviderType.SMTP,
                    "provider_name": f"{provider}_smtp",
                    "credentials": data["credentials"],
                    "config": data.get("config", {}),
                    "is_active": True,
                    "is_default_for_type": is_default,
                    "description": data["description"],
                },
            )

            status = "✅ Created" if created else "📝 Updated"
            self.stdout.write(
                f"  {status} {obj.name} ({obj.slug})"
                + (" ★ default" if is_default else "")
            )

        # ── Test connections ────────────────────────────────────────────
        if options["test"]:
            self.stdout.write("\nTesting SMTP connections...")
            for provider in both_providers:
                integration = ThirdPartyIntegration.objects.filter(
                    slug=f"{provider}-smtp",
                    is_active=True,
                ).first()
                if integration:
                    result = self._test_smtp(integration)
                    icon = "✅" if result["success"] else "❌"
                    self.stdout.write(f"  {icon} {integration.name}: {result['message']}")

        self.stdout.write(self.style.SUCCESS("\n✅ Email providers configured."))

    # ──────────────────────────────────────────────────────────────────────
    # Credential loaders
    # ──────────────────────────────────────────────────────────────────────

    def _get_credentials(self, provider: str) -> dict[str, Any] | None:
        if provider == "google":
            return self._get_google_credentials()
        return self._get_hostinger_credentials()

    def _get_google_credentials(self) -> dict[str, Any] | None:
        user = os.getenv("EMAIL_HOST_USER", "")
        password = os.getenv("EMAIL_HOST_PASSWORD", "")
        if not user or not password:
            return None

        return {
            "credentials": {
                "host": os.getenv("EMAIL_HOST", "smtp.gmail.com"),
                "port": int(os.getenv("EMAIL_PORT", "587")),
                "use_tls": os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes"),
                "username": user,
                "password": password,
                "from_email": os.getenv("DEFAULT_FROM_EMAIL", user),
            },
            "config": {
                "timeout_seconds": 30,
                "max_retries": 3,
                "provider": "google_workspace",
            },
            "description": (
                "Google Gmail SMTP relay. Uses an App Password (not your regular "
                "Gmail password). Generate at https://myaccount.google.com/apppasswords. "
                "Daily sending limit: 2,000 messages (Google Workspace)."
            ),
        }

    def _get_hostinger_credentials(self) -> dict[str, Any] | None:
        user = os.getenv("HOSTINGER_SMTP_USER", "")
        password = os.getenv("HOSTINGER_SMTP_PASSWORD", "")
        if not user or not password:
            return None

        port = int(os.getenv("HOSTINGER_SMTP_PORT", "587"))
        use_tls = os.getenv("HOSTINGER_SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")

        return {
            "credentials": {
                "host": os.getenv("HOSTINGER_SMTP_HOST", "smtp.hostinger.com"),
                "port": port,
                "use_tls": use_tls,
                "username": user,
                "password": password,
                "from_email": os.getenv("HOSTINGER_SMTP_FROM_EMAIL", user),
            },
            "config": {
                "timeout_seconds": 30,
                "max_retries": 3,
                "provider": "hostinger",
            },
            "description": (
                "Hostinger Business Email SMTP. Uses your Hostinger mailbox "
                "credentials. Port 587 with STARTTLS is recommended; port 465 "
                "with SSL is also supported. Daily sending limit depends on "
                "your Hostinger hosting plan (typically 500-1,000/hour)."
            ),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _test_smtp(self, integration: ThirdPartyIntegration) -> dict[str, Any]:
        creds = integration.credentials or {}
        host = creds.get("host", "")
        port = int(creds.get("port", 587))
        use_tls = creds.get("use_tls", True)
        username = creds.get("username", "")
        password = creds.get("password", "")
        now = timezone.now()

        try:
            if use_tls:
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(host, port, timeout=10)
            if username:
                server.login(username, password)
            server.quit()

            integration.last_tested_at = now
            integration.last_test_result = "success"
            integration.save(update_fields=["last_tested_at", "last_test_result", "updated_at"])
            return {"success": True, "message": "SMTP connection successful."}
        except Exception as exc:
            error_msg = f"failed: {exc}"
            integration.last_tested_at = now
            integration.last_test_result = error_msg[:255]
            integration.save(update_fields=["last_tested_at", "last_test_result", "updated_at"])
            return {"success": False, "message": error_msg}

    @staticmethod
    def _load_env_file(path: str) -> None:
        """Parse a KEY=VALUE .env file into os.environ (simple parser)."""
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key and value:
                    os.environ.setdefault(key, value)
