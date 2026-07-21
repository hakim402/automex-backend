# AUTOMEX — MVP Documentation

> Version: 2.0 | July 2026

---

## Company

**AUTOMEX** is a technology consulting and software development company that helps startups, SMEs, and enterprises build scalable digital products through modern software engineering, AI, cloud technologies, and dedicated development teams.

- **Website**: https://automex.tech
- **API**: https://api.automex.tech
- **Admin**: https://api.automex.tech/control-panel/

---

## Mission & Vision

**Mission**: Help businesses accelerate digital transformation by delivering reliable, scalable, and innovative software solutions.

**Vision**: Become a trusted global technology partner empowering organizations to innovate, automate, and grow.

---

## Target Audience

**Clients**: Startups, SMEs, Enterprises, SaaS companies, Government, Healthcare, Manufacturing, Retail, Logistics, Financial institutions.

**Decision Makers**: CEOs, CTOs, Founders, Product Managers, IT Managers, Digital Transformation Leaders.

---

## Core Value Proposition

- Modern Technology Stack (Next.js, Django, PostgreSQL, Docker)
- Agile Development Methodology
- Enterprise-grade Security & Scalable Architecture
- Experienced Engineering Team
- Transparent Communication & Long-term Support
- AI-driven Innovation via Groq-powered Assistant

---

## Services

| # | Service | Key Deliverables |
|---|---|---|
| 1 | **Custom Software Development** | Custom apps, SaaS platforms, MVP development, API development, system integration, QA, software modernization |
| 2 | **Artificial Intelligence** | AI applications, chatbots, workflow automation, ML, NLP, computer vision, AI integration |
| 3 | **Data Engineering & Analytics** | ETL pipelines, data warehousing, BI dashboards, analytics platforms, reporting systems |
| 4 | **ERP & CRM Solutions** | Odoo, Microsoft Dynamics 365 — CRM, Sales, HR, Finance, Inventory, Manufacturing |
| 5 | **Cloud & DevOps** | AWS, Azure, Docker, Kubernetes, CI/CD, infrastructure automation, monitoring |
| 6 | **UI/UX Design** | UX research, wireframes, UI design, design systems, interactive prototypes |
| 7 | **IT Staff Augmentation** | Frontend, backend, full-stack, mobile, DevOps, QA, AI engineers, UI/UX designers |

---

## Industries Served

SaaS · Healthcare · Finance · Retail · Manufacturing · Logistics · Government · Education · Real Estate · E-Commerce

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16, TypeScript, Tailwind CSS |
| **Backend** | Django 5.2, Django REST Framework, django-parler (10 languages), django-filter |
| **Database** | PostgreSQL 15 |
| **Cache / Queue** | Redis 7, Celery |
| **AI** | Groq API (GPT-OSS-120B) |
| **Email** | Gmail SMTP |
| **Infrastructure** | Docker, Docker Compose, Nginx, Hostinger VPS |
| **Admin** | Unfold (custom Django admin theme) |
| **API Docs** | drf-spectacular (OpenAPI 3.0), Swagger UI |
| **Auth** | JWT (SimpleJWT), API keys, Google OAuth, magic links |

---

## Features (MVP Complete)

### Public Website

- [x] Service pages with hero images, features, benefits, technologies, industries, FAQs
- [x] Enterprise sub-models: deliverables, add-ons, comparison tables, SLAs, client logos, documents
- [x] Case studies with gallery images, technologies, results
- [x] Blog with categories, tags, search, featured posts
- [x] Team member profiles
- [x] Client testimonials with ratings
- [x] Technology partners with tier/type filtering
- [x] Certifications & badges
- [x] AI capabilities showcase (NLP, computer vision, generative AI, etc.)
- [x] Technical expertise areas
- [x] Portfolio projects with image galleries
- [x] Multi-language support (10 languages: en, es, de, fr, it, nl, zh, ar, fa, ps)
- [x] Full SEO: per-page meta, Open Graph, Twitter cards, sitemap, robots.txt, redirects
- [x] Structured data (JSON-LD schema.org)

### Lead Generation

- [x] Contact form (captures IP, user-agent, referrer server-side)
- [x] Quote request form with budget estimation
- [x] Consultation booking with real availability validation + double-booking prevention
- [x] Newsletter subscription (idempotent)
- [x] Cost calculator with estimate-to-lead conversion
- [x] Admin notification emails on every lead

### AI Sales Assistant

- [x] Groq-powered chat endpoint
- [x] Grounded in published Services + AI knowledge base
- [x] Mid-conversation lead capture (email extraction)
- [x] Session persistence across chat turns
- [x] JSON response mode with fallback to raw text

### Client Dashboard

- [x] User registration/login (email/password, Google OAuth, magic links)
- [x] Password reset
- [x] Profile management with session tracking
- [x] Request/Lead tracking with activity timeline
- [x] Booking management (view, reschedule, cancel)
- [x] Support ticket system (create, view, reply)
- [x] Cost estimate history
- [x] Notification center (email with SMS/WhatsApp/Slack ready)
- [x] Guest tracking (non-logged-in users)

### Enterprise Backend

- [x] Multi-channel notification system (email implemented, SMS/WhatsApp/Slack scaffolded)
- [x] Encrypted credential storage for third-party providers
- [x] API key management with SHA-256 hashing
- [x] Role-based access control (RBAC) with tenant isolation
- [x] Soft delete with email reuse support
- [x] Content revision/audit logging
- [x] Full OpenAPI 3.0 schema (auto-generated)
- [x] Comprehensive test suite (236 tests, 0 regressions)

---

## Development Process

```
Discovery → Planning → UI/UX Design → Development → QA → Deployment → Maintenance
```

---

## Success Metrics

| Metric | Target |
|---|---|
| Organic traffic increase | +30% within 6 months |
| Lead conversion rate | > 3% from contact forms |
| Consultation booking rate | > 5 per week |
| Average session duration | > 2 minutes |
| Bounce rate | < 45% |
| Keyword rankings | Top 10 for 10+ target keywords |
| API uptime | 99.9% |

---

## Language Support

`en` `es` `de` `fr` `it` `nl` `zh` `ar` `fa` `ps`

RTL languages: `ar` (Arabic), `fa` (Persian), `ps` (Pashto)

All content models support per-language translations with automatic English fallback.

---

## API Overview

| Group | Endpoints | Auth |
|---|---|---|
| Public Content | 26 | API Key (server-side) |
| CRM Public (write) | 5 | API Key (proxied) |
| Auth | 14 | JWT / public |
| CRM Dashboard | 13 | JWT |
| CRM Guest | 5 | API Key + token |
| Notifications | 6 | JWT |
| SEO | 2 | API Key |
| AI Assistant | 1 | API Key |

**Total: 65 API endpoints, 8 groups, 2 auth mechanisms**

Full API reference: [NEXTJS_API_GUIDE.md](./NEXTJS_API_GUIDE.md)

---

## Future Roadmap

- [ ] Live chat widget (real-time via WebSocket)
- [ ] SMS/WhatsApp/Slack provider integration
- [ ] Client portal with project tracking
- [ ] Resource center / knowledge base
- [ ] Interactive process timeline
- [ ] Downloadable company profile / capability deck
- [ ] AI-powered content recommendations
- [ ] Advanced analytics dashboard for admin
- [ ] Webhook system for third-party integrations
- [ ] A/B testing for CTAs and landing pages

---

**© AUTOMEX — Technology Consulting · Software Development · AI Solutions · Cloud Services**
