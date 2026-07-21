# 🚀 AUTOMEX Backend — Production Deployment Guide

---

## Architecture

```
                          ┌──────────────┐
                          │  Cloudflare   │
                          │  (DNS + CDN)  │
                          └──────┬───────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ automex.tech │    │ api.automex  │    │  admin.*    │
    │  (Next.js)   │    │  (DRF API)   │    │  (Django)   │
    │  Port 3000   │    │  Port 8000   │    │  Port 8001  │
    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
           │                   │                    │
           └───────────────────┼────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Hostinger VPS      │
                    │   Docker Compose     │
                    │                      │
                    │  ┌────┐ ┌────┐ ┌───┐ │
                    │  │ DB │ │Redis│ │Web│ │
                    │  │PG15│ │     │ │:80│ │
                    │  └────┘ └────┘ └───┘ │
                    │  ┌──────────┐        │
                    │  │  Celery  │        │
                    │  └──────────┘        │
                    └──────────────────────┘
```

| Component | Technology | Port |
|---|---|---|
| API Server | Gunicorn + Django 5.2 | 8000 (internal) |
| Reverse Proxy | Nginx | 80 / 443 |
| Database | PostgreSQL 15 (Docker) | 5432 (internal) |
| Cache / Broker | Redis 7 (Docker) | 6379 (internal) |
| Task Queue | Celery + Celery Beat | — |
| AI Provider | Groq API (external) | — |
| Email | Gmail SMTP | 587 |

---

## Server Requirements

- **OS**: Ubuntu 22.04+ LTS
- **CPU**: 2+ vCPUs
- **RAM**: 4 GB minimum (8 GB recommended)
- **Storage**: 40 GB SSD
- **Docker**: 24+ & Docker Compose v2
- **Nginx**: 1.24+

---

## Initial Server Setup

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone Repository

```bash
git clone https://github.com/your-org/automex-backend.git ~/sites/automex-backend
cd ~/sites/automex-backend
```

### 3. Create `.env` File

```env
# Django
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(64))">
DEBUG=0
ALLOWED_HOSTS=api.automex.tech,automex.tech,localhost
ADMIN_URL_PATH=control-panel/

# Database
DB_NAME=automex
DB_USER=automex
DB_PASSWORD=<strong-db-password>
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Email (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=notifications@automex.tech
EMAIL_HOST_PASSWORD=<app-password>
DEFAULT_FROM_EMAIL=hello@automex.tech
ADMIN_NOTIFICATION_EMAILS=sales@automex.tech,hello@automex.tech

# Frontend
FRONTEND_BASE_URL=https://automex.tech

# Groq AI
GROQ_API_KEY=gsk_<your-key>
GROQ_MODEL=openai/gpt-oss-120b

# Encryption (for notification credentials)
FIELD_ENCRYPTION_KEY=<32-char-hex-key>

# Cors
CORS_ALLOWED_ORIGINS=https://automex.tech,https://www.automex.tech
```

### 4. Build & Start

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py create_api_key --name "automex-frontend-web"
```

**Save the printed API key** — it's shown exactly once and used by the Next.js frontend.

### 5. Configure Nginx

```nginx
# /etc/nginx/sites-available/api.automex.tech
server {
    listen 80;
    server_name api.automex.tech;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }

    location /staticfiles/ {
        alias /home/deploy/sites/automex-backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /home/deploy/sites/automex-backend/media/;
        expires 7d;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/api.automex.tech /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 6. SSL (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.automex.tech
```

---

## Deploying Updates

### Standard deploy (code-only changes)

```bash
cd ~/sites/automex-backend
git pull origin main
docker compose up -d --build          # rebuilds web + celery containers
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose restart celery_beat
```

### Deploy with dependency changes

```bash
cd ~/sites/automex-backend
git pull origin main
docker compose build --no-cache
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose restart celery_beat
```

### Protected Files

The following files are locked on the production server via `git update-index --assume-unchanged` to prevent accidental overwrites:

- `Dockerfile`
- `docker-compose.yml`
- `config/settings.py`

To update them:

```bash
git update-index --no-assume-unchanged Dockerfile docker-compose.yml config/settings.py
git pull origin main
docker compose down && docker compose up -d --build
docker compose exec web python manage.py migrate
git update-index --assume-unchanged Dockerfile docker-compose.yml config/settings.py
```

---

## Useful Commands

```bash
docker compose ps                          # container status
docker compose logs -f web                 # tail web logs
docker compose logs -f celery_worker       # tail celery logs
docker compose exec web python manage.py shell           # Django shell
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py create_api_key --name "frontend-web"
docker compose exec db psql -U automex automex            # DB shell
docker compose restart web                                # restart API
docker compose restart celery_worker                      # restart workers
sudo tail -f /var/log/nginx/api.automex.tech-error.log   # Nginx errors
sudo systemctl reload nginx
```

---

## Health Checks

```bash
# API health
curl -I https://api.automex.tech/api/v1/services/

# Admin panel
curl -I https://api.automex.tech/control-panel/

# Sitemap
curl https://api.automex.tech/sitemap.xml | head -20

# Celery
docker compose exec celery_worker celery -A config inspect active
```

---

## Backup

### Database

```bash
docker compose exec db pg_dump -U automex automex > ~/backups/automex_$(date +%Y%m%d).sql
```

### Media files

```bash
tar -czf ~/backups/media_$(date +%Y%m%d).tar.gz ~/sites/automex-backend/media/
```

### Restore

```bash
docker compose exec -T db psql -U automex automex < ~/backups/automex_20260720.sql
```

---

## Monitoring

- **Container health**: `docker compose ps`
- **Disk usage**: `df -h`
- **Memory**: `free -h`
- **Django logs**: `~/sites/automex-backend/logs/django.log`
- **API Schema**: `GET /api/schema/`
- **Swagger UI**: `GET /api/schema/docs/`

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `could not translate host name "db"` | DB not ready — wait 15s, retry |
| `403` on all requests | Check `X-API-Key` header, key may be expired |
| `403` on static/media | `sudo chown -R www-data:www-data staticfiles/ media/` |
| Nginx SSL error | Verify certbot paths in `/etc/letsencrypt/live/` |
| Celery not processing | `docker compose restart celery_worker celery_beat` |
| AI assistant not responding | Check `GROQ_API_KEY` in `.env` |
| Email not sending | Verify Gmail app password, check spam folder |

---

## Security Checklist

- [ ] `DEBUG=0` in `.env`
- [ ] `SECRET_KEY` is 60+ random characters
- [ ] DB password is strong and unique
- [ ] `ADMIN_URL_PATH` is obfuscated (not `/admin`)
- [ ] SSL certificate is valid and auto-renewing
- [ ] Firewall (UFW) allows only ports 80, 443, 22
- [ ] Docker daemon not exposed on TCP
- [ ] `.env` and backups excluded from Git
- [ ] Regular `apt update && apt upgrade`

---

## Scaling

- **More traffic**: Increase Gunicorn `--workers` in `docker-compose.yml`
- **More background tasks**: `docker compose scale celery_worker=3`
- **Separate DB server**: Point `DB_HOST` to external PostgreSQL
- **CDN for media**: Mount S3-compatible bucket via `django-storages`

---

**Last updated: July 2026**
