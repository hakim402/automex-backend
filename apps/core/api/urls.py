"""
apps/core/api/urls.py
─────────────────────────
Mounted at /api/v1/seo/ from config/urls.py.
"""
from __future__ import annotations

from django.urls import path

from . import seo_views

app_name = "seo"

urlpatterns = [
    path("settings/", seo_views.SEOSettingsView.as_view(), name="seo-settings"),
    path("sitemap-urls/", seo_views.SitemapURLsView.as_view(), name="sitemap-urls"),
]
