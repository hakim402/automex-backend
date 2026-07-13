# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — builder: installs build tools, compiles Python wheels
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install build dependencies (compilers, headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels for all Python packages
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — runtime: only runtime libraries + the app
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime shared libraries (no compilers or -dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Copy pre‑built wheels from the builder stage
COPY --from=builder /wheels /wheels
COPY requirements.txt .

# Install Python packages from wheels (no internet required)
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Create a non‑root user and group
RUN groupadd --system automex && \
    useradd --system --gid automex --create-home automex

# Copy the project code, preserving ownership
COPY --chown=automex:automex . .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media && \
    chown -R automex:automex /app/logs /app/staticfiles /app/media

# Switch to the non‑root user
USER automex

# Expose the application port
EXPOSE 8000

# Default command – overridden for Celery workers in docker-compose
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "config.wsgi:application"]