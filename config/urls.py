# zfix-backend/config/urls.py

from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.sitemaps import BlogPostSitemap, CaseStudySitemap, ServiceSitemap, StaticViewSitemap
from apps.core.views import robots_txt

sitemaps = {
    "services": ServiceSitemap,
    "case-studies": CaseStudySitemap,
    "blog": BlogPostSitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path(settings.ADMIN_URL_PATH, admin.site.urls),

    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots-txt"),

     # Client-facing API v1
    path("api/v1/", include("apps.accounts.api.urls", namespace="accounts")),
    path("api/v1/", include("apps.content.api.urls", namespace="content")),
    path("api/v1/crm/", include("apps.crm.api.urls", namespace="crm")),
    path("api/v1/assistant/", include("apps.assistant.api.urls", namespace="assistant")),
    path("api/v1/seo/", include("apps.core.api.urls", namespace="seo")),

    # OpenAPI schema JSON stays available (useful for codegen tooling even
    # in production); the interactive Swagger UI is dev-only — a browsable
    # map of every endpoint isn't something to leave open on a public prod URL.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]

