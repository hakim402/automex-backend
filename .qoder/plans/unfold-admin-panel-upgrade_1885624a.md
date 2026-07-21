# Unfold Admin Panel — Full Upgrade Plan

## Phase A — Register All Unregistered Models (12 models)

These models exist in the codebase but have **zero** admin visibility — staff can't see or manage them at all.

### A1. APIKey (apps/core)
- Model: `apps.core.models.APIKey` — UUID, name, key prefix, hashed_key, scopes, is_active, expires_at, last_used_at, created_by, created_at
- Register with `ActiveToggleAdminMixin`, `readonly_fields` for key/hash/timestamps
- Show key prefix + masked display, scopes as JSON
- Fieldsets: Identity / Scopes / Lifecycle

### A2–A10. Service Enterprise Sub-Models (apps/content) — Register Standalone + Wire as Inlines
These 9 models are **registered standalone** (so they appear in sidebar) AND **added as inlines** inside `ServiceAdmin`:

| # | Model | Inline type in ServiceAdmin |
|---|-------|---------------------------|
| A2 | `ServiceHeroImage` | TabularInline (image, caption, is_cover, order) |
| A3 | `ServiceProcessStep` | TabularInline (process_step, custom_title, custom_description, order) |
| A4 | `ServiceDeliverable` | TabularInline (title, description, icon, order) |
| A5 | `ServiceAddOn` | TabularInline (name, description, price, is_included_in_enterprise, order) |
| A6 | `ServiceComparisonRow` | TabularInline (feature_name, standard/premium/enterprise values, is_highlighted, order) |
| A7 | `ServiceClientLogo` | TabularInline (logo, client_name, client_url, order) |
| A8 | `ServiceTestimonial` | TabularInline (testimonial, is_featured, order) |
| A9 | `ServiceDocument` | TabularInline (title, file, document_type, is_public, order) |
| A10 | `ServiceSLA` | TabularInline (guarantee_name, value, description, icon, order) |

Each standalone admin uses `ActiveToggleAdminMixin` (or appropriate mixin) with `autocomplete_fields`, `readonly_fields=["id"]`, and proper `list_display`.

### A11. LeadActivity — Standalone Registration (apps/crm)
- Already an inline in LeadAdmin; also register standalone for global timeline view
- `list_display`: lead, activity_type, description, performed_by, is_customer_visible, created_at
- `list_filter`: activity_type, created_at range
- `search_fields`: description, message
- `autocomplete_fields`: lead, performed_by, attachment
- `readonly_fields`: id, created_at

### A12. NotificationDeliveryAttempt — Standalone Registration (apps/notifications)
- Already an inline in NotificationAdmin; also register standalone
- `list_display`: notification, attempt_number, provider_name, status, response_code, duration_ms, attempted_at
- `list_filter`: status, provider_name
- `readonly`: all fields (logs should never be edited)
- `has_add_permission = False`

---

## Phase B — Populate Sidebar with All Missing Entries (17 items)

The sidebar in `settings_unfold_additions.py` is missing these models. Add them into appropriate groups:

### B1. New Group: "Integrations & API"
| Icon | Model |
|------|-------|
| `vpn_key` | API Keys |
| `settings_input_component` | Third-Party Integrations |

### B2. Add to "Website Content"
| Icon | Model |
|------|-------|
| `photo_library` | Portfolio Projects |
| `person_book` | Blog Authors |
| `psychology` | AI Capabilities |
| `code_blocks` | Tech Expertise |
| `handshake` | Partners |
| `verified` | Certifications |

### B3. Add to "Sales & CRM"
| Icon | Model |
|------|-------|
| `support_agent` | Support Tickets |
| `timeline` | Lead Activities |

### B4. Add to "Notifications"
| Icon | Model |
|------|-------|
| `receipt_long` | Delivery Attempts |

### B5. Service Sub-Models — New Group: "Service Detail Pages"
| Icon | Model |
|------|-------|
| `collections` | Service Hero Images |
| `account_tree` | Service Process Steps |
| `inventory` | Service Deliverables |
| `add_shopping_cart` | Service Add-Ons |
| `compare` | Service Comparison Rows |
| `apartment` | Service Client Logos |
| `rate_review` | Service Testimonials |
| `description` | Service Documents |
| `verified_user` | Service SLAs |

---

## Phase C — Enhanced Dashboard (KPI Cards + Charts)

`apps/accounts/dashboard.py` currently only shows accounts metrics. Expand to cover the entire business:

### C1. New KPI Cards (add to existing 5 → total 12)
- "Total Leads" — total leads, with "X open" footer
- "Pending Bookings" — consultation bookings pending confirmation
- "Open Tickets" — support tickets not resolved/closed
- "Published Services" — content services with status=published
- "Published Blog Posts" — blog posts published
- "Active Conversations" — AI conversations currently active
- "Notifications Today" — notifications created in last 24h

### C2. New Charts
- Leads by status (bar chart) — replaces static text
- Leads by source channel (doughnut chart) — attribution insight

---

## Phase D — Add Help Text to ALL Admin Fields

Audit every admin `fieldsets` across all 6 apps and add inline `"description"` keys explaining what each field does from the admin's perspective. Priority order:

1. **CRM Lead fields** — UTM fields, score, priority, tags — explain their purpose
2. **Booking fields** — calendar provider, meeting link, slot selection
3. **Notification fields** — channel routing, template selection, delivery tracking
4. **Content fields** — SEO stack, publishing workflow, translations
5. **Accounts fields** — security fields, Google OAuth, RBAC
6. **Core fields** — media metadata, redirect rules, SEO settings

This is primarily adding `"description"` strings to fieldset tuples and `help_text` on individual fields where admin confusion is likely.

---

## Phase E — Polish Unfold UX Features

### E1. Add `warn_unsaved_form = True` to ALL ModelAdmins
Currently only on TenantAdmin and UserAdmin and ServiceAdmin. Add to every single admin class that's a change form (not read-only — skip ContentRevision, CalculatorSubmission, token admins, etc.).

### E2. Add `compressed_fields = True` to forms with 6+ visible fields
Currently only on a few admins. Add to BookingAdmin, TicketAdmin, NotificationAdmin, CaseStudyAdmin, Service-related admins.

### E3. Add `list_filter_submit = True` to all admins with list_filter
Already present on ~60% of admins. Fill in the remaining ~40%.

### E4. Fill in missing `autocomplete_fields`
Several FK/M2M fields that would benefit from autocomplete (especially for `user`, `lead`, `service` lookups):
- TeamMemberAdmin: add `projects_showcase` to filter_horizontal/autocomplete
- TestimonialAdmin: add `client_industry` to autocomplete_fields
- Several service sub-model admins

### E5. Fill in empty `static/css/custom.css`
Add minor Unfold tweaks:
- Tighter KPI card spacing on dashboard
- Better responsive column widths for tabular inlines
- Subtle table-row hover highlight

---

## Phase F — Verification

- `docker compose build web && docker compose up -d web`
- `docker compose exec web python manage.py check --deploy`
- Verify all 6 admin sections render without errors
- Verify sidebar navigation shows all new entries
- Verify dashboard renders all 12 KPI cards + 4 charts
- Verify each new model admin: create, edit, list, filter, search, bulk actions
- Verify service change form shows all 9 inlines in tabs
