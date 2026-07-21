# AUTOMEX Backend — Contributor's Handbook

How to add features to this Django REST Framework backend: models, API
endpoints, tests, and admin panels, following the conventions already
established across all 6 apps.

---

## 1. Project Anatomy

```
apps/
├── accounts/      Auth (JWT, OAuth, magic links, password reset)
├── assistant/     AI Chat — OpenAI/Claude/Gemini providers, extraction
├── content/       Public website content — services, blog, portfolio, etc.
├── core/          Shared abstractions — base models, mixins, API keys, SEO
├── crm/           Lead capture, bookings, support tickets, dashboard
└── notifications/ Email + in-app notifications (Celery tasks)

config/
├── settings.py    All Django/DRF/parler/Celery configuration
├── urls.py        Root URLConf — mounts all app routers
└── celery.py      Celery app configuration
```

**Two API surfaces co-exist:**

| Surface | Auth | Gate | Throttle scope | Examples |
|---|---|---|---|---|
| **Public Content** | `X-API-Key` header | `HasValidAPIKey` | `public_content` | services, blog, partners |
| **Public Write** | `X-API-Key` header | `HasValidAPIKey` | `public_write` | contact form, bookings |
| **Dashboard** | `Bearer <JWT>` | `IsAuthenticated` | none (per-user) | CRM dashboard, tickets |
| **Guest** | `X-API-Key` + `X-Guest-Token` | `HasValidAPIKey` | `public_content` | guest ticket tracking |

---

## 2. Adding a New Model

### 2.1 Choose Your Mixins

Every model in this project uses these from `apps.core.models`:

```
UUIDModel          → uuid.UUID4 PK (not auto-increment integers)
TimeStampedModel   → created_at, updated_at
OrderableModel     → order field for drag-to-sort (0..n)
PublishableModel   → draft/in_review/approved/published/archived workflow
SoftDeleteModel    → deleted_at soft-delete (CRM contacts, leads)
SEOFieldsMixin     → meta_title, og_image, robots_*, sitemap_* (content)​
```

**Three model archetypes in this project:**

#### Archetype A: Plain Reference Data (no translations, no workflow)

```python
# apps/content/models/partners.py
class Partner(UUIDModel, TimeStampedModel, OrderableModel):
    name         = models.CharField(_("name"), max_length=200)
    slug         = models.SlugField(_("slug"), max_length=220, unique=True)
    logo         = models.ForeignKey("core.MediaAsset", ...)
    partner_type = models.CharField(choices=PartnerType.choices, db_index=True)
    is_active    = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]
```

#### Archetype B: Translated Content (django-parler, multiple languages)

```python
# apps/content/models/services.py
class Service(
    TranslatableModel,          # ← parler — translations table
    UUIDModel, TimeStampedModel,
    OrderableModel, PublishableModel, SEOFieldsMixin,
):
    translations = TranslatedFields(
        name              = models.CharField(_("name"), max_length=200),
        slug              = models.SlugField(_("slug"), max_length=220, db_index=True),
        short_description = models.CharField(...),
        overview          = models.TextField(...),
        **seo_translated_fields(),       # ← per-language meta_title, meta_description, etc.
        meta={"unique_together": [("language_code", "slug")]},
    )

    # Shared (language-independent) fields go here
    category  = models.ForeignKey(ServiceCategory, ...)
    is_enterprise = models.BooleanField(default=False, db_index=True)
    technologies = models.ManyToManyField(Technology, ...)

    objects = PublishableTranslatableManager()
```

> **Key rule:** Parler's `_translated` fields exist on a separate database
> table. `slug` is NOT a real column on the base table — you MUST use
> `.translated(language_code, slug=...)` or `.language(language_code)` to
> query by translated fields. The `TranslatedSlugLookupMixin` (see §3.1)
> handles this for API views.

#### Archetype C: Child Model (FK to a parent, no standalone API)

```python
class ServiceDeliverable(UUIDModel, TimeStampedModel, OrderableModel):
    service     = models.ForeignKey(Service, on_delete=models.CASCADE,
                                    related_name="deliverables")
    title       = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    icon        = models.CharField(_("icon"), max_length=100, blank=True)
```

> These never have their own API endpoint. They're serialized as nested
> arrays through their parent's `SerializerMethodField` — see §3.2.

### 2.2 Register the Admin

Three Unfold admin mixins exist in `apps/core/admin_mixins.py`:

| Mixin | For models with |
|---|---|
| `PublishableAdminMixin` | `status` workflow (Service, CaseStudy, BlogPost) |
| `ActiveToggleAdminMixin` | plain `is_active` (Partner, Technology, FAQ) |

Example registration:

```python
# apps/content/admin.py
from apps.core.admin_mixins import ActiveToggleAdminMixin

@admin.register(Partner)
class PartnerAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["name", "partner_type", "tier", "display_active", "order"]
    list_filter = [("partner_type", ChoicesDropdownFilter), ("tier", ChoicesDropdownFilter)]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["logo"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    list_filter_submit = True
    warn_unsaved_form = True
```

For translated models, insert `TranslatableAdmin` before `ModelAdmin`:

```python
class IndustryAdmin(ActiveToggleAdminMixin, TranslatableAdmin, ModelAdmin):
    search_fields = ["translations__name", "translations__slug"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")
```

### 2.3 Make Migrations

```bash
docker compose exec web python manage.py makemigrations content
```

> **Important:** Because the project uses django-parler and
> django-celery-results at top level, removing them triggers recursion
> errors in `makemigrations`. Make sure requirements.txt is intact
> before running migrations. The Docker image always installs the
> complete `requirements.txt`.

---

## 3. Adding a Public API Endpoint (API-Key Gated)

### 3.1 Create the ViewSet

```python
# apps/content/api/views.py
class PartnerViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PartnerSerializer
    filterset_class = PartnerFilter
    lookup_field = "slug"

    def get_queryset(self):
        return Partner.objects.filter(is_active=True)\
            .select_related("logo")\
            .order_by("order", "name")
```

**`PublicContentViewSetMixin` must always come first** in the MRO. It:

- Removes JWT auth (`authentication_classes = []`)
- Applies API-key permission (`permission_classes = [HasValidAPIKey]`)
- Sets rate limiting (`throttle_scope = "public_content"`)
- Resolves the request language from `?lang=` or `Accept-Language` header
- Puts `language_code` into the serializer context

**For translated models**, also mix in `TranslatedSlugLookupMixin`:

```python
class ServiceViewSet(
    TranslatedSlugLookupMixin,     # ← handles parler slug lookup
    PublicContentViewSetMixin,
    viewsets.ReadOnlyModelViewSet,
):
```

This overrides `get_object()` to use
`.translated(self.language_code, slug=lookup_value)` instead of the
default `queryset.get(slug=...)`.

### 3.2 Write the Serializer

```python
# apps/content/api/serializers/partners.py
class PartnerSerializer(serializers.ModelSerializer):
    partner_type_display = serializers.SerializerMethodField()
    tier_display         = serializers.SerializerMethodField()
    logo                 = MediaAssetSerializer(read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id", "name", "slug", "description",
            "partner_type", "partner_type_display",
            "tier", "tier_display",
            "logo", "website_url", "is_active", "order",
        ]

    def get_partner_type_display(self, obj): return obj.get_partner_type_display()
    def get_tier_display(self, obj):         return obj.get_tier_display()
```

**Patterns to follow:**

- **MediaAsset fields**: Use `MediaAssetSerializer(read_only=True)` — it
  outputs `{id, file, alt_text, width, height, mime_type}`.
- **Display labels**: Always expose both the raw value AND its
  `.get_*_display()` for choices fields.
- **List vs Detail**: For expensive models (Service, PortfolioProject,
  BlogPost), define a `*ListSerializer` and `*DetailSerializer`. The
  ViewSet switches via `get_serializer_class()` based on `self.action`.
- **Nested sub-models**: Use `SerializerMethodField` with a
  `_prefetched_or_query()` helper:

```python
class ServiceDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    deliverables = serializers.SerializerMethodField()

    def get_deliverables(self, obj):
        qs = self._prefetched_or_query(obj, "deliverables")
        return ServiceDeliverableSerializer(qs, many=True).data

    def _prefetched_or_query(self, obj, related_name):
        """Use prefetch cache when available; fall back to DB query."""
        if hasattr(obj, "_prefetched_objects_cache") and related_name in obj._prefetched_objects_cache:
            return obj._prefetched_objects_cache[related_name]
        return getattr(obj, related_name).all()
```

This prevents N+1 queries when the ViewSet uses `prefetch_related()`.

### 3.3 Write the Filter (Optional)

```python
# apps/content/api/filters.py
class PartnerFilter(filters.FilterSet):
    partner_type = filters.CharFilter(field_name="partner_type")
    tier         = filters.CharFilter(field_name="tier")

    class Meta:
        model = Partner
        fields = ["partner_type", "tier"]
```

### 3.4 Register the Route

```python
# apps/content/api/urls.py
router.register("partners", views.PartnerViewSet, basename="partner")
```

The URL prefix (`partners`) becomes `/api/v1/partners/` because
`config/urls.py` includes this router at `path("api/v1/", ...)`.

### 3.5 Update the Export Chain

```python
# apps/content/api/serializers/__init__.py
from .partners import PartnerSerializer
```

### 3.6 Update drf-spectacular Annotations (Recommended)

For endpoints with list/detail serializer switching, add schema annotations:

```python
@extend_schema_view(
    list=extend_schema(responses=PartnerSerializer(many=True)),
    retrieve=extend_schema(responses=PartnerSerializer),
)
class PartnerViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    ...
```

This ensures the OpenAPI schema (used by Next.js for TypeScript generation)
correctly documents both list and detail response shapes.

---

## 4. Adding a JWT Dashboard Endpoint

Dashboard endpoints live in `apps/crm/api/dashboard_views.py` and use the
`DashboardMixin` pattern:

### 4.1 Simple Read-Only List

```python
class DashboardBookingListView(DashboardMixin, generics.ListAPIView):
    serializer_class = DashboardBookingSerializer
    pagination_class = PageNumberPagination
    filterset_fields = ["status"]

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ConsultationBooking.objects.filter(user=self.request.user)\
            .select_related("lead", "slot")\
            .order_by("-scheduled_date")
```

**Rules:**
- Always use `pagination_class = PageNumberPagination` for list views
- Use `filterset_fields` for simple status/type filtering
- Always scope to `self.request.user` — never expose other users' data
- Use `select_related` / `prefetch_related` to avoid N+1 queries

### 4.2 Write / Action Endpoint

```python
class DashboardBookingCancelView(DashboardMixin, APIView):
    def post(self, request, pk):
        booking = ConsultationBooking.objects.select_related("lead")\
            .get(pk=pk, user=request.user)

        if booking.status in [ConsultationBooking.Status.CANCELLED, ...]:
            return Response({"detail": "Already cancelled."}, status=400)

        booking.status = ConsultationBooking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=["status", "cancelled_at", "updated_at"])

        # Log activity → audit trail
        LeadActivity.objects.create(
            lead=booking.lead,
            activity_type=LeadActivity.ActivityType.OTHER,
            description=f"Booking #{booking.id} cancelled by client.",
            performed_by=request.user,
        )

        return Response({"detail": "Booking cancelled."})
```

### 4.3 Register the Route

```python
# apps/crm/api/urls.py — in the dashboard_urlpatterns list
path("dashboard/my-feature/", MyFeatureView.as_view(), name="dashboard-my-feature"),
```

### 4.4 Write the Serializer

Dashboard serializers go in `apps/crm/api/dashboard_serializers.py`.
Keep them flat and user-scoped — they only serialize what the user
owns, not internal admin fields.

---

## 5. Adding a Public Write Endpoint (Contact Form, Booking, etc.)

Public write endpoints are API-key gated (same as content), with
business logic delegated to a `services.py` module.

### 5.1 Write the Service Function

```python
# apps/crm/services.py
@transaction.atomic
def capture_contact_lead(*, request, validated_data: dict, user=None) -> Lead:
    lead = Lead.objects.create(
        lead_type=Lead.LeadType.CONTACT,
        status=Lead.Status.NEW,
        user=user,
        **validated_data,
        **_client_meta(request),     # ← IP, user-agent, referrer
    )
    _log_activity(lead, LeadActivity.ActivityType.OTHER, "Lead captured via contact form.")
    _notify(lead)                    # ← enqueue admin notification (Celery)
    _notify_user_request_submitted(lead)
    return lead
```

**Every write function MUST:**
- Be wrapped in `@transaction.atomic`
- Accept `request` for server-captured attribution (IP, user-agent)
- Call `_log_activity()` for audit trails
- Call `_notify()` to enqueue admin notification
- Catch notification failures — never let an email failure break the API

### 5.2 Write the View

```python
# apps/crm/api/views.py
class ContactLeadCreateView(CreateAPIView):
    authentication_classes = []
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_write"

    serializer_class = ContactLeadSerializer

    @extend_schema(responses=LeadSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead = services.capture_contact_lead(
            request=request,
            validated_data=serializer.validated_data,
            user=request.user if request.user.is_authenticated else None,
        )

        return Response(LeadSerializer(lead).data, status=201)
```

### 5.3 Rate Limit Definitions

Rate limits are defined in `config/settings.py` under
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`. Check existing scopes
before adding a new one — most writes use `public_write`.

---

## 6. Testing

### 6.1 Test Configuration

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py *_tests.py
```

Run all tests:
```bash
docker compose exec web pytest
```

Run a single app:
```bash
docker compose exec web pytest apps/content/tests/
```

### 6.2 Factory Pattern

No factory_boy dependency. Factories are plain Python functions in
`apps/<app>/tests/factories.py`:

```python
def create_partner(**kwargs) -> Partner:
    defaults = dict(
        name="AWS", slug="aws",
        partner_type=Partner.PartnerType.CLOUD,
        tier=Partner.Tier.PLATINUM,
        is_active=True,
    )
    defaults.update(kwargs)
    return Partner.objects.create(**defaults)
```

For translated models, set parler language after creation:

```python
def create_service(*, language_code="en", name="Dev", slug="dev",
                   status=PublishableModel.Status.PUBLISHED, **kwargs) -> Service:
    fields = dict(status=status)
    if status == PublishableModel.Status.PUBLISHED:
        fields["published_at"] = timezone.now()
    fields.update(kwargs)

    service = Service.objects.create(**fields)
    service.set_current_language(language_code)
    service.name = name
    service.slug = slug
    service.short_description = f"{name} short description."
    service.save()
    return service
```

### 6.3 Test Writing Conventions

```python
"""apps/content/tests/test_api_extended.py"""
import pytest
from rest_framework.test import APIClient
from apps.core.models import APIKey
from .factories import create_partner

pytestmark = pytest.mark.django_db        # ← every test needs DB access


@pytest.fixture
def raw_api_key() -> str:
    _, raw_key = APIKey.generate(name="test-frontend")
    return raw_key


@pytest.fixture
def client_with_key(raw_api_key) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=raw_api_key)
    return client


def test_partners_list_requires_api_key():
    """Reject requests without an API key."""
    client = APIClient()
    response = client.get("/api/v1/partners/")
    assert response.status_code == 403


def test_partners_list_accepts_valid_api_key(client_with_key):
    """List endpoint returns 200 with valid key."""
    create_partner(slug="aws", is_active=True)
    response = client_with_key.get("/api/v1/partners/")
    assert response.status_code == 200
    assert response.data["count"] >= 1          # paginated
```

**Test naming convention:**
- `test_<endpoint>_<scenario>` — e.g., `test_partners_list_excludes_inactive`
- `test_<endpoint>_<scenario_with_underscores>` — no camelCase

**Coverage checklist for every new endpoint:**
1. Auth rejection test (missing API key or JWT → 403/401)
2. Successful list test (200 + count in response)
3. Successful detail test (200 + key fields present)
4. Filtering test (query params narrow results)
5. 404 test (nonexistent slug → 404)
6. Active/published filtering test (inactive → excluded)

---

## 7. Conventions

### 7.1 File-Level

| Rule | Detail |
|---|---|
| `from __future__ import annotations` | Every Python file — enables PEP 604 union syntax |
| Module docstring | Every file starts with `"""apps/<app>/<path>.py"""` and a brief description |
| Section separators | `# ── HEADING ──` with 78-column dashes |
| Logger | `logger = logging.getLogger("apps.<app>")` — never `__name__` |

### 7.2 Imports

- **core models**: `from apps.core.models import UUIDModel, TimeStampedModel`
- **core permissions**: `from apps.core.permissions import HasValidAPIKey`
- **model imports**: always use the stringified path in ForeignKey, e.g.,
  `ForeignKey("core.MediaAsset", ...)` — never import the class into the
  models file to avoid circular imports
- **translation**: `from django.utils.translation import gettext_lazy as _`
  — every user-facing string MUST be wrapped in `_()`

### 7.3 Models

- **Primary key**: Always `UUIDModel` (UUID4), never auto-increment integers
- **Verbose names**: Every field gets `verbose_name=_("...")` using
  lowercase, no trailing punctuation — matching Django admin default style
- **related_name**: FK fields use `related_name="+"` when a reverse is
  unnecessary (most MediaAsset FKs). Through-model FKs use meaningful names:
  `related_name="deliverables"`, `related_name="service_links"`
- **Index ordering**: Use `db_index=True` on fields used in `.filter()`
  and `.order_by()` — not on every field
- **`__str__`**: Return the most human-readable field, never the UUID

### 7.4 API Views

- **Queryset**: Always defined in `get_queryset()`, never as a class-level
  attribute — because language resolution happens per-request
- **Pagination**: All list views use `PageNumberPagination` (DRF default)
  which outputs `{count, next, previous, results}`
- **Language resolution**: Content views resolve via
  `?lang=xx` → `Accept-Language` → Django's `LANGUAGE_CODE` default
- **Error format**: `{"detail": "Human-readable message."}` — always a dict

### 7.5 Errors & Logging

- **Never expose raw exceptions** to the API. Catch and return
  `{"detail": "message"}` with the appropriate HTTP status
- **Notification failures** must NEVER break the user-facing response.
  Always `try/except` around `_notify()` calls
- **`logger.exception()`** (includes traceback) for unexpected errors;
  **`logger.warning()`** for validation/edge cases;
  **`logger.info()`** for business events (user registered, lead created);
  **`logger.debug()`** for detailed traces

### 7.6 drf-spectacular

- Add `@extend_schema_view` decorators on ViewSets that use
  `get_serializer_class()` to switch between list/detail serializers
- Add `@extend_schema` on individual methods with request/response bodies
- The OpenAPI schema is used by Next.js for automatic TypeScript generation
  via `openapi-typescript`

---

## 8. PR-Ready Checklist

Before opening a PR for a new feature:

```
□ Each new model uses UUIDModel + TimeStampedModel + appropriate mixins
□ Each new model has verbose_name on every field
□ Each user-facing string is wrapped in gettext_lazy _()
□ Admin is registered (with TabularInlines for child models)
□ makemigrations ran → new migration file present
□ manage.py check returns no errors
□ Public API: PublicContentViewSetMixin applied, API-key tested
□ Dashboard: DashboardMixin + IsAuthenticated, scoped to request.user
□ Select_related / prefetch_related on every list queryset
□ Filterset_class or filterset_fields for list endpoints
□ Write endpoints wrapped in @transaction.atomic
□ Write endpoints call _notify() in try/except
□ Factories created for each new model
□ Tests cover: auth rejection, 200 list, 200 detail, filtering, 404
□ All tests pass: docker compose exec web pytest
□ drf-spectacular annotations updated
□ OpenAPI schema regenerated (docker compose exec web python manage.py spectacular --file schema.yml)
```

---

## 9. Quick Reference: File-by-File

| What you're adding | Files to touch |
|---|---|
| **New model** | `apps/<app>/models/<file>.py` → `apps/<app>/models/__init__.py` → `apps/<app>/admin.py` → `makemigrations` |
| **Public read endpoint** | `serializers/<file>.py` → `api/views.py` → `api/filters.py` (optional) → `api/urls.py` → `tests/factories.py` → `tests/test_api_*.py` |
| **Dashboard list endpoint** | `api/dashboard_serializers.py` → `api/dashboard_views.py` → `api/urls.py` → tests |
| **Dashboard write endpoint** | `services.py` → `api/dashboard_views.py` → `api/dashboard_serializers.py` → `api/urls.py` → tests |
| **Public write endpoint** | `services.py` → `api/views.py` → `api/serializers.py` → `api/urls.py` → tests |
