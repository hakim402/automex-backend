# zfix-backend/config/urls.py

from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path(settings.ADMIN_URL_PATH, admin.site.urls),
     # Client-facing API v1
    path("api/v1/", include("apps.accounts.api.urls", namespace="accounts")),
    path("api/v1/", include("apps.content.api.urls", namespace="content")),
    path("api/v1/crm/", include("apps.crm.api.urls", namespace="crm")),
    path("api/v1/assistant/", include("apps.assistant.api.urls", namespace="assistant")),

    # OpenAPI schema JSON stays available (useful for codegen tooling even
    # in production); the interactive Swagger UI is dev-only — a browsable
    # map of every endpoint isn't something to leave open on a public prod URL.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]

