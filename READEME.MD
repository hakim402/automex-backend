# AUTOMEX Backend

Enterprise technology consulting platform — CRM, content management, AI sales assistant, multi-channel notifications, and multi-language storefront API.

## Tech Stack

| Category | Technology |
|---|---|
| Framework | Django 5 + Django REST Framework |
| Admin | Unfold (modern enterprise admin theme) |
| Database | PostgreSQL |
| Cache / Queue | Redis |
| Tasks | Celery Worker + Celery Beat |
| API Docs | drf-spectacular (OpenAPI 3) |
| Auth | SimpleJWT + Google OAuth2 |
| i18n | django-parler (10 languages including RTL) |
| Serve | Gunicorn + Whitenoise |
| Infra | Docker Compose |

## Prerequisites

- Docker & Docker Compose
- Git

```bash
docker --version
docker compose version
```

## Quick Start

```bash
# Clone and enter
git clone <repo-url>
cd automex-backend

# Copy and fill in environment variables
cp .env.example .env   # edit with your values

# Build and start all services
docker compose up -d --build

# Apply migrations and create admin
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Done — access at http://localhost:8000/admin
```

## Environment Variables

Create `.env` from the template below. See `config/settings.py` for defaults.

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=automex_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=db
DB_PORT=5432
DB_SSL_MODE=disable

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# JWT
JWT_SIGNING_KEY=your-jwt-signing-key
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Google OAuth2
GOOGLE_OAUTH2_CLIENT_ID=your-client-id
GOOGLE_OAUTH2_CLIENT_SECRET=your-client-secret

# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@automex.tech

# AI Assistant (Groq — OpenAI-compatible)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b

# Frontend
FRONTEND_BASE_URL=http://localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Encryption (generate with: python manage.py generate_field_encryption_key)
FIELD_ENCRYPTION_KEY=your-fernet-key

# Optional
ADMIN_URL_PATH=admin/
ADMIN_NOTIFICATION_EMAILS=sales@automex.tech
MFA_ENABLED=False
CACHE_KEY_PREFIX=automex_cache
```

## Services

| Service | Role | Port |
|---|---|---|
| `web` | Django + Gunicorn | 8000 |
| `db` | PostgreSQL | 5432 |
| `redis` | Redis cache + broker | 6379 |
| `celery_worker` | Background tasks | — |
| `celery_beat` | Scheduled tasks (DB scheduler) | — |

## Project Structure

```
automex-backend/
├── apps/
│   ├── accounts/       # Users, tenants, RBAC, MFA, JWT sessions
│   ├── core/           # Media assets, SEO, redirects, API keys
│   ├── content/        # Services, case studies, blog, portfolio, team
│   ├── crm/            # Leads, bookings, support tickets, calculator
│   ├── assistant/      # AI sales assistant + knowledge base
│   └── notifications/  # Multi-channel notifications + integrations
├── config/             # Django settings, URLs, WSGI/ASGI, Celery
├── static/             # Custom CSS, logos, icons
├── templates/          # Admin dashboard override
├── doc/                # API guides and architecture docs
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
└── pytest.ini
```

## Admin Panel

The admin runs **Unfold** — a modern enterprise theme with:
- Dashboard KPI cards + Chart.js analytics
- Curated sidebar navigation across all 6 apps
- Colored status badges, tabbed change forms, bulk actions
- 10-language django-parler translation tabs
- Editorial workflow (Draft → Review → Publish → Archive)

## Development

```bash
# Code changes — restart web
docker compose restart web

# Model changes — migrate
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Static files
docker compose exec web python manage.py collectstatic --noinput

# New packages — rebuild
docker compose build
docker compose up -d

# Clean rebuild
docker compose build --no-cache
docker compose up -d
```

## Testing

```bash
docker compose exec web pytest

# Specific app with verbose output
docker compose exec web pytest apps/accounts/tests -v

# Coverage report
docker compose exec web pytest --cov=apps --cov-report=term-missing
```

## Logs

```bash
docker compose logs -f              # all services
docker compose logs -f web          # Django
docker compose logs -f celery_worker
docker compose logs -f celery_beat
```

## Deployment

```bash
git pull
docker compose build
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose restart
```

## API Documentation

OpenAPI schema available at:

```
http://localhost:8000/api/schema/
http://localhost:8000/api/docs/     # Swagger UI
http://localhost:8000/api/redoc/    # ReDoc
```

---

Built with Django, DRF, PostgreSQL, Redis, Celery, and Unfold.
