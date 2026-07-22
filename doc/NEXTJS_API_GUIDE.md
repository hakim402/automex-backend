# AUTOMEX API — Next.js 16 Integration Guide

> Complete reference for building the AUTOMEX Next.js frontend. Covers every endpoint, TypeScript type generation, auth patterns, SEO, CRM dashboard, and server/client best practices.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [TypeScript Type Generation](#2-typescript-type-generation)
3. [API Client Setup](#3-api-client-setup)
4. [Auth Patterns](#4-auth-patterns)
5. [Public Content API (read-only, API key)](#5-public-content-api-read-only-api-key)
6. [CRM Public API (write, API key)](#6-crm-public-api-write-api-key)
7. [Accounts API (auth, JWT)](#7-accounts-api-auth-jwt)
8. [CRM Dashboard API (JWT)](#8-crm-dashboard-api-jwt)
9. [Notifications API (JWT)](#9-notifications-api-jwt)
10. [SEO & Sitemap API](#10-seo--sitemap-api)
11. [AJAX Sales Assistant API](#11-ai-sales-assistant-api)
12. [CRM Guest API (API key + token)](#12-crm-guest-api-api-key--token)
13. [Language Handling](#13-language-handling)
14. [SEO Patterns (generateMetadata, JSON-LD)](#14-seo-patterns-generatemetadata-json-ld)
15. [Rate Limits & Caching](#15-rate-limits--caching)
16. [Error Handling](#16-error-handling)
17. [Next.js Route Patterns](#17-nextjs-route-patterns)

---

## 1. Quick Start

### Environment Variables

```bash
# .env.local (server-side — NEVER prefix with NEXT_PUBLIC_)
AUTOMEX_API_KEY=automex_live_xxxxxxxxxxxxxxxxxxxxxxxxxxx
AUTOMEX_API_BASE_URL=https://api.automex.tech/api/v1
```

```bash
# .env.local (client-safe — DO prefix with NEXT_PUBLIC_)
NEXT_PUBLIC_API_BASE_URL=https://api.automex.tech/api/v1
```

### Generate an API Key

```bash
docker compose exec web python manage.py create_api_key --name "automex-frontend-web"
# → automex_live_xxxxxxxxxx   ← save this, shown only once
```

The key must be passed in the `X-API-Key` header on every public content/CRM request.

---

## 2. TypeScript Type Generation

### Method 1: openapi-typescript (recommended)

The API exposes a live OpenAPI 3.0 schema at `GET /api/schema/`. Use `openapi-typescript` to generate types automatically — no hand-written interfaces needed.

```bash
npm install -D openapi-typescript
```

```bash
# One-time generation (add this as a package.json script)
npx openapi-typescript https://api.automex.tech/api/schema/ \
  --output src/types/automex-api.ts
```

This creates a `src/types/automex-api.ts` file with every request/response type:

```ts
// src/types/automex-api.ts  (auto-generated — do not edit)
export interface paths {
  "/api/v1/services/": {
    get: {
      parameters: {
        query?: {
          category?: string;
          technology?: string;
          industry?: string;
          is_featured?: boolean;
          search?: string;
          ordering?: string;
          page?: number;
        };
      };
      responses: {
        200: {
          content: {
            "application/json": PaginatedServiceList;
          };
        };
      };
    };
  };
  // ... every endpoint
}

export interface components {
  schemas: {
    ServiceList: { /* ... */ };
    ServiceDetail: { /* ... */ };
    // ... every serializer
  };
}
```

### Method 2: Manual types file

If you prefer hand-written types, create a `src/types/automex.ts` with the response shapes from sections 5–12 of this guide.

### Method 3: Swagger UI

Browse interactive docs with try-it-out:
```
https://api.automex.tech/api/schema/docs/
```

All response shapes are clickable and expandable.

---

## 3. API Client Setup

### Public content/CRM client (server-side only)

```ts
// src/lib/automex-public.ts
const API_BASE = process.env.AUTOMEX_API_BASE_URL!;
const API_KEY = process.env.AUTOMEX_API_KEY!;

interface AutomexOptions extends Omit<RequestInit, "headers"> {
  lang?: string;
  revalidate?: number | false;
}

export async function automexFetch<T>(
  path: string,
  { lang, revalidate = 300, ...init }: AutomexOptions = {}
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (lang) url.searchParams.set("lang", lang);

  const res = await fetch(url.toString(), {
    ...init,
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
      ...init.headers as Record<string, string>,
    },
    ...(revalidate !== undefined ? { next: { revalidate } } : {}),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new AutomexError(res.status, body);
  }
  return res.json();
}

export class AutomexError extends Error {
  constructor(public status: number, body: string) {
    try { const d = JSON.parse(body); super(d.detail || d.message || body); }
    catch { super(body); }
    this.name = "AutomexError";
  }
}
```

### JWT-authenticated client (dashboard, notifications, accounts)

```ts
// src/lib/automex-auth.ts
import { cookies } from "next/headers";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL!; // OK — no secret here

interface AuthFetchOptions extends Omit<RequestInit, "headers"> {
  accessToken: string;
}

export async function automexAuthFetch<T>(
  path: string,
  { accessToken, ...init }: AuthFetchOptions
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...init.headers as Record<string, string>,
    },
    cache: "no-store",
  });

  if (res.status === 401) {
    // Attempt token refresh, retry once
    const refreshToken = (await cookies()).get("refresh_token")?.value;
    if (refreshToken) {
      const refreshRes = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (refreshRes.ok) {
        const { access } = await refreshRes.json();
        // Retry with new token
        const retryRes = await fetch(`${API_BASE}${path}`, {
          ...init,
          headers: {
            "Authorization": `Bearer ${access}`,
            "Content-Type": "application/json",
            ...init.headers as Record<string, string>,
          },
        });
        if (retryRes.ok) return retryRes.json();
      }
    }
    throw new AutomexError(401, "Authentication required");
  }

  if (!res.ok) {
    const body = await res.text();
    throw new AutomexError(res.status, body);
  }
  return res.json();
}
```

---

## 4. Auth Patterns

### Two Auth Mechanisms

| API Group | Auth | Header | Used For |
|---|---|---|---|
| Public Content | `X-API-Key` | Server-side only | Public pages (services, blog, portfolio) |
| Public CRM (write) | `X-API-Key` | Server-side only | Contact forms, bookings, newsletter |
| CRM Guest | `X-API-Key` + `guest_token` | Server-side only | Guest tracking (no login) |
| AI Assistant | `X-API-Key` | Server-side only | Chat widget |
| Accounts | JWT `Bearer` token | Client-side (httpOnly cookie) | Login, register, profile |
| CRM Dashboard | JWT `Bearer` token | Client-side (httpOnly cookie) | User dashboard |
| Notifications | JWT `Bearer` token | Client-side (httpOnly cookie) | User notifications |
| SEO Settings | `X-API-Key` | Server-side only | SEO metadata |

### JWT Token Flow

```
1. POST /api/v1/auth/login/          → { access, refresh }
2. Store access in memory (React state/Zustand)
3. Store refresh in httpOnly cookie (set by API route)
4. On 401 → call POST /api/v1/auth/token/refresh/ with refresh cookie
5. On refresh failure → redirect to /login
```

### API Key Safety Rule

> ⚠️ **NEVER prefix `AUTOMEX_API_KEY` with `NEXT_PUBLIC_`** — If you do, it ships to the browser and anyone can steal it. All `automexFetch` calls must happen in:
> - Server Components (`async` components, no `"use client"`)
> - Route Handlers (`app/api/**/route.ts`)
> - `generateMetadata` / `generateStaticParams`

**For client-side forms (contact, booking)**: create a Next.js Route Handler that proxies to the Django API with the server-side key:

```ts
// app/api/contact/route.ts
import { automexFetch } from "@/lib/automex-public";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const data = await automexFetch("/crm/leads/contact/", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return NextResponse.json(data, { status: 201 });
}
```

```tsx
// Client component
"use client";
async function handleSubmit(formData: ContactInput) {
  const res = await fetch("/api/contact", {   // ← your route handler
    method: "POST",
    body: JSON.stringify(formData),
  });
  // ...
}
```

---

## 5. Public Content API (read-only, API key)

Base: `GET /api/v1/` | Header: `X-API-Key` | Paginated: `{ count, next, previous, results }`

### 5.1 Services

| Endpoint | Description |
|---|---|
| `GET /services/` | List published services. Filters: `?category=<slug>` `?technology=<slug>` `?industry=<slug>` `?is_featured=true` `?search=<term>` `?ordering=order\|published_at` |
| `GET /services/{slug}/` | Full service detail with all sub-models |

**Service List Item:**
```ts
interface ServiceListItem {
  id: string;
  slug: string;
  /** 🔤 */ name: string;
  /** 🔤 */ short_description: string;
  icon: string;                     // e.g. "lucide:code"
  hero_image: MediaAsset | null;
  category: ServiceCategory | null;
  is_featured: boolean;
  order: number;
}
```

**Service Detail** (adds to List):
```ts
interface ServiceDetail extends ServiceListItem {
  /** 🔤 */ overview: string;
  /** 🔤 */ problems_we_solve: string;
  /** 🔤 */ features: string;                 // one per line — split for bullets
  /** 🔤 */ benefits: string;                 // one per line — split for bullets
  thumbnail_image: MediaAsset | null;
  video_presentation: MediaAsset | null;
  brochure: MediaAsset | null;
  service_level: "standard" | "premium" | "enterprise";
  service_level_display: string;
  is_enterprise: boolean;
  technologies: Technology[];
  tech_stack_grouped: Record<string, string[]>;  // {"Frontend":["React"]}
  industries: Industry[];
  pricing_model: "fixed" | "hourly" | "quote" | "subscription" | "retainer";
  pricing_model_display: string;
  starting_price: string | null;    // "5000.00"
  currency: string;                 // "USD"
  delivery_time_estimate: string;   // "4-6 weeks"
  team_size_range: string;          // "5-10 engineers"
  /** 🔤 */ cta_text: string;
  /** 🔤 */ cta_url: string;
  key_metrics: Record<string, number>;  // {"projects_delivered":150}
  enterprise_features: string[];
  // Sub-model arrays (empty [] if none)
  hero_images: Array<{ id: string; image: MediaAsset; /** 🔤 */ caption: string; is_cover: boolean; order: number }>;
  process_steps: Array<{ id: string; /** 🔤 */ title: string; /** 🔤 */ description: string; icon: string; order: number }>;
  deliverables: Array<{ id: string; /** 🔤 */ title: string; /** 🔤 */ description: string; icon: string; order: number }>;
  add_ons: Array<{ id: string; /** 🔤 */ name: string; /** 🔤 */ description: string; price: string; is_included_in_enterprise: boolean; order: number }>;
  comparison_rows: Array<{ id: string; /** 🔤 */ feature_name: string; standard_value: string; premium_value: string; enterprise_value: string; is_highlighted: boolean; order: number }>;
  client_logos: Array<{ id: string; logo: MediaAsset; /** 🔤 */ client_name: string; client_url: string; order: number }>;
  service_testimonials: Array<{ id: string; testimonial_id: string; /** 🔤 */ client_name: string; client_role: string; client_company: string; client_avatar: MediaAsset | null; /** 🔤 */ quote: string; rating: number; is_featured: boolean; order: number }>;
  documents: Array<{ id: string; /** 🔤 */ title: string; /** 🔤 */ description: string; file: MediaAsset; document_type: string; document_type_display: string; is_public: boolean; order: number }>;
  slas: Array<{ id: string; /** 🔤 */ guarantee_name: string; /** 🔤 */ value: string; /** 🔤 */ description: string; icon: string; order: number }>;
  related_services: ServiceListItem[];
  faqs: Array<{ id: string; /** 🔤 */ question: string; /** 🔤 */ answer: string; category: string; service: string; order: number }>;
  published_at: string;
  seo: SEOObject;
}
```

### 5.2 Taxonomy (reference data)

| Endpoint | Filters |
|---|---|
| `GET /service-categories/` | — |
| `GET /technologies/` | `?category=backend\|frontend\|database\|cloud\|ai\|enterprise\|mobile\|devops` |
| `GET /industries/` | — |
| `GET /process-steps/` | — |
| `GET /faqs/` | `?category=general\|pricing\|process\|service` `?service=<uuid>` |

### 5.3 Case Studies

| Endpoint | Filters |
|---|---|
| `GET /case-studies/` | `?industry=<slug>` `?technology=<slug>` `?service=<slug>` `?is_featured=true` `?search=<term>` |
| `GET /case-studies/{slug}/` | Includes gallery images + SEO |

### 5.4 Blog

| Endpoint | Filters |
|---|---|
| `GET /blog/categories/` | — |
| `GET /blog/tags/` | — |
| `GET /blog/posts/` | `?category=<slug>` `?tag=<slug>` `?is_featured=true` `?search=<term>` `?ordering=published_at\|views_count` |
| `GET /blog/posts/{slug}/` | Full content + SEO |

### 5.5 Team & Testimonials

| Endpoint | Filters |
|---|---|
| `GET /team/` | — |
| `GET /testimonials/` | `?related_service=<uuid>` `?related_case_study=<uuid>` `?is_featured=true` |

### 5.6 Partners & Certifications

| Endpoint | Filters |
|---|---|
| `GET /partners/` | `?partner_type=technology\|implementation\|cloud\|integration\|reseller` `?tier=silver\|gold\|platinum\|diamond` |
| `GET /partners/{slug}/` | Detail by slug |
| `GET /certifications/` | `?related_services=<uuid>` |

### 5.7 AI Capabilities & Tech Expertise

| Endpoint | Filters |
|---|---|
| `GET /ai-capabilities/` | `?category=nlp\|computer_vision\|predictive_analytics\|generative_ai\|automation\|rag_agents\|mlops` `?maturity_level=research\|production\|experimental` |
| `GET /ai-capabilities/{slug}/` | Detail with nested technologies |
| `GET /tech-expertise/` | `?category=architecture\|cloud\|data_engineering\|ai\|security\|mobile\|devops\|qa` |
| `GET /tech-expertise/{slug}/` | Detail with nested technologies + case studies |

### 5.8 Portfolio

| Endpoint | Filters |
|---|---|
| `GET /portfolio/` | `?industry=<slug>` `?technology=<slug>` `?service=<slug>` `?is_featured=true` `?search=<term>` `?ordering=order\|completion_year\|created_at` |
| `GET /portfolio/{slug}/` | Detail with gallery images, services, technologies |

### Shared Response Types

> 🔤 Fields marked with `🔤` are **language-dependent** — their value changes based on the `?lang=` query parameter or `Accept-Language` header. When no translation exists for the requested language, the API falls back to English (never returns empty strings). See [Section 13](#13-language-handling) for details.

```ts
interface MediaAsset {
  id: string;
  url: string;
  alt_text: string;
  caption: string;
  width: number;
  height: number;
  file_type: string;              // "image" | "video" | "document"
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ── Taxonomy ───────────────────────────────────────────────────────

interface ServiceCategory {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
  /** 🔤 */ description: string;
  icon: string;
  order: number;
}

interface Technology {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
  category: string;              // "backend" | "frontend" | "database" | "cloud" | "ai" | "enterprise" | "mobile" | "devops"
  icon: string;
  website_url: string;
  order: number;
}

interface Industry {
  id: string;
  /** 🔤 */ name: string;
  /** 🔤 */ slug: string;
  /** 🔤 */ description: string;
  icon: string;
  order: number;
}

interface ProcessStep {
  id: string;
  /** 🔤 */ title: string;
  /** 🔤 */ description: string;
  icon: string;
  order: number;
}

interface FAQ {
  id: string;
  /** 🔤 */ question: string;
  /** 🔤 */ answer: string;
  category: string;              // "general" | "pricing" | "process" | "service"
  service: string | null;        // Service UUID
  order: number;
}

// ── Blog ───────────────────────────────────────────────────────────

interface BlogCategory {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
  /** 🔤 */ description: string;
  order: number;
}

interface BlogTag {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
}

interface BlogAuthor {
  id: string;
  /** 🔤 */ full_name: string;
  /** 🔤 */ bio: string;
  /** 🔤 */ role_title: string;
  slug: string;
  avatar: MediaAsset | null;
  linkedin_url: string;
  github_url: string;
}

// ── Team ───────────────────────────────────────────────────────────

interface TeamMember {
  id: string;
  /** 🔤 */ full_name: string;
  slug: string;
  /** 🔤 */ role_title: string;
  department: string;            // "engineering" | "design" | "ai" | "devops" | "management" | "sales" | "qa" | "other"
  /** 🔤 */ bio: string;
  photo: MediaAsset | null;
  linkedin_url: string;
  github_url: string;
  twitter_url: string;
  is_leadership: boolean;
  order: number;
}

// ── Testimonials ───────────────────────────────────────────────────

interface Testimonial {
  id: string;
  /** 🔤 */ client_name: string;
  /** 🔤 */ client_role: string;
  /** 🔤 */ client_company: string;
  client_avatar: MediaAsset | null;
  /** 🔤 */ quote: string;
  rating: number;                // 1–5
  source: string;                // "manual" | "clutch" | "google" | "linkedin" | "trustpilot"
  source_url: string;
  related_case_study: string | null;
  related_service: string | null;
  is_featured: boolean;
  order: number;
}

// ── Partners & Certifications ──────────────────────────────────────

interface Partner {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
  logo: MediaAsset | null;
  website_url: string;
  partner_type: string;          // "technology" | "implementation" | "cloud" | "integration" | "reseller"
  partner_type_display: string;
  tier: string;                  // "silver" | "gold" | "platinum" | "diamond"
  tier_display: string;
  /** 🔤 */ description: string;
  is_active: boolean;
  order: number;
}

interface Certification {
  id: string;
  /** 🔤 */ name: string;
  /** 🔤 */ issuer: string;
  badge_image: MediaAsset | null;
  credential_url: string;
  credential_id: string;
  issue_date: string | null;
  expiry_date: string | null;
  related_services: string[];    // Service UUIDs
  is_active: boolean;
  order: number;
}

// ── AI Capabilities & Tech Expertise ───────────────────────────────

interface AICapability {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
  /** 🔤 */ description: string;
  category: string;              // "nlp" | "computer_vision" | "predictive_analytics" | "generative_ai" | "automation" | "rag_agents" | "mlops"
  category_display: string;
  maturity_level: string;        // "research" | "production" | "experimental"
  maturity_level_display: string;
  icon: string;
  demo_url: string;
  cover_image: MediaAsset | null;
  related_services: string[];
  technologies: Technology[];
  is_active: boolean;
  order: number;
}

interface TechExpertiseArea {
  id: string;
  /** 🔤 */ name: string;
  slug: string;
  /** 🔤 */ description: string;
  icon: string;
  category: string;              // "architecture" | "cloud" | "data_engineering" | "ai" | "security" | "mobile" | "devops" | "qa"
  category_display: string;
  technologies: Technology[];
  case_studies: string[];
  is_active: boolean;
  order: number;
}

// ── Portfolio ──────────────────────────────────────────────────────

interface PortfolioProjectListItem {
  id: string;
  slug: string;
  /** 🔤 */ title: string;
  /** 🔤 */ short_description: string;
  cover_image: MediaAsset | null;
  /** 🔤 */ client_name: string;
  completion_year: number | null;
  industry: Industry | null;
  is_featured: boolean;
  is_published: boolean;
  order: number;
}

interface PortfolioProjectDetail extends PortfolioProjectListItem {
  services: Array<{ id: string; slug: string; /** 🔤 */ name: string }>;
  technologies: Technology[];
  project_url: string;
  gallery: PortfolioGalleryImage[];
  created_at: string;
}

interface PortfolioGalleryImage {
  id: string;
  image: MediaAsset;
  /** 🔤 */ caption: string;
  order: number;
}

// ── Case Studies ───────────────────────────────────────────────────

interface CaseStudyListItem {
  id: string;
  slug: string;
  /** 🔤 */ title: string;
  client_name: string;
  client_industry: Industry | null;
  thumbnail: MediaAsset | null;
  is_featured: boolean;
  order: number;
  published_at: string;
}

interface CaseStudyDetail extends CaseStudyListItem {
  /** 🔤 */ overview: string;
  /** 🔤 */ challenge: string;
  /** 🔤 */ solution: string;
  /** 🔤 */ results: string;
  client_logo: MediaAsset | null;
  technologies: Technology[];
  gallery: CaseStudyGalleryImage[];
  project_url: string;
  project_duration_weeks: number | null;
  seo: SEOObject;
}

interface CaseStudyGalleryImage {
  id: string;
  media: MediaAsset;
  /** 🔤 */ caption: string;
  order: number;
}
```

---

## 6. CRM Public API (write, API key)

Base: `POST /api/v1/crm/` | Header: `X-API-Key` | Throttle: 20/min

> ⚠️ All write endpoints must be proxied through Next.js Route Handlers — never called from the browser directly.

### 6.1 Contact Form

```
POST /crm/leads/contact/
```

```ts
interface ContactInput {
  full_name: string;
  email: string;
  phone?: string;
  company?: string;
  job_title?: string;
  message?: string;
  service_interest?: string;     // UUID of the Service
  industry?: string;
  budget_range?: string;
  timeline?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  page_url?: string;
}

// Response: { id: string; lead_type: "contact"; status: "new"; created_at: string }
```

### 6.2 Quote Request

```
POST /crm/leads/quote/
```

```ts
interface QuoteInput extends ContactInput {
  requested_services: string[];   // Array of Service UUIDs
  project_description?: string;
  estimated_budget_min?: number;
  estimated_budget_max?: number;
  currency?: string;              // "USD"
}
```

### 6.3 Consultation Booking

```ts
// 1. Check available slots
GET /crm/bookings/availability/?date=2026-08-03

// Response: Array<{ slot_id: string; start_time: string; end_time: string; remaining: number }>
```

```
POST /crm/bookings/consultations/
```

```ts
interface BookingInput extends ContactInput {
  slot: string;                   // UUID of AvailabilitySlot
  scheduled_date: string;         // "2026-08-03"
  scheduled_time: string;         // "14:00:00"
  meeting_type?: "video" | "phone" | "in_person";
  timezone?: string;              // "America/New_York"
  notes?: string;
}
```

### 6.4 Newsletter

```
POST /crm/newsletter/subscribe/
```

```ts
{ email: string; language?: string; source?: string }
// Idempotent — subscribing twice returns 200 without error
```

---

## 7. Accounts API (auth, JWT)

Base: `/api/v1/auth/` | No API key needed | Throttle: 5-20/min depending on endpoint

### 7.1 Authentication

| Method | Endpoint | Body | Response |
|---|---|---|---|
| POST | `/auth/register/` | `{ email, password, full_name }` | `{ access, refresh, user }` |
| POST | `/auth/verify-email/` | `{ token }` | `{ detail }` |
| POST | `/auth/login/` | `{ email, password }` | `{ access, refresh, user }` |
| POST | `/auth/logout/` | `{ refresh }` | `{ detail }` |
| POST | `/auth/token/refresh/` | `{ refresh }` | `{ access }` |
| POST | `/auth/magic-link/request/` | `{ email }` | `{ detail }` (always 200) |
| POST | `/auth/magic-link/verify/` | `{ token }` | `{ access, refresh, user }` |
| POST | `/auth/password-reset/request/` | `{ email }` | `{ detail }` (always 200) |
| POST | `/auth/password-reset/confirm/` | `{ token, new_password }` | `{ detail }` |
| POST | `/auth/google/` | `{ access_token }` | `{ access, refresh, user }` |

### 7.2 Profile

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/auth/me/` | JWT | User profile + nested profile object |
| PATCH | `/auth/me/update/` | JWT | Update name, profile fields, profile picture |
| POST | `/auth/me/change-password/` | JWT | `{ old_password, new_password, confirm_password }` |

### 7.3 Sessions

| Method | Endpoint | Auth |
|---|---|---|
| GET | `/auth/sessions/` | JWT |
| DELETE | `/auth/sessions/{id}/revoke/` | JWT |

---

## 8. CRM Dashboard API (JWT)

Base: `/api/v1/crm/dashboard/` | Auth: `Bearer <token>` | Paginated: 20/page

### 8.1 Summary

```
GET /crm/dashboard/
```

```ts
{ total_requests: number; active_requests: number; total_bookings: number;
  upcoming_bookings: number; total_tickets: number; open_tickets: number;
  total_calculations: number; }
```

### 8.2 Requests / Leads

| Method | Endpoint | Filters |
|---|---|---|
| GET | `/crm/dashboard/requests/` | `?status=new\|contacted\|qualified\|...` `?lead_type=contact\|quote` `?page=1` |
| GET | `/crm/dashboard/requests/{id}/` | Includes `activities` timeline |
| POST | `/crm/dashboard/requests/{id}/message/` | `{ message }` — send message to staff |

### 8.3 Bookings

| Method | Endpoint | Filters |
|---|---|---|
| GET | `/crm/dashboard/bookings/` | `?status=confirmed\|pending\|...` `?page=1` |
| GET | `/crm/dashboard/bookings/{id}/` | Full detail |
| POST | `/crm/dashboard/bookings/{id}/reschedule/` | `{ new_date, new_time, reason? }` |
| POST | `/crm/dashboard/bookings/{id}/cancel/` | Cancels booking (only if not already cancelled/completed) |

### 8.4 Support Tickets

| Method | Endpoint | Filters |
|---|---|---|
| GET | `/crm/dashboard/tickets/` | `?status=open\|in_progress\|...` `?ticket_type=bug\|feature\|...` `?page=1` |
| POST | `/crm/dashboard/tickets/` | `{ title, description, ticket_type, priority?, related_lead?, related_service? }` |
| GET | `/crm/dashboard/tickets/{id}/` | Includes `messages` array with `unread_message_count` |
| POST | `/crm/dashboard/tickets/{id}/messages/` | `{ body }` — reply to ticket |

### 8.5 Calculator Estimates

| Method | Endpoint | Description |
|---|---|---|
| GET | `/crm/dashboard/calculations/` | Past cost estimates, paginated |
| POST | `/crm/dashboard/calculations/{id}/convert/` | Convert estimate to a lead |

---

## 9. Notifications API (JWT)

Base: `/api/v1/notifications/` | Auth: `Bearer <token>`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/notifications/` | List user notifications |
| GET | `/notifications/unread-count/` | `{ count: number }` |
| POST | `/notifications/{id}/mark-read/` | Mark single notification read |
| POST | `/notifications/mark-all-read/` | Mark all read |
| GET | `/notifications/preferences/` | Get notification preferences |
| PUT | `/notifications/preferences/` | Update preferences |

---

## 10. SEO & Sitemap API

Base: `/api/v1/seo/` | Header: `X-API-Key`

| Endpoint | Cache | Description |
|---|---|---|
| `GET /seo/settings/` | 15 min | Site name, org schema.org data, GA/GTM IDs, social profiles |
| `GET /seo/sitemap-urls/` | 60 min | Flat list of `{ path, lastmod, priority, changefreq }` for all published content |

Use these in Next.js `app/sitemap.ts` and `app/robots.ts`:

```ts
// app/sitemap.ts
import { automexFetch } from "@/lib/automex-public";
import type { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const urls = await automexFetch<SitemapURL[]>("/seo/sitemap-urls/", { revalidate: 3600 });
  return urls.map((u) => ({
    url: `https://automex.tech${u.path}`,
    lastModified: u.lastmod,
    changeFrequency: u.changefreq as any,
    priority: u.priority,
  }));
}
```

```ts
// app/robots.ts
import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: "https://automex.tech/sitemap.xml",
  };
}
```

### XML endpoints (Django-hosted, no API key needed)

| URL | Description |
|---|---|
| `GET /sitemap.xml` | Standard XML sitemap |
| `GET /robots.txt` | Robots directives |

---

## 11. AI Sales Assistant API

Base: `POST /api/v1/assistant/chat/` | Header: `X-API-Key` | Throttle: 20/min

```
POST /assistant/chat/
```

```ts
interface ChatRequest {
  message: string;
  session_id?: string;            // omit on first message, use returned ID thereafter
  language?: string;              // "en", "es", etc.
  page_url?: string;              // current page for context
}

interface ChatResponse {
  session_id: string;
  reply: string;
  lead_captured: boolean;         // true once email extracted from conversation
}
```

> ⚠️ Proxy through a Next.js Route Handler — the Groq API key is server-side.

---

## 12. CRM Guest API (API key + token)

Base: `/api/v1/crm/guest/` | Header: `X-API-Key` | For non-logged-in visitors with a `guest_token`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/crm/guest/requests/` | Guest's submitted requests |
| GET | `/crm/guest/requests/{id}/` | Request detail |
| POST | `/crm/guest/tickets/` | Create support ticket as guest |
| GET | `/crm/guest/tickets/{id}/` | Ticket detail |
| POST | `/crm/guest/tickets/{id}/messages/` | Reply to ticket |

---

## 13. Language Handling (i18n)

### Architecture

AUTOMEX uses [django-parler](https://django-parler.readthedocs.io/) for multi-language content via a **shared-model translation table** pattern. Each `TranslatableModel` stores language-dependent fields in a separate translations table. The API resolves the requested language server-side and returns the appropriate translation — the frontend does NOT need to know anything about translation tables.

### Resolution Order

1. `?lang=fr` query param (highest priority)
2. `Accept-Language` HTTP header
3. Falls back to `en` (English)

### Supported Language Codes

| Code | Language | Direction |
|---|---|---|
| `en` | English | LTR |
| `es` | Spanish | LTR |
| `de` | German | LTR |
| `fr` | French | LTR |
| `it` | Italian | LTR |
| `nl` | Dutch | LTR |
| `zh-hans` | Chinese (Simplified) | LTR |
| `ar` | Arabic | **RTL** |
| `fa` | Persian | **RTL** |
| `ps` | Pashto | **RTL** |

> ⚠️ Note: The language code for Chinese is `zh-hans` (not `zh`).
>
> Arabic (`ar`), Persian (`fa`), and Pashto (`ps`) are **RTL languages** — set `dir="rtl"` on the `<html>` element when rendering these locales.

### Fallback Behavior

- **Always-on fallback**: When a translation does not exist for the requested language, the API automatically returns the **English** (`en`) version — never an empty string.
- **New content**: You can add translations incrementally. No content will break while translations are pending.
- **SEO fields** (`meta_title`, `meta_description`, `meta_keywords`) fall back to model-level content fields (e.g. `name` / `title` / `short_description`) when no explicit SEO translation is set.

### What Gets Translated

Every text field that appears on the public-facing website is translatable. Non-text fields (images, URLs, booleans, numbers, enums, UUIDs) are NOT translated — they're the same across all languages.

#### Translated Fields by Model

| Model | Translated Fields |
|---|---|
| **ServiceCategory** | `name`, `description` |
| **Technology** | `name`, `description` |
| **Industry** | `name`, `slug`, `description` |
| **ProcessStep** | `title`, `description` |
| **FAQ** | `question`, `answer` |
| **Service** | `name`, `slug`, `short_description`, `overview`, `problems_we_solve`, `features`, `benefits`, `cta_text`, `cta_url`, `meta_title`, `meta_description`, `meta_keywords` |
| **ServiceHeroImage** | `caption` |
| **ServiceDeliverable** | `title`, `description` |
| **ServiceAddOn** | `name`, `description` |
| **ServiceComparisonRow** | `feature_name` |
| **ServiceClientLogo** | `client_name` |
| **ServiceDocument** | `title`, `description` |
| **ServiceSLA** | `guarantee_name`, `value`, `description` |
| **BlogCategory** | `name`, `description` |
| **BlogTag** | `name` |
| **BlogAuthor** | `full_name`, `bio`, `role_title` |
| **BlogPost** | `title`, `slug`, `excerpt`, `content`, `meta_title`, `meta_description`, `meta_keywords` |
| **BlogHeroImage** | `caption` |
| **CaseStudy** | `title`, `slug`, `overview`, `challenge`, `solution`, `results`, `meta_title`, `meta_description`, `meta_keywords` |
| **CaseStudyGalleryImage** | `caption` |
| **TeamMember** | `full_name`, `role_title`, `bio` |
| **Testimonial** | `client_name`, `client_role`, `client_company`, `quote` |
| **Partner** | `name`, `description` |
| **Certification** | `name`, `issuer` |
| **AICapability** | `name`, `description` |
| **TechExpertiseArea** | `name`, `description` |
| **PortfolioProject** | `title`, `short_description`, `client_name` |
| **PortfolioGalleryImage** | `caption` |

> 💡 In the TypeScript interfaces throughout this guide, translatable fields are marked with `/** 🔤 */` for quick identification.

### Best Practice

Pass `lang` from your Next.js locale routing explicitly:

```tsx
// app/[locale]/services/[slug]/page.tsx
export default async function ServicePage({ params }: { params: { locale: string; slug: string } }) {
  const service = await automexFetch<ServiceDetail>(
    `/services/${params.slug}/`,
    { lang: params.locale }
  );
  // ...
}
```

For SEO `generateMetadata`, always pass `lang` so meta tags are in the correct language:

```ts
export async function generateMetadata({ params }: {
  params: { locale: string; slug: string }
}): Promise<Metadata> {
  const service = await automexFetch<ServiceDetail>(
    `/services/${params.slug}/`,
    { lang: params.locale }
  );
  // service.seo.meta_title is now in params.locale (or English fallback)
  // ...
}
```

### Common Mistakes

❌ **Hardcoding `lang: "en"`** — This bypasses the translation system. Always use the user's current locale.

❌ **Re-fetching for every language** — The `automexFetch` client already includes Next.js `fetch` cache with `revalidate`. Different languages are cached separately by URL (via the `?lang=` query param).

❌ **Duplicating content in the frontend** — Don't store translated strings in your Next.js app. Always fetch them from the API with the correct `lang` parameter.

---

## 14. SEO Patterns (generateMetadata, JSON-LD)

### generateMetadata

Every detail endpoint returns a `seo` object with all meta fields pre-resolved:

```ts
// app/[locale]/services/[slug]/page.tsx
import type { Metadata } from "next";

export async function generateMetadata({ params }: {
  params: { locale: string; slug: string }
}): Promise<Metadata> {
  const service = await automexFetch<ServiceDetail>(
    `/services/${params.slug}/`,
    { lang: params.locale }
  );

  return {
    title: service.seo.meta_title,
    description: service.seo.meta_description,
    keywords: service.seo.meta_keywords || undefined,
    alternates: service.seo.canonical_url
      ? { canonical: service.seo.canonical_url }
      : undefined,
    robots: service.seo.robots_meta_content,
    openGraph: {
      title: service.seo.og_title,
      description: service.seo.og_description,
      images: service.seo.og_image ? [service.seo.og_image] : undefined,
      type: service.seo.og_type as any,
    },
    twitter: { card: service.seo.twitter_card as any },
  };
}
```

### JSON-LD Structured Data

```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      "@context": "https://schema.org",
      "@type": service.seo.structured_data_type,
      name: service.name,
      description: service.short_description,
      provider: { "@type": "Organization", name: "AUTOMEX" },
      ...(service.seo.og_image && { image: service.seo.og_image }),
    }),
  }}
/>
```

### SEO Object Shape

```ts
interface SEOObject {
  meta_title: string;              // already includes "| AUTOMEX" suffix
  meta_description: string;
  meta_keywords: string;
  canonical_url: string;
  og_title: string;
  og_description: string;
  og_image: string | null;
  og_type: string;                 // "website" | "article"
  twitter_card: string;            // "summary_large_image"
  robots_meta_content: string;     // "index, follow" | "noindex, follow" | ...
  sitemap_priority: string;
  sitemap_changefreq: string;      // "monthly" | "weekly" | ...
  structured_data_type: string;    // "Service" | "Article" | "BlogPosting"
}
```

---

## 15. Rate Limits & Caching

| Scope | Limit | Applies To |
|---|---|---|
| `public_content` | 300 req/min per API key | Read-only content endpoints |
| `public_write` | 20 req/min per API key | CRM write endpoints |
| `ai_assistant` | 20 req/min per API key | Chat endpoint |
| `anon` | 100 req/day per IP | Auth endpoints (unauthenticated) |
| `user` | 1000 req/hour per user | Auth endpoints (authenticated) |

### Caching Strategy

| Layer | TTL | What |
|---|---|---|
| Django Redis cache | 5-15 min | API responses |
| Next.js `revalidate` | 300s (5 min) | fetch cache in Server Components |
| Next.js `generateStaticParams` | Build time + revalidate | Static paths for top pages |

**Recommended:** Use `revalidate: 300` in `automexFetch` (matches Django's cache). For real-time data (dashboard), use `revalidate: 0` or `cache: "no-store"`.

---

## 16. Error Handling

### HTTP Status Codes

| Code | Meaning | Response |
|---|---|---|
| `200` | Success | Response data |
| `201` | Created | New resource |
| `400` | Validation error | `{ "field_name": ["error message"] }` |
| `401` | No/invalid JWT | `{ "detail": "Authentication credentials were not provided." }` |
| `403` | Bad/missing API key | `{ "detail": "A valid X-API-Key header is required." }` |
| `404` | Not found | `{ "detail": "Not found." }` |
| `429` | Rate limited | `{ "detail": "Request was throttled." }` |
| `500` | Server error | `{ "detail": "Internal server error." }` |

### DRF Validation Errors

```json
{
  "full_name": ["This field is required."],
  "email": ["Enter a valid email address."],
  "scheduled_date": ["Cannot look up availability for past dates."]
}
```

Map directly to form field errors using the key as the field name.

---

## 17. Next.js Route Patterns

### Pattern 1: Server Component (public content)

```tsx
// app/[locale]/services/page.tsx
import { automexFetch } from "@/lib/automex-public";

export default async function ServicesPage({ params }: { params: { locale: string } }) {
  const { results: services } = await automexFetch<PaginatedResponse<ServiceListItem>>(
    "/services/",
    { lang: params.locale }
  );

  return (
    <main>
      {services.map((s) => <ServiceCard key={s.id} service={s} />)}
    </main>
  );
}
```

### Pattern 2: Route Handler (proxy for write endpoints)

```tsx
// app/api/contact/route.ts
import { NextRequest, NextResponse } from "next/server";
import { automexFetch, AutomexError } from "@/lib/automex-public";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const data = await automexFetch("/crm/leads/contact/", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return NextResponse.json(data, { status: 201 });
  } catch (err) {
    if (err instanceof AutomexError) {
      return NextResponse.json(
        { detail: err.message },
        { status: err.status }
      );
    }
    return NextResponse.json(
      { detail: "Something went wrong." },
      { status: 500 }
    );
  }
}
```

### Pattern 3: Dashboard (client component with JWT)

```tsx
// app/[locale]/dashboard/page.tsx
"use client";
import { useAuth } from "@/hooks/use-auth";
import { automexAuthFetch } from "@/lib/automex-auth";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const { accessToken } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    automexAuthFetch<DashboardSummary>("/crm/dashboard/", { accessToken })
      .then(setSummary);
  }, [accessToken]);

  // ...
}
```

### Pattern 4: generateStaticParams (pre-build dynamic routes)

```ts
// app/[locale]/services/[slug]/page.tsx
export async function generateStaticParams({ params }: { params: { locale: string } }) {
  const { results } = await automexFetch<PaginatedResponse<ServiceListItem>>(
    `/services/?lang=${params.locale}`
  );
  return results.map((s) => ({ slug: s.slug }));
}
```

### Pattern 5: ISR with on-demand revalidation

```ts
// app/api/revalidate/route.ts  (called by Django webhook when content changes)
import { revalidatePath } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { path, secret } = await req.json();
  if (secret !== process.env.REVALIDATION_SECRET) {
    return NextResponse.json({ error: "Invalid secret" }, { status: 401 });
  }
  revalidatePath(path);
  return NextResponse.json({ revalidated: true });
}
```

---

## Quick Reference — All Endpoints

```
# Content (API key)
GET  /api/v1/services/
GET  /api/v1/services/{slug}/
GET  /api/v1/service-categories/
GET  /api/v1/technologies/
GET  /api/v1/industries/
GET  /api/v1/process-steps/
GET  /api/v1/faqs/
GET  /api/v1/case-studies/
GET  /api/v1/case-studies/{slug}/
GET  /api/v1/blog/categories/
GET  /api/v1/blog/tags/
GET  /api/v1/blog/posts/
GET  /api/v1/blog/posts/{slug}/
GET  /api/v1/team/
GET  /api/v1/testimonials/
GET  /api/v1/partners/
GET  /api/v1/partners/{slug}/
GET  /api/v1/certifications/
GET  /api/v1/ai-capabilities/
GET  /api/v1/ai-capabilities/{slug}/
GET  /api/v1/tech-expertise/
GET  /api/v1/tech-expertise/{slug}/
GET  /api/v1/portfolio/
GET  /api/v1/portfolio/{slug}/

# CRM Public (API key — proxy through route handlers)
POST /api/v1/crm/leads/contact/
POST /api/v1/crm/leads/quote/
GET  /api/v1/crm/bookings/availability/?date=YYYY-MM-DD
POST /api/v1/crm/bookings/consultations/
POST /api/v1/crm/newsletter/subscribe/

# CRM Dashboard (JWT)
GET  /api/v1/crm/dashboard/
GET  /api/v1/crm/dashboard/requests/
GET  /api/v1/crm/dashboard/requests/{id}/
POST /api/v1/crm/dashboard/requests/{id}/message/
GET  /api/v1/crm/dashboard/bookings/
GET  /api/v1/crm/dashboard/bookings/{id}/
POST /api/v1/crm/dashboard/bookings/{id}/reschedule/
POST /api/v1/crm/dashboard/bookings/{id}/cancel/
GET  /api/v1/crm/dashboard/tickets/
POST /api/v1/crm/dashboard/tickets/
GET  /api/v1/crm/dashboard/tickets/{id}/
POST /api/v1/crm/dashboard/tickets/{id}/messages/
GET  /api/v1/crm/dashboard/calculations/
POST /api/v1/crm/dashboard/calculations/{id}/convert/

# Auth (public — no API key)
POST /api/v1/auth/register/
POST /api/v1/auth/verify-email/
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/magic-link/request/
POST /api/v1/auth/magic-link/verify/
POST /api/v1/auth/password-reset/request/
POST /api/v1/auth/password-reset/confirm/
POST /api/v1/auth/google/

# Auth Profile (JWT)
GET  /api/v1/auth/me/
PATCH /api/v1/auth/me/update/
POST /api/v1/auth/me/change-password/
GET  /api/v1/auth/sessions/
DELETE /api/v1/auth/sessions/{id}/revoke/

# Notifications (JWT)
GET  /api/v1/notifications/
GET  /api/v1/notifications/unread-count/
POST /api/v1/notifications/{id}/mark-read/
POST /api/v1/notifications/mark-all-read/
GET  /api/v1/notifications/preferences/
PUT  /api/v1/notifications/preferences/

# SEO (API key)
GET  /api/v1/seo/settings/
GET  /api/v1/seo/sitemap-urls/

# AI Assistant (API key)
POST /api/v1/assistant/chat/

# Guest CRM (API key + guest_token)
GET  /api/v1/crm/guest/requests/
GET  /api/v1/crm/guest/requests/{id}/
POST /api/v1/crm/guest/tickets/
GET  /api/v1/crm/guest/tickets/{id}/
POST /api/v1/crm/guest/tickets/{id}/messages/

# OpenAPI Schema (public)
GET  /api/schema/
GET  /api/schema/docs/
```

---

**65 endpoints, 8 API groups, 2 auth mechanisms. Fully documented with types, patterns, and best practices.**
