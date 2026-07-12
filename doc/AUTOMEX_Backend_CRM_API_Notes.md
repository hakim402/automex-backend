# AUTOMEX Backend — CRM API Build Notes

## What was built
Full write-endpoint layer for `apps.crm`: contact form, quote requests,
consultation booking (with real availability/double-booking enforcement),
and newsletter signup — plus the notification-sending pipeline that fires
on every lead capture.

### `apps.crm`
- **`services.py`** — business logic layer (mirrors `apps.accounts.services.AuthService`):
  `capture_contact_lead()`, `capture_quote_lead()`, `book_consultation()`,
  `available_slots_for_date()`, `subscribe_newsletter()`. Every write
  captures `ip_address`/`user_agent`/`referrer_url` **server-side** from
  the request — never trusted from the payload.
- **`api/serializers.py`** — input validation (only safe, public fields
  accepted — `score`, `status`, `assigned_to` etc. are never settable from
  outside) + minimal "ack" response serializers.
- **`api/views.py`** — 5 endpoints, all API-key gated (same `X-API-Key` as
  the content API) and throttled at a stricter `public_write` scope
  (20/minute vs. content's 300/minute).
- **`admin.py`** — Lead admin with inline quote/booking/activity detail,
  auto-logs a `LeadActivity` on every status change.

### `apps.notifications`
- **`services.py`** — `notify()` (creates a `Notification` row, renders an
  active `NotificationTemplate` if one exists else falls back to
  caller-supplied text, enqueues delivery) + `notify_admins_of_new_lead()`
  (fires on every lead, routes to `settings.ADMIN_NOTIFICATION_EMAILS`).
- **`tasks.py`** — `send_notification_task`, a retrying Celery task. Only
  **EMAIL** actually sends right now (Gmail SMTP, already configured) —
  SMS/WhatsApp/Slack record the attempt and fail clearly
  (`"No provider configured for channel 'slack' yet"`) rather than
  pretending to succeed, so nothing silently vanishes once those providers
  get added.
- **`admin.py`** — read-only Notification log with inline delivery attempts.

---

## Endpoints (mounted at `/api/v1/crm/`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/leads/contact/` | Contact form |
| POST | `/leads/quote/` | Quote request (creates Lead + QuoteRequestDetail) |
| GET | `/bookings/availability/?date=YYYY-MM-DD` | Open slots + remaining capacity for a date |
| POST | `/bookings/consultations/` | Book a consultation (validated against `AvailabilitySlot`) |
| POST | `/newsletter/subscribe/` | Newsletter signup (idempotent) |

All require the same `X-API-Key` header as the content API. All return
`201` with a minimal ack payload (`id`, `status`, `created_at` — never
internal pipeline fields).

### Booking validation (full enforcement, per your decision)
- Rejects past dates
- Rejects a slot whose weekday doesn't match the requested date
- Rejects a time outside the slot's `start_time`–`end_time` window
- Rejects once `max_bookings` is reached for that slot+date, using
  `select_for_update()` so two concurrent requests can't both slip through

---

## Two real bugs found and fixed while testing this

### 1. Stale `queryset=` timestamp (would have silently broken every write endpoint referencing a Service)
`Service.objects.published()` filters on `published_at__lte=timezone.now()`.
Declared as a serializer field's static `queryset=` default (the normal DRF
pattern), `timezone.now()` gets evaluated **once, at module import time** —
freezing the cutoff to server-startup time. Any service published *after*
that would silently fail validation forever (`"object does not exist"`),
even though it's genuinely published and visible on the content API.

**Fix**: reassign the queryset in `__init__()` instead of as a class-level
default, so it's evaluated fresh per-request. Caught by
`test_contact_lead_captures_service_interest` and
`test_quote_request_create_success` — both failed with `400` until fixed.
This is a general pattern worth remembering for any future time-sensitive
`queryset=`.

### 2. Celery app wasn't deterministically wired (test-only symptom, but worth knowing)
`config/__init__.py` was empty. Celery's own documented Django integration
pattern is:
```python
# config/__init__.py
from .celery import app as celery_app
__all__ = ("celery_app",)
```
Without it, which Celery app instance `shared_task` binds to (and therefore
whether it picks up `CELERY_TASK_ALWAYS_EAGER` from the right settings
module) depended on import order — worked fine in production (real broker
always configured the same way) but caused test failures where the eager
task tried to connect to a real Redis broker instead of running
synchronously. Fixed by adding the standard wiring.

---

## Settings changes
```python
ADMIN_NOTIFICATION_EMAILS = env.list("ADMIN_NOTIFICATION_EMAILS", default=[]) or [DEFAULT_FROM_EMAIL]

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["public_write"] = "20/minute"
```
```python
# config/urls.py
path("api/v1/crm/", include("apps.crm.api.urls", namespace="crm")),
```

**Set this in your `.env`** once you have a real sales inbox (currently
falls back to `DEFAULT_FROM_EMAIL`):
```
ADMIN_NOTIFICATION_EMAILS=sales@automex.tech,hello@automex.tech
```

## No new packages, no new migrations
This round was pure service/API/task logic on top of existing models —
`AvailabilitySlot`, `ConsultationBooking`, `Lead`, `QuoteRequestDetail`,
`NewsletterSubscriber`, `Notification` were all already migrated last
round. Nothing to run beyond your normal `git pull` + container restart.

## Before this goes live: seed at least one `AvailabilitySlot`
The booking endpoint has nothing to validate against until you create slots
in the admin (`/admin/crm/availabilityslot/add/`) — e.g. Mon–Fri 9am–5pm UTC.

## Tests — 152 passing (119 previous + 33 new)
```bash
docker compose exec web pytest apps/crm apps/notifications -v
docker compose exec web pytest   # full suite
```
New coverage: API key enforcement, full validation (missing/invalid
fields, internal-field-injection attempts, unpublished-service rejection),
booking conflict/capacity/weekday/time-window validation, newsletter
idempotency, notification template rendering + fallback, Celery task
delivery + retry-skip logic for unimplemented channels, and the
stale-queryset regression itself (so it can't silently come back).

## Next steps
Public-facing write API is done. Natural next phases: the `assistant` app
(AI Sales Assistant chat, Groq-backed, mid-conversation lead capture into
this same `Lead` pipeline) or wiring real SMS/WhatsApp/Slack providers into
`NotificationProviderConfig` + `tasks.py`. Your call.
