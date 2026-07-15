# AUTOMEX Backend — SEO Extras Build Notes

## What was built
Wired the previously-model-only SEO infrastructure (`Redirect`,
`SEOSettings`) into actual working endpoints/middleware: `/sitemap.xml`,
`/robots.txt`, DB-backed redirects, plus JSON equivalents for a Next.js
frontend that prefers to generate its own.

### `/sitemap.xml`
Django's built-in `django.contrib.sitemaps` framework, covering published
Services, Case Studies, Blog Posts, and a short static-pages list. Every
URL points at `FRONTEND_BASE_URL`'s domain (your Next.js site) — not
wherever Django itself happens to be hosted.

**Real bug found and fixed while testing**: Django's sitemap framework
always builds URLs as `f"{protocol}://{domain}{location()}"` — it does
**not** treat an already-absolute URL from `location()` as absolute; it
concatenates regardless. My first pass returned full URLs from
`location()`, producing `https://testserverhttps://automex.tech/...`
(broken, doubled). Fixed by overriding `get_domain()`/`protocol` instead
(so Django's own concatenation lands on the right host) and returning bare
paths from `location()`. Caught by
`test_sitemap_uses_frontend_domain_not_django_host` before it ever shipped.

**Documented assumption**: URLs are flat and English-default —
`{FRONTEND_BASE_URL}/services/{slug}/`, no locale prefix. If your Next.js
routing uses locale-prefixed paths (`/en/services/{slug}`), the
`location()` methods in `apps/core/sitemaps.py` need a one-line adjustment
per sitemap class. Didn't try to guess a full i18n URL scheme without
knowing your actual frontend routing — flagging this explicitly rather
than shipping something confidently wrong.

### `/robots.txt`
Plain Django view (`apps/core/views.py`), dynamically built: disallows
`ADMIN_URL_PATH` and `/api/`, allows everything else, references the
sitemap via `request.build_absolute_uri('/sitemap.xml')` (Django's own
host — see note below if your frontend serves its own separate sitemap).

### Redirect middleware
`apps/core/middleware.py` — `RedirectMiddleware`, registered last in
`MIDDLEWARE`. Deliberately implemented via `process_response()` gated on
`status_code == 404`, not a lookup on every request — the vast majority of
requests resolve successfully, no reason to pay a DB/cache cost on those.
Results cached 5 minutes (your existing Redis cache).

**Real bug found and fixed while testing**: the cache stored the redirect
row's `hit_count` at lookup time, and incremented from *that cached value*
on every hit — so within the 5-minute cache window, repeated hits on the
same redirect kept computing `cached_hit_count + 1` instead of actually
accumulating (a redirect hit 5 times in a row would end at `hit_count=1`,
not `5`). Fixed by decoupling: the cache holds only the (rarely-changing)
redirect target, while `hit_count` always increments atomically against
the live DB value via `F("hit_count") + 1`. Caught by
`test_redirect_increments_hit_count` — first version of that test failed
exactly as described (`1 == 2` assertion failure).

### JSON API alternative (`/api/v1/seo/`)
Since I don't know whether Next.js will consume the XML sitemap directly
or generate its own via `app/sitemap.ts`, added a same-data JSON hedge —
same `X-API-Key` gate as the rest of the content API:

| Endpoint | Returns |
|---|---|
| `GET /api/v1/seo/settings/` | Site name, org schema.org data (legal name, logo, social profiles, contact), GA/GTM IDs, Google Search Console verification |
| `GET /api/v1/seo/sitemap-urls/` | Flat list of `{path, lastmod, priority, changefreq}` for every published Service/CaseStudy/BlogPost |

`SEOSettings` is a singleton (`get_solo()` auto-creates a default row with
sensible fallbacks on first access — confirmed this works correctly:
hitting `/api/v1/seo/settings/` on a completely fresh database returned a
working default row, not an error).

---

## Architecture note: single domain vs. split frontend/API domains
Everything above assumes Django *can* serve `/sitemap.xml` and
`/robots.txt` usefully — true if Django is reverse-proxied under your main
domain, or if search engines are pointed at it directly. If your actual
setup has the Next.js frontend on `automex.tech` and this API on a
separate subdomain (`api.automex.tech`), search engines will crawl
whichever domain **automex.tech** resolves to — meaning the real
`sitemap.xml`/`robots.txt` search engines see needs to live on the
frontend, not here. In that case:
- Use the JSON endpoints above from Next.js's own `app/sitemap.ts` /
  `app/robots.ts` instead of relying on Django's XML/text output.
- Django's own `/sitemap.xml`/`/robots.txt` still work and stay harmless
  (just pointed at the right target domain either way — the `loc` values
  are already `automex.tech`, not the API's own host) — just may end up
  unused depending on your reverse-proxy topology.

Both were built since I didn't want to guess which topology you're
running and block on a clarifying round-trip — whichever one applies, one
of the two approaches is ready to use.

---

## Settings changes
```python
INSTALLED_APPS += ["django.contrib.sitemaps"]
MIDDLEWARE += ["apps.core.middleware.RedirectMiddleware"]  # must run last
```
```python
# config/urls.py
path("sitemap.xml", sitemap, {"sitemaps": {...}}, name="sitemap"),
path("robots.txt", robots_txt, name="robots-txt"),
path("api/v1/seo/", include("apps.core.api.urls", namespace="seo")),
```

No `django.contrib.sites` needed — deliberately avoided (see the
`get_domain()` override note above) since it adds a whole extra
model/admin surface just to answer "what's our domain," which
`FRONTEND_BASE_URL` already answers.

## No new packages, no new migrations
Pure views/middleware/URL wiring on top of the `Redirect`/`SEOSettings`
models that already existed.

## Tests — 209 passing (187 previous + 22 new)
Coverage: sitemap includes only published content and uses the correct
domain (not Django's own host), robots.txt structure, full redirect
middleware behavior (301 vs 302, inactive redirects correctly 404,
non-matching paths correctly 404, hit-count accumulation, confirms
successful 200 responses are never touched by the middleware), and both
JSON SEO endpoints (API-key enforcement, singleton defaults, published-only
filtering).

```bash
docker compose exec web bash -c "DJANGO_SETTINGS_MODULE=config.settings_test pytest apps/core/tests/test_seo_extras.py apps/core/tests/test_seo_api.py -v"
```

## Try it yourself
```bash
docker compose exec web python manage.py seed_demo_data   # if not already seeded
curl http://localhost:8001/sitemap.xml
curl http://localhost:8001/robots.txt
```

## Next steps
Real SMS/WhatsApp/Slack providers (encrypted credential storage is ready
for this) or API documentation polish for frontend handoff are the
remaining items from the earlier list — otherwise this is a reasonable
point to shift toward frontend integration.
