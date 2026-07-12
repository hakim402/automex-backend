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

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
