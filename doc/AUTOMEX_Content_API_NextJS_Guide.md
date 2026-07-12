# AUTOMEX Content API — Next.js Integration Guide

This covers everything the frontend needs to consume the public content API:
auth, language handling, endpoints, response shapes, filtering, and SEO.

---

## 1. Base setup

```
NEXT_PUBLIC_API_BASE_URL=https://api.automex.tech/api/v1
AUTOMEX_API_KEY=<raw key from `python manage.py create_api_key --name "automex-frontend-web"`>
```

`AUTOMEX_API_KEY` is **not** prefixed `NEXT_PUBLIC_` — it must stay server-side
(Server Components / Route Handlers / `getServerSideProps`), never shipped to
the browser. Every request needs it as a header:

```
X-API-Key: <raw key>
```

If the key is missing, invalid, inactive, or expired, every endpoint returns
`403 Forbidden`.

### Minimal fetch wrapper

```ts
// lib/automex-api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL!;
const API_KEY = process.env.AUTOMEX_API_KEY!;

export async function automexFetch<T>(
  path: string,
  { lang, ...init }: RequestInit & { lang?: string } = {}
): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (lang) url.searchParams.set("lang", lang);

  const res = await fetch(url.toString(), {
    ...init,
    headers: { "X-API-Key": API_KEY, ...init.headers },
    next: { revalidate: 300 }, // ISR — matches the API's own 5-15min cache
  });

  if (!res.ok) {
    throw new Error(`AUTOMEX API ${res.status}: ${await res.text()}`);
  }
  return res.json();
}
```

---

## 2. Language handling

Every endpoint resolves the response language in this order:

1. `?lang=fr` query param (highest priority)
2. `Accept-Language` header
3. Falls back to English

Supported codes: `en, es, de, fr, it, nl, zh-hans, ar, fa, ps` (`ar`/`fa`/`ps` are
RTL — set `dir="rtl"` on `<html>` when rendering those).

**Recommended pattern**: pass `lang` explicitly from your Next.js locale
routing (`app/[locale]/...`) rather than relying on `Accept-Language`, so
what the user sees always matches the URL:

```ts
const service = await automexFetch<Service>(`/services/${slug}/`, { lang: locale });
```

If a translation doesn't exist for the requested language, fields fall back
to English automatically (server-side) — you'll never get an empty string
for a missing translation.

---

## 3. Endpoints

All are read-only (`GET`), paginated (`{ count, next, previous, results }`,
20/page) except detail routes.

| Endpoint | Description |
|---|---|
| `GET /services/` | List services. Filters: `?category=<slug>` `?technology=<slug>` `?industry=<slug>` `?is_featured=true` |
| `GET /services/{slug}/` | Full service landing-page payload, incl. nested FAQs |
| `GET /service-categories/` | Nav/grid grouping |
| `GET /technologies/` | Filter: `?category=backend\|frontend\|database\|cloud\|ai\|enterprise\|mobile\|devops` |
| `GET /industries/` | Industry verticals |
| `GET /process-steps/` | Discovery → Planning → ... → Maintenance, globally ordered |
| `GET /faqs/` | Filters: `?category=general\|pricing\|process\|service` `?service=<uuid>` |
| `GET /case-studies/` | Filters: `?industry=<slug>` `?technology=<slug>` `?service=<slug>` `?is_featured=true` |
| `GET /case-studies/{slug}/` | Full case study, incl. gallery |
| `GET /blog/categories/` | |
| `GET /blog/tags/` | |
| `GET /blog/posts/` | Filters: `?category=<slug>` `?tag=<slug>` `?is_featured=true` |
| `GET /blog/posts/{slug}/` | Full post content |
| `GET /team/` | |
| `GET /testimonials/` | Filters: `?related_service=<uuid>` `?related_case_study=<uuid>` `?is_featured=true` |

All list endpoints also support `?search=<term>` (matches title/name fields)
and `?ordering=<field>` / `?ordering=-<field>`.

> Only `status=published` content with `published_at` in the past is ever
> returned — draft/in-review/rejected content is invisible to this API by
> design, so there's no risk of leaking unpublished pages.

---

## 4. Response shapes

### Service — list item
```json
{
  "id": "uuid",
  "slug": "custom-software-development",
  "name": "Custom Software Development",
  "short_description": "...",
  "icon": "lucide:code",
  "hero_image": { "id": "uuid", "url": "https://.../hero.jpg", "alt_text": "...", "width": 1600, "height": 900, "file_type": "image" },
  "category": { "id": "uuid", "name": "Software Development", "slug": "software-development", "icon": "...", "order": 0 },
  "is_featured": true,
  "order": 0
}
```

### Service — detail (adds full content + SEO)
```json
{
  "id": "uuid",
  "slug": "custom-software-development",
  "name": "...", "short_description": "...", "overview": "...",
  "problems_we_solve": "...", "features": "One per line", "benefits": "One per line",
  "icon": "...", "hero_image": { "...": "..." },
  "category": { "...": "..." },
  "technologies": [{ "id": "uuid", "name": "Django", "slug": "django", "category": "backend", "icon": "...", "website_url": "...", "order": 0 }],
  "industries": [{ "id": "uuid", "name": "Healthcare", "slug": "healthcare", "description": "...", "icon": "...", "order": 0 }],
  "faqs": [{ "id": "uuid", "question": "...", "answer": "...", "category": "service", "service": "uuid", "order": 0 }],
  "is_featured": true,
  "published_at": "2026-01-15T10:00:00Z",
  "seo": { "...": "see section 5" }
}
```

Case studies and blog posts follow the same list/detail split. Full field
lists are in the OpenAPI schema (section 6).

---

## 5. The `seo` object — build `<head>` directly from it

Every detail endpoint (`services/{slug}`, `case-studies/{slug}`,
`blog/posts/{slug}`) includes a `seo` object with fallbacks already resolved
server-side — the frontend should not reimplement any fallback logic:

```json
{
  "meta_title": "Custom Software Development | AUTOMEX",
  "meta_description": "...",
  "meta_keywords": "...",
  "canonical_url": "",
  "og_title": "Custom Software Development",
  "og_description": "...",
  "og_image": "https://.../hero.jpg",
  "og_type": "website",
  "twitter_card": "summary_large_image",
  "robots_meta_content": "index, follow",
  "sitemap_priority": "0.5",
  "sitemap_changefreq": "monthly",
  "structured_data_type": "Service"
}
```

### Next.js App Router — `generateMetadata`

```ts
export async function generateMetadata({ params }): Promise<Metadata> {
  const service = await automexFetch<Service>(`/services/${params.slug}/`, { lang: params.locale });
  const { seo } = service;

  return {
    title: seo.meta_title,
    description: seo.meta_description,
    keywords: seo.meta_keywords || undefined,
    alternates: seo.canonical_url ? { canonical: seo.canonical_url } : undefined,
    robots: seo.robots_meta_content,
    openGraph: {
      title: seo.og_title,
      description: seo.og_description,
      images: seo.og_image ? [seo.og_image] : undefined,
      type: seo.og_type,
    },
    twitter: { card: seo.twitter_card },
  };
}
```

### JSON-LD

`structured_data_type` tells you which schema.org type to wrap the response
in. Minimal example for a Service:

```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      "@context": "https://schema.org",
      "@type": service.seo.structured_data_type, // "Service"
      name: service.name,
      description: service.short_description,
      provider: { "@type": "Organization", name: "AUTOMEX" },
    }),
  }}
/>
```

---

## 6. OpenAPI schema & interactive docs

The full, always-current schema (every field, every filter) is generated by
drf-spectacular:

- Swagger UI: `GET /api/schema/docs/`
- Raw OpenAPI JSON: `GET /api/schema/`

Point an OpenAPI codegen tool (e.g. `openapi-typescript`) at `/api/schema/`
to generate typed fetch clients automatically instead of hand-writing
interfaces.

---

## 7. Rate limits & caching

- Public content endpoints are throttled at **300 requests/minute per client**
  (the `X-API-Key`, not per-IP) — plenty for SSR/ISR traffic, not intended
  for client-side polling.
- Responses are cached server-side (Redis) for 5–15 minutes. Combine with
  Next.js `revalidate` (as in the fetch wrapper above) for a two-layer cache
  — content changes propagate within minutes, not instantly, which is the
  right tradeoff for marketing content.

---

## 8. Error shapes

| Status | Meaning |
|---|---|
| `403` | Missing/invalid/inactive/expired `X-API-Key` |
| `404` | Slug not found, or exists but isn't published |
| `429` | Rate limit exceeded |
| `400` | Invalid filter/query param value |

```json
{ "detail": "A valid X-API-Key header is required." }
```
