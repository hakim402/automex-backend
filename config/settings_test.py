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

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ─── Force HTTP in tests, avoid HTTPS redirects ──────────────────────────
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = None       # remove any proxy header triggering HTTPS
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
USE_X_FORWARDED_HOST = False