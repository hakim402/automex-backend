# 🚀 Production Deployment Guide

This document outlines the standard workflow for deploying updates from the local development environment to the production server (Hostinger VPS).

---

## 📋 Overview

| Environment       | URL                     | Tech Stack                                   |
| ----------------- | ----------------------- | -------------------------------------------- |
| **Frontend**      | `https://idwe.tech`     | Next.js (Port 3000)                          |
| **Backend API**   | `https://api.idwe.tech` | Django REST Framework (Port 8000 via Docker) |
| **Database**      | Internal                | PostgreSQL 15 (Docker)                       |
| **Cache / Queue** | Internal                | Redis + Celery (Docker)                      |

---

## 🛡️ Protected Files (IMPORTANT)

The following files contain **production-specific configurations** and are protected from being overwritten during a standard deployment:

* `Dockerfile`
* `docker-compose.yml`
* `config/settings.py`

> ⚠️ **Do NOT modify or update these files during a normal deployment.**
>
> These files are locked on the production server to prevent accidental overwrites of production-specific settings such as:
>
> * Docker bind mounts
> * SSL configurations
> * CSRF settings
> * Nginx proxy headers
> * Production environment tweaks

---

# 💻 Local Development Workflow (Pushing Code)

When you've completed a feature or bug fix locally, follow these steps:

## Step 1: Stage Your Changes

> Do **NOT** stage protected files unless you intentionally want to update them.

```bash
git add .
```

## Step 2: Commit Your Changes

```bash
git commit -m "feat: add new authentication endpoint"
```

## Step 3: Push to GitHub

```bash
git push origin main
```

---

# 🖥️ Production Deployment Workflow (Pulling Code)

## Step 1: SSH Into the Server

```bash
ssh idwe_mis@your_server_ip

cd ~/sites/idwe-backend
```

## Step 2: Pull the Latest Code

```bash
git pull origin main
```

> Git will automatically ignore the protected files because they are marked with the `--assume-unchanged` flag.

---

## Step 3: Rebuild and Restart Docker

Because application code may have changed, rebuild the containers and apply any new migrations or dependencies.

### Rebuild Containers

```bash
docker compose up -d --build
```

### Apply Database Migrations

```bash
docker compose exec web python manage.py migrate
```

### Collect Static Files

```bash
docker compose exec web python manage.py collectstatic --noinput
```

### Restart Celery Beat

```bash
docker compose restart celery_beat
```

---

## Step 4: Verify the Deployment

### Check Container Status

```bash
docker compose ps
```

### View Web Logs

```bash
docker compose logs -f web
```

---

## ✅ Deployment Complete

Your production API is now running the latest version.

---

# 🔓 Updating Protected Files

Occasionally, you may need to update:

* `Dockerfile`
* `docker-compose.yml`
* `config/settings.py`

Examples:

* Adding a new Python package
* Modifying Gunicorn settings
* Adding a new Django application
* Updating Docker services

In these cases, use the following workflow.

---

## Step 1: Unlock Protected Files

Run on the production server:

```bash
cd ~/sites/idwe-backend

git update-index --no-assume-unchanged Dockerfile
git update-index --no-assume-unchanged docker-compose.yml
git update-index --no-assume-unchanged config/settings.py
```

---

## Step 2: Pull Latest Changes

```bash
git pull origin main
```

---

## Step 3: Rebuild the Environment

```bash
docker compose down

docker compose up -d --build

docker compose exec web python manage.py migrate

docker compose exec web python manage.py collectstatic --noinput

docker compose restart celery_beat
```

---

## Step 4: Re-Lock the Protected Files

> ⚠️ This is a crucial step.

```bash
git update-index --assume-unchanged Dockerfile
git update-index --assume-unchanged docker-compose.yml
git update-index --assume-unchanged config/settings.py
```

---

## Verify Files Are Protected

```bash
git ls-files -v | grep '^h'
```

Expected output:

```text
h Dockerfile
h docker-compose.yml
h config/settings.py
```

---

# 🧰 Useful Production Commands

## View Container Status

```bash
docker compose ps
```

## View Logs (All Services)

```bash
docker compose logs -f
```

## View Web Logs Only

```bash
docker compose logs -f web
```

## Restart Web Service

```bash
docker compose restart web
```

## Open Django Shell

```bash
docker compose exec web python manage.py shell
```

## Create a Superuser

```bash
docker compose exec web python manage.py createsuperuser
```

## Check Celery Worker Status

```bash
docker compose exec celery_worker celery -A config inspect active
```

## View Nginx Error Logs

```bash
sudo tail -f /var/log/nginx/api.idwe.tech-error.log
```

## Reload Nginx

```bash
sudo systemctl reload nginx
```

---

# 🆘 Troubleshooting

## Error: "Could not translate host name 'db'"

The PostgreSQL container is still starting up.

Wait 10–15 seconds and try the command again.

---

## Error: "403 Forbidden" on Static or Media Files

Nginx has lost read permissions.

Run:

```bash
sudo chown -R www-data:www-data \
~/sites/idwe-backend/staticfiles \
~/sites/idwe-backend/media

sudo chmod -R 755 \
~/sites/idwe-backend/staticfiles \
~/sites/idwe-backend/media
```

---

## Nginx Fails to Reload Due to SSL Errors

Verify that the certificate paths configured in:

```text
/etc/nginx/sites-available/api.idwe.tech
```

match the actual certificate directory:

```text
/etc/letsencrypt/live/
```

---

## 📅 Last Updated

**June 2026**
