"""
apps/core/views.py
─────────────────────
Plain (non-DRF) views: robots.txt. sitemap.xml is handled by Django's own
django.contrib.sitemaps.views.sitemap, wired directly in config/urls.py.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse


def robots_txt(request: HttpRequest) -> HttpResponse:
    """
    Served at /robots.txt. Disallows the admin path and raw API routes
    (nothing there is meant to be indexed), allows everything else, and
    points crawlers at the sitemap.

    NOTE: if your Next.js frontend generates its own separate robots.txt/
    sitemap.xml (common when frontend and API are on different domains),
    this one only matters for whichever domain this Django app is actually
    served under — adjust the Sitemap: line below to point at the
    frontend's sitemap instead if that's where the real one lives.
    """
    lines = [
        "User-agent: *",
        f"Disallow: /{settings.ADMIN_URL_PATH}",
        "Disallow: /api/",
        "Allow: /",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
