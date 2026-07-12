"""
config/settings.py
───────────────────
AUTOMEX Backend — Production Django Settings
Uses django-environ for environment variables.
All secrets and environment-specific values come from .env.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

from config.settings_unfold_additions import UNFOLD_ADDITIONS
from django.conf.locale import LANG_INFO

# Add Pashto to Django's internal language database
LANG_INFO['ps'] = {
    'name': 'Pashto',
    'name_local': 'پښتو',          # native script
    'name_translated': 'Pashto',   # English fallback
    'bidi': True,                  # right-to-left
    'code': 'ps',
}

# ──────────────────────────────────────────────────────────────────────────────
# PATH & ENVIRONMENT
# ──────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")   # loads .env from project root

# ──────────────────────────────────────────────────────────────────────────────
# CORE SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY           = env("SECRET_KEY")
DEBUG                = env.bool("DEBUG", default=False)
ALLOWED_HOSTS        = env.list("ALLOWED_HOSTS", default=[])
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
WSGI_APPLICATION     = "config.wsgi.application"
ROOT_URLCONF         = "config.urls"
DEFAULT_AUTO_FIELD   = "django.db.models.BigAutoField"
AUTH_USER_MODEL      = "accounts.User"

# ──────────────────────────────────────────────────────────────────────────────
# INSTALLED APPS
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Admin theme (must come before django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",   
    "unfold.contrib.forms",   

    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "django_redis",
    "parler",
    "django_filters",

    # Local apps
    "apps.accounts",
    "apps.core",               
    "apps.content",        
    "apps.crm",                   
    "apps.assistant",             
    "apps.notifications",         
]

# ──────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ──────────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"] if (BASE_DIR / "templates").exists() else [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# DATABASE (PostgreSQL)
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE":       "django.db.backends.postgresql",
        "NAME":         env("DB_NAME"),
        "USER":         env("DB_USER"),
        "PASSWORD":     env("DB_PASSWORD"),
        "HOST":         env("DB_HOST"),
        "PORT":         env("DB_PORT"),
        "CONN_MAX_AGE": 60,
        "OPTIONS":      {"sslmode": env("DB_SSL_MODE", default="disable")},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION & PASSWORD VALIDATION
# ──────────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Failed login lock settings
MAX_FAILED_LOGIN_ATTEMPTS = env.int("MAX_FAILED_LOGIN_ATTEMPTS", default=5)
ACCOUNT_LOCK_MINUTES      = env.int("ACCOUNT_LOCK_MINUTES", default=30)

# ──────────────────────────────────────────────────────────────────────────────
# SIMPLE JWT
# ──────────────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7)),
    "SIGNING_KEY":            env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES":      ("Bearer",),
    "USER_ID_FIELD":          "id",
    "USER_ID_CLAIM":          "user_id",
    "AUTH_TOKEN_CLASSES":     ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM":       "token_type",
    # Rotation handled manually in AuthService to support device tracking
    "ROTATE_REFRESH_TOKENS":      False,
    "BLACKLIST_AFTER_ROTATION":   False,
    "ALGORITHM":                  "HS256",
    "JTI_CLAIM":                  "jti",
}

# ──────────────────────────────────────────────────────────────────────────────
# GOOGLE OAUTH2
# ──────────────────────────────────────────────────────────────────────────────
GOOGLE_OAUTH2_CLIENT_ID     = env("GOOGLE_OAUTH2_CLIENT_ID")
GOOGLE_OAUTH2_CLIENT_SECRET = env("GOOGLE_OAUTH2_CLIENT_SECRET")

# ──────────────────────────────────────────────────────────────────────────────
# CACHES (Redis)
# ──────────────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND":   "django_redis.cache.RedisCache",
        "LOCATION":  env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS":             "django_redis.client.DefaultClient",
            "CONNECTION_POOL_CLASS":    "redis.BlockingConnectionPool",
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,
                "timeout":         20,
            },
            "RETRY_ON_TIMEOUT": True,
            "IGNORE_EXCEPTIONS": True, 
        },
        "KEY_PREFIX": env("CACHE_KEY_PREFIX", default="infinity_cache"),
        "TIMEOUT":    300,
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# CELERY
# ──────────────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL       = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND   = env("REDIS_URL")
CELERY_ACCEPT_CONTENT   = ["json"]
CELERY_TASK_SERIALIZER  = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE         = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT    = 30 * 60   # 30 min hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60  # 4 min soft limit
CELERY_BEAT_SCHEDULER   = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    # Delete expired tokens every hour
    "cleanup-expired-tokens": {
        "task":     "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": 3600,
    },
    # Unlock accounts whose lock period has elapsed every 15 minutes
    "unlock-expired-accounts": {
        "task":     "apps.accounts.tasks.unlock_expired_accounts",
        "schedule": 900,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# EMAIL (SMTP)
# ──────────────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = env("EMAIL_HOST")
EMAIL_PORT          = env.int("EMAIL_PORT")
EMAIL_USE_TLS       = env.bool("EMAIL_USE_TLS")
EMAIL_HOST_USER     = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL  = env("DEFAULT_FROM_EMAIL")

# Fall back to console backend in local dev when no SMTP is configured
if DEBUG and not env("EMAIL_HOST_USER", default=""):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ──────────────────────────────────────────────────────────────────────────────
# INTERNATIONALISATION
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

# ──────────────────────────────────────────────────────────────────────────────
# django-parler needs its own LANGUAGES-derived config 
# ──────────────────────────────────────────────────────────────────────────────
PARLER_DEFAULT_LANGUAGE_CODE = "en"
PARLER_LANGUAGES = {
    None: (
        {"code": "en"}, {"code": "es"}, {"code": "de"}, {"code": "fr"},
        {"code": "it"}, {"code": "nl"}, {"code": "zh-hans"}, {"code": "ar"},
        {"code": "fa"}, {"code": "ps"},
    ),
    "default": {"fallbacks": ["en"], "hide_untranslated": False},
}

# Django's own LANGUAGES setting parler validates its codes against this
LANGUAGES = [
    ("en", _("English")), ("es", _("Spanish")), ("de", _("German")),
    ("fr", _("French")), ("it", _("Italian")), ("nl", _("Dutch")),
    ("zh-hans", _("Chinese")), ("ar", _("Arabic")), ("fa", _("Persian")),
    ("ps", _("Pashto")),
]


# ──────────────────────────────────────────────────────────────────────────────
# STATIC & MEDIA FILES
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL     = "/static/"
STATIC_ROOT    = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL  = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ──────────────────────────────────────────────────────────────────────────────
# SECURITY HEADERS (production only)
# ──────────────────────────────────────────────────────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER        = True
    SECURE_CONTENT_TYPE_NOSNIFF      = True
    X_FRAME_OPTIONS                  = "DENY"
    SECURE_HSTS_SECONDS              = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS   = True
    SECURE_HSTS_PRELOAD              = True
    SECURE_SSL_REDIRECT              = True
    SESSION_COOKIE_SECURE            = True
    CSRF_COOKIE_SECURE               = True
    SESSION_COOKIE_HTTPONLY          = True
    CSRF_COOKIE_HTTPONLY             = True
    SECURE_REFERRER_POLICY           = "same-origin"

# ──────────────────────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────────────────────

CORS_ALLOWED_ORIGINS  = env.list("CORS_ALLOWED_ORIGINS", default=[])
# This ensures Django accepts POST requests from your frontend
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS + ['https://api.idwe.tech']) 
CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 86_400

# ──────────────────────────────────────────────────────────────────────────────
# Groq API Settings (for AI Assistant)
# ──────────────────────────────────────────────────────────────────────────────
GROQ_API_KEY                      = env("GROQ_API_KEY", default="")
GROQ_API_BASE_URL                 = env("GROQ_API_BASE_URL", default="https://api.groq.com/openai/v1")
GROQ_MODEL                        = env("GROQ_MODEL", default="openai/gpt-oss-120b")
GROQ_REQUEST_TIMEOUT_SECONDS       = env.int("GROQ_REQUEST_TIMEOUT_SECONDS", default=20)
AI_ASSISTANT_MAX_HISTORY_MESSAGES = env.int("AI_ASSISTANT_MAX_HISTORY_MESSAGES", default=20)

# ──────────────────────────────────────────────────────────────────────────────
# DJANGO REST FRAMEWORK
# ──────────────────────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS":    "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon":                "100/day",
        "user":                "1000/hour",
        "registration":        "5/minute",
        "magic_link_request":  "5/minute",
        "magic_link_verify":   "20/minute",
        "public_content": "300/minute",
        "public_write": "20/minute",
        "ai_assistant": "20/minute",
    },
    "DEFAULT_FILTER_BACKENDS": (              # ← added
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# ──────────────────────────────────────────────────────────────────────────────
# DRF SPECTACULAR (OpenAPI schema)
# ──────────────────────────────────────────────────────────────────────────────

SPECTACULAR_SETTINGS = {
    "TITLE":                "Infinity Backend API",
    "DESCRIPTION":          (
        "Enterprise authentication API — registration, Google OAuth2, "
        "magic link, JWT, RBAC, MFA."
    ),
    "VERSION":              "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ──────────────────────────────────────────────────────────────────────────────
# APPLICATION SETTINGS
# ──────────────────────────────────────────────────────────────────────────────

MAGIC_LINK_EXPIRY_MINUTES        = env.int("MAGIC_LINK_EXPIRY_MINUTES", 15)
EMAIL_VERIFICATION_EXPIRY_HOURS  = env.int("EMAIL_VERIFICATION_EXPIRY_HOURS", 24)
PASSWORD_RESET_EXPIRY_MINUTES    = env.int("PASSWORD_RESET_EXPIRY_MINUTES", 30)
MFA_ENABLED                      = env.bool("MFA_ENABLED", default=False)
FRONTEND_BASE_URL                = env("FRONTEND_BASE_URL", default="https://automex.tech")

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────────

LOGGING = {
    "version":                  1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style":  "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style":  "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "verbose" if DEBUG else "simple",
        },
        "file": {
            "class":        "logging.handlers.RotatingFileHandler",
            "filename":     BASE_DIR / "logs" / "django.log",
            "maxBytes":     10_485_760,   # 10 MB
            "backupCount":  5,
            "formatter":    "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level":    "INFO" if not DEBUG else "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers":  ["console", "file"],
            "level":     "INFO",
            "propagate": False,
        },
        "apps.accounts": {
            "handlers":  ["console", "file"],
            "level":     "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# Ensure the logs directory exists
_logs_dir = BASE_DIR / "logs"
if not _logs_dir.exists():
    os.makedirs(_logs_dir)


# =============================================================================
# ADMIN NOTIFICATION EMAILS
# =============================================================================
ADMIN_NOTIFICATION_EMAILS = env.list("ADMIN_NOTIFICATION_EMAILS", default=[]) or [DEFAULT_FROM_EMAIL]


# ──────────────────────────────────────────────────────────────────────────────
# UNFOLD ADMIN THEME
# ──────────────────────────────────────────────────────────────────────────────

from django.templatetags.static import static   # noqa: E402

UNFOLD = {
    "SITE_TITLE":     "AUTOMEX",
    "SITE_HEADER":    "Dashboard",
    "SITE_SUBHEADER": "Manage your application data",
    "SITE_URL":       "/",
    "SHOW_HISTORY":      True,
    "SHOW_VIEW_ON_SITE": True,
    "SITE_LOGO": {
        "light": lambda request: static("logo/dark.png"),
        "dark":  lambda request: static("logo/light.png"),
    },
    "SITE_ICON": {
        "light": lambda request: static("icon/light.png"),
        "dark":  lambda request: static("icon/light.png"),
    },
    "SITE_FAVICONS": [
        {
            "rel":   "icon",
            "sizes": "32x32",
            "type":  "image/png",
            "href":  lambda request: static("icon/icon.png"),
        },
    ],
    "STYLES": [
        lambda request: static("css/custom.css"),
    ],
    **UNFOLD_ADDITIONS,
}