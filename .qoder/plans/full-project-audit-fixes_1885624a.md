# AUTOMEX Backend — Full Project Audit & Cleanup Plan

## Summary
Deep analysis of all 6 apps (accounts, core, assistant, crm, notifications, content), config, and templates. No critical runtime bugs found. One real 404 bug (Unfold admin icon), several code quality/consistency issues, and one naming mismatch. The assistant app correctly supports guest users via API-key gating with optional JWT enrichment.

---

## 1. BUGS (Will Cause Runtime Issues)

### 1.1  Unfold `SITE_ICON` References Non-Existent File
[config/settings.py](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/config/settings.py#L497-L500) references `static("icon/light.png")` for `SITE_ICON`, but only `icon/icon.png` exists on disk. This causes a broken icon on the admin login page and browser tab.
- **Fix**: Point both light/dark to `static("icon/icon.png")`.

### 1.2  Unused Import in Assistant Views
[apps/assistant/api/views.py](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/assistant/api/views.py#L11) imports `get_authorization_header` but never uses it.
- **Fix**: Remove the unused import.

---

## 2. CODE QUALITY / CONSISTENCY (No Runtime Errors)

### 2.1  Duplicate `_uuid_pk()` in accounts vs `uuid_pk()` in core
- [apps/accounts/models.py](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/accounts/models.py#L22-L29) defines `_uuid_pk()` privately
- [apps/core/models/base.py](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/core/models/base.py#L23-L30) defines `uuid_pk()` publicly (exported via `__init__.py`)
- Both do exactly the same thing: return a UUIDField pk with `default=uuid.uuid4, editable=False, db_index=True`
- **Fix**: Replace all `_uuid_pk()` usage in accounts/models.py with core's `uuid_pk()`, remove the duplicate function. This is a safe drop-in replacement since the field definitions are identical.

### 2.2  5 Models Use Manual `order` Field Instead of `OrderableModel`
These models define their own `order = models.PositiveIntegerField(...)` but don't inherit `OrderableModel`:
- `Partner` — [partners.py#L47](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/content/models/partners.py#L47)
- `Certification` — [partners.py#L79](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/content/models/partners.py#L79)
- `AICapability` — [expertise.py#L60](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/content/models/expertise.py#L60)
- `TechExpertiseArea` — [expertise.py#L101](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/content/models/expertise.py#L101)
- `PortfolioProject` — [portfolio.py#L46](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/content/models/portfolio.py#L46)

`OrderableModel` provides the exact same field (`order = PositiveIntegerField(default=0, db_index=True)`) plus the `Meta.ordering = ["order"]` pattern.
- **Fix**: Add `OrderableModel` to these 5 models' MRO; remove their manual `order` field. Requires migrations.

### 2.3  `BlogCategory` Missing `is_active` Field
[BlogCategory](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/content/models/blog.py#L27-L42) has no `is_active` toggle. Its admin doesn't use `ActiveToggleAdminMixin` either. All other taxonomy/grouping models (`ServiceCategory`, `Technology`, `Industry`, `ProcessStep`, `FAQ`, `BlogAuthor`) have `is_active`.
- **Fix**: Add `is_active = BooleanField(default=True, db_index=True)` to `BlogCategory`, update admin to use `ActiveToggleAdminMixin`. Requires migration.

### 2.4  `AIMessage` Uses Manual `created_at` Instead of `TimeStampedModel`
[AIMessage](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/assistant/models.py#L65-L91) inherits only `UUIDModel` but defines `created_at` manually. This is intentional (messages are append-only, no `updated_at` needed), so **no change required** — noted for awareness only.

### 2.5  Inconsistent IP Capturing
- CRM's `_client_meta()` uses `HTTP_X_FORWARDED_FOR` (proxy-aware)
- Assistant's `_get_or_create_conversation()` uses `REMOTE_ADDR` directly (not proxy-aware)
- **Fix**: Align assistant to also check `HTTP_X_FORWARDED_FOR` first, falling back to `REMOTE_ADDR`.

---

## 3. NAMING / BRANDING

### 3.1  `SPECTACULAR_SETTINGS` Title Still Says "Infinity Backend API"
[config/settings.py#L381](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/config/settings.py#L381) — the OpenAPI schema title is a leftover from the template.
- **Fix**: Change to "AUTOMEX Backend API".

### 3.2  `SPECTACULAR_SETTINGS` Description Mentions "Infinity" (Old Project Name)
Description text references old branding.
- **Fix**: Update to describe AUTOMEX's actual API surface (CRM, Content, Assistant, etc.).

---

## 4. ASSISTANT GUEST USER CHECK  (Confirmed Working)

The assistant app **correctly supports guest users**:
- [ChatView](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/assistant/api/views.py#L31-L65) has `authentication_classes = []` — no JWT required
- `permission_classes = [HasValidAPIKey]` — API-key gated (frontend holds the key)
- `_get_optional_user()` silently extracts JWT user if present, returns `None` for guests
- [AIConversation.user](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/assistant/models.py#L26-L31) is `null=True, blank=True` — guest conversations work without a user
- `ConversationListView` / `ConversationDetailView` require `IsAuthenticated` — only logged-in users see history (correct behavior)

**No changes needed for guest chat.**

---

## 5. MODELS REVIEW — NO DUPLICATE MODELS TO REMOVE

- **`PortfolioProject` vs `CaseStudy`**: Both model "completed work" but serve different purposes. `PortfolioProject` is a lightweight visual gallery (non-translatable, no publish workflow). `CaseStudy` is a detailed client story with translations, SEO, editorial workflow. Both are valid. **No removal needed.**
- **`Tenant` model**: Exists in [accounts/models.py](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/accounts/models.py#L36-L76), has a `User.tenant` FK, used in the admin dashboard, has migrations. It's described as "reserved for future white-label" in [base.py](file:///c:/Users/Administrator/Documents/Projects/Automex/automex-backend/apps/core/models/base.py#L10). **Keep** — it's intentional scaffolding.
- **No other duplicate models found.** Every model serves a distinct purpose.

---

## 6. IMPLEMENTATION PLAN (Ordered by Priority)

### Phase A — Quick Fixes (No Migrations)
1. Fix `SITE_ICON` in settings — change `icon/light.png` → `icon/icon.png`
2. Remove unused `get_authorization_header` import in views.py
3. Fix `SPECTACULAR_SETTINGS` title/description

### Phase B — Consistency Improvements (Requires Migrations)
4. Replace `_uuid_pk()` in accounts with core's `uuid_pk()`
5. Add `OrderableModel` to Partner, Certification, AICapability, TechExpertiseArea, PortfolioProject
6. Add `is_active` to BlogCategory + wire into admin
7. Align IP capturing in assistant with CRM's proxy-aware approach

### Phase C — Verification
8. Run all tests: `docker compose exec web pytest apps/`
9. Run `docker compose exec web python manage.py makemigrations --check` to verify migration consistency
10. Build and verify admin renders without 404s

---

## 7. TEST PLAN
- `pytest apps/assistant/tests/` — 30 tests, should all pass after changes
- `pytest apps/content/tests/` — model tests for the 5 models with new `OrderableModel`
- `pytest apps/crm/tests/` — verify lead capture still works with IP fix
- `pytest apps/accounts/tests/` — verify `uuid_pk()` replacement doesn't break anything
- Manual: Open admin panel, verify favicon loads correctly