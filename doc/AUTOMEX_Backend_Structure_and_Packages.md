# AUTOMEX Backend — New Apps, Packages & Settings

## 1. New Project Structure

We started with 13 one-model-per-app packages and consolidated into **5 new
bounded-context apps** (plus your existing `accounts`) — matches how the
domains actually get worked on, and keeps `INSTALLED_APPS` / migration
dependency graphs sane.

```
apps/
├── accounts/          (yours — untouched)
│
├── core/               # Shared abstractions — no admin-facing data model
│   ├── models/
│   │   ├── base.py       → UUIDModel, TimeStampedModel, SoftDeleteModel,
│   │   │                    OrderableModel, PublishableModel
│   │   ├── media.py       → MediaAsset (centralized upload library)
│   │   ├── seo.py         → seo_translated_fields(), SEOFieldsMixin,
│   │   │                    SEOSettings (singleton), Redirect
│   │   └── revision.py    → ContentRevision (generic audit/version log)
│
├── content/            # Everything a marketing editor touches
│   ├── models/
│   │   ├── taxonomy.py    → ServiceCategory, Technology, Industry,
│   │   │                    ProcessStep, FAQ
│   │   ├── services.py    → Service
│   │   ├── case_studies.py→ CaseStudy, CaseStudyGalleryImage
│   │   ├── blog.py        → BlogCategory, BlogTag, BlogPost
│   │   ├── team.py        → TeamMember
│   │   └── testimonials.py→ Testimonial
│
├── crm/                 # The entire conversion pipeline
│   ├── models/
│   │   ├── leads.py       → Lead, QuoteRequestDetail, LeadActivity,
│   │   │                    NewsletterSubscriber
│   │   ├── booking.py     → AvailabilitySlot, ConsultationBooking
│   │   └── calculator.py  → CostCalculatorRule, CalculatorSubmission
│
├── assistant/           # AI Sales Assistant
│   └── models.py          → AIConversation, AIMessage, AIKnowledgeEntry
│
└── notifications/       # Enterprise multi-channel notification system
    └── models.py          → NotificationTemplate, NotificationProviderConfig,
                              Notification, NotificationDeliveryAttempt,
                              NotificationPreference
```

Why apps are split into `models/` **packages** (multiple files) instead of
one `models.py`: Django only cares that `apps.<name>.models` is importable
— it doesn't need to be a single file. Splitting by sub-domain keeps each
file under ~150 lines and makes git diffs/reviews sane as the CMS grows,
while `models/__init__.py` re-exports everything so imports elsewhere stay
simple: `from apps.content.models import Service, CaseStudy`.

**Validated**: `python manage.py check` passes with zero issues, and
`makemigrations` generates cleanly for all 5 new apps with no FK/constraint
errors — the code in the zip is not just written, it's been run through
Django's own consistency checks.

---

## 2. The SEO System (the actual ask this round)

Three layers, used together on every public content model
(`Service`, `CaseStudy`, `BlogPost`):

| Layer | Where | What it does |
|---|---|---|
| **Per-language meta** | `seo_translated_fields()` → spliced into each model's `TranslatedFields()` | `meta_title`, `meta_description`, `meta_keywords`, `canonical_url` — these genuinely differ per language, so they live inside django-parler's translation table, not on the shared row. |
| **Language-independent controls** | `SEOFieldsMixin` (mixed into the model class itself) | Open Graph image/type, Twitter card type, `robots_index`/`robots_follow` (→ `.robots_meta_content` property gives you `"index, follow"` ready for `<meta>`), sitemap `priority`/`changefreq`, and `structured_data_type` (schema.org type for JSON-LD — auto-set in each model's `save()`, e.g. Service → `"Service"`, BlogPost → `"BlogPosting"`). |
| **Site-wide defaults** | `SEOSettings` (singleton via `SEOSettings.get_solo()`) + `Redirect` | Default title suffix, default meta description/OG image, full Organization schema data (legal name, logo, `sameAs` social profiles, contact info) for the JSON-LD injected site-wide, plus GA/GTM/Search-Console IDs. `Redirect` is a 301/302 table for retired URLs — critical when a site restructures and you don't want to lose search rankings. |

This avoids duplicating 4 SEO fields × 13 translated models × 10 languages
by hand, and gives you real enterprise SEO controls (robots directives,
sitemap hints, structured data typing) that the earlier draft didn't have.

---

## 3. New Packages to Add

### `requirements.txt` additions

```txt
django-parler==2.3            # Multi-language content (10 languages incl. RTL)
```

Everything else your project already needs (`djangorestframework`,
`Pillow`, `psycopg2-binary`, `django-redis`, `celery`, `django-celery-beat`,
`drf-spectacular`, `django-cors-headers`, `django-unfold`, `whitenoise`)
is already in your existing `requirements.txt` — nothing else new was
required for this phase.

> When we build the AI Assistant's API logic (next phase), we'll add an
> HTTP client for Groq (`groq` official SDK, or plain `httpx`) — not needed
> yet since this phase is models-only.

### `config/settings.py` changes made

```python
INSTALLED_APPS = [
    ...
    "parler",                    # ← added, third-party section

    # Local apps
    "apps.accounts",
    "apps.core",                 # ← added
    "apps.content",               # ← added
    "apps.crm",                   # ← added
    "apps.assistant",             # ← added
    "apps.notifications",         # ← added
]

# django-parler needs its own LANGUAGES-derived config
PARLER_DEFAULT_LANGUAGE_CODE = "en"
PARLER_LANGUAGES = {
    None: (
        {"code": "en"}, {"code": "es"}, {"code": "de"}, {"code": "fr"},
        {"code": "it"}, {"code": "nl"}, {"code": "zh"}, {"code": "ar"},
        {"code": "fa"}, {"code": "ps"},
    ),
    "default": {"fallbacks": ["en"], "hide_untranslated": False},
}

# Django's own LANGUAGES setting — parler validates its codes against this
LANGUAGES = [
    ("en", _("English")), ("es", _("Spanish")), ("de", _("German")),
    ("fr", _("French")), ("it", _("Italian")), ("nl", _("Dutch")),
    ("zh", _("Chinese")), ("ar", _("Arabic")), ("fa", _("Persian")),
    ("ps", _("Pashto")),
]
```

Also added `from django.utils.translation import gettext_lazy as _` to the
top-level imports (needed for the `LANGUAGES` labels above).

**Not yet configured** (flag for later, once we build the AI/notification
API logic): `GROQ_API_KEY`, and provider credentials for
SendGrid/Twilio/Slack/WhatsApp — intentionally left out of settings for now
since `NotificationProviderConfig` stores these in the database (per-channel,
admin-editable) rather than as static env vars. We should revisit whether
that's the right call once we design the actual sending logic — env vars
are simpler and more secure for secrets; DB storage is more flexible for
multi-provider/multi-account setups. Worth a quick decision before we build
that part.

---

## 4. What Changed From the Original 13-App Draft

- **Removed `**seo_translated_fields()` duplication risk** — same helper,
  but now paired with `SEOFieldsMixin` so SEO is a complete system, not
  just 3 text fields.
- **`MediaAsset` moved into `core`** (was its own `media_library` app) —
  it's a foundational cross-cutting concern used by every content model,
  same category as the abstract mixins.
- **`Redirect` and `SEOSettings` moved into `core`** (was a separate `seo`
  app) — small enough to not warrant its own app entry.
- **`leads` + `booking` + `calculator` merged into `crm`** — all three are
  the same bounded context (the conversion pipeline) and constantly
  reference each other via FK; splitting them just added cross-app
  migration dependencies for no benefit.
- **`case_studies` + `blog` + `testimonials` + `team` merged into
  `content`** alongside the original `cms` — one editorial team touches
  all of this, so one app with clean internal file separation beats four
  apps with identical patterns.

---

## 5. Next Steps

Models are done and validated. Next phase (when you're ready) is the API
logic layer per app — serializers, viewsets, permissions, and the
notification-sending service (Celery tasks + provider adapters). Say the
word and which app to start with.
