"""
config/settings_test.py
─────────────────────────
Optional settings overlay for fast local/CI test runs — swaps Postgres for
SQLite and speeds up password hashing, so `pytest` doesn't require a live
database server. Production and normal development still use
config.settings (Postgres) as configured in .env.

Usage:
    DJANGO_SETTINGS_MODULE=config.settings_test pytest
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
    }
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Django's test runner forces DEBUG=False for the duration of any test run
# (standard behavior — tests should run under production-like conditions),
# so apps.core.fields.EncryptedJSONField's DEBUG-only fallback key correctly
# never activates here. Fixed test-only key, never used outside this file.
FIELD_ENCRYPTION_KEY = "fXi2wZcyWsfGe_qNzYkogWYueklhmKmlmjNDHeeNtrs="

# Same root cause as FIELD_ENCRYPTION_KEY above: Django's test runner forces
# DEBUG=False during any test run, which means settings.py's `if not DEBUG:`
# block (SECURE_SSL_REDIRECT, secure cookies, HSTS, ...) silently activates
# here too — breaking the Django/DRF test client, which always talks plain
# HTTP internally. Explicitly disabled for tests only.
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
USE_X_FORWARDED_HOST = False

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
