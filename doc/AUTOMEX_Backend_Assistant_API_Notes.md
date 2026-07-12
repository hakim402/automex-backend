# AUTOMEX Backend — AI Sales Assistant Build Notes

## What was built
A single chat endpoint backed by Groq (OpenAI-compatible API), grounded in
your real published Services + curated `AIKnowledgeEntry` rows, that
captures leads mid-conversation without interrupting the chat — per the
design agreed back when we scoped `apps.crm`.

### Important: Groq model deprecation
Checked current Groq docs before building — **`llama-3.3-70b-versatile`
and `llama-3.1-8b-instant` are deprecated.** Default model is now
`openai/gpt-oss-120b` (current flagship). Swap anytime via `GROQ_MODEL` in
`.env` — no code change needed. `openai/gpt-oss-20b` is the
smaller/faster/cheaper alternative if cost matters more than quality.

### `apps.assistant`
- **`providers.py`** — `AIProvider` interface + `GroqProvider`
  implementation. Nothing else in the app talks to Groq directly, so
  swapping providers later doesn't touch business logic. Every failure
  mode (missing API key, timeout, connection error, malformed response,
  HTTP error) raises a single `AIProviderError` that callers handle
  uniformly.
- **`prompts.py`** — builds the system prompt fresh per request from
  published Services + active `AIKnowledgeEntry` rows (lightweight RAG —
  no vector search needed at this content scale). Instructs the model to
  always respond in JSON matching a fixed schema.
- **`extraction.py`** — deterministic regex email/phone detection. This is
  what actually **triggers** lead capture (per your decision) — reliable
  and testable, unlike depending on the LLM to reliably self-report intent.
- **`services.py`** — `handle_chat_message()`: the whole orchestration.
  Persists both sides of the conversation, calls the provider with capped
  history (`AI_ASSISTANT_MAX_HISTORY_MESSAGES`, default 20 — controls
  token cost), parses the JSON reply (falls back to raw text if the model
  ignores the format instruction — never crashes the conversation), and
  captures a lead **once per conversation** the moment a real email shows
  up in the visitor's own message. The LLM's structured output enriches
  that lead (name, company, matched service) but never gates the decision.
- **API**: one endpoint, `POST /api/v1/assistant/chat/` — same `X-API-Key`
  posture as content/crm, own throttle scope (`ai_assistant`, 20/min —
  LLM calls are expensive, throttled tighter than plain writes).

### Response style: plain request/response (per your decision)
No streaming in this phase — the client sends a message, waits, gets the
full reply. Streaming (SSE) would need a different view base (DRF doesn't
do it natively) — worth a dedicated pass later if you want the
typed-out-live feel.

### Architecture note: keep this behind your Next.js backend, not the browser
The chat widget is inherently browser-facing, but `X-API-Key` must stay
server-side. Route: **browser → your Next.js API route → this Django
endpoint** (same pattern as your other server-side fetches), not
browser → Django directly. Documented in the Next.js guide addendum below.

---

## Endpoint

```
POST /api/v1/assistant/chat/
Headers: X-API-Key: <key>
Body: { "message": "...", "session_id"?: "...", "language"?: "en", "page_url"?: "..." }

→ 200 { "session_id": "...", "reply": "...", "lead_captured": true|false }
```

- Omit `session_id` on the first message — the response returns one;
  persist it (e.g. in the browser's `sessionStorage`, passed through your
  Next.js proxy) and send it on every subsequent message in the same chat.
- `lead_captured` reflects the conversation's cumulative state (`true` once
  captured, stays `true` for the rest of that conversation) — not just
  "captured this specific turn."

---

## Settings added
```python
GROQ_API_KEY                      = env("GROQ_API_KEY", default="")
GROQ_API_BASE_URL                 = env("GROQ_API_BASE_URL", default="https://api.groq.com/openai/v1")
GROQ_MODEL                        = env("GROQ_MODEL", default="openai/gpt-oss-120b")
GROQ_REQUEST_TIMEOUT_SECONDS       = env.int("GROQ_REQUEST_TIMEOUT_SECONDS", default=20)
AI_ASSISTANT_MAX_HISTORY_MESSAGES = env.int("AI_ASSISTANT_MAX_HISTORY_MESSAGES", default=20)

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai_assistant"] = "20/minute"
```
```python
# config/urls.py
path("api/v1/assistant/", include("apps.assistant.api.urls", namespace="assistant")),
```

**Add to your `.env`** — the app works without this (returns a graceful
fallback reply instead of crashing), but obviously won't produce real
responses until it's set:
```
GROQ_API_KEY=gsk_your_real_key_here
```
Get one at https://console.groq.com.

## No new packages, no new migrations
Used `requests` (already in `requirements.txt`). All models
(`AIConversation`, `AIMessage`, `AIKnowledgeEntry`) were already migrated
in an earlier round.

## Before this is useful in production
`AIKnowledgeEntry` is empty until you add rows in the admin
(`/admin/assistant/aiknowledgeentry/add/`) — FAQ-style Q&A pairs (pricing
questions, process questions, "do you sign NDAs" etc.) that get injected
into every conversation's context. Without any, the assistant only knows
about your published Services (name + short description) — functional,
but shallow.

## Tests — 182 passing (152 previous + 30 new)
```bash
docker compose exec web bash -c "DJANGO_SETTINGS_MODULE=config.settings_test pytest apps/assistant -v"
```
**None of these tests touch the real Groq API** — that's intentional and
standard practice (never hit a real third-party API in a unit test suite:
slow, costly, flaky, and requires a real key just to run CI). Instead:
- `test_providers.py` mocks `requests.post` directly to verify `GroqProvider`
  builds the right payload/headers and correctly wraps every failure mode
  (timeout, connection error, HTTP error, malformed response) as
  `AIProviderError`.
- `test_services.py` / `test_api.py` inject a `FakeAIProvider` (implements
  the same interface) via dependency injection — verifies the actual
  business logic (conversation persistence, lead capture triggering,
  fallback behavior) without needing any network access at all.

If you want a genuine end-to-end confirmation that Groq itself works, that
has to be a manual check against a real `GROQ_API_KEY` in a real
environment — not something that belongs in the automated suite.

## Next steps
This closes out the three MVP-critical API layers (content, crm,
assistant). Remaining from the earlier options list: real SMS/WhatsApp/
Slack provider wiring, spam-protection hardening, SEO extras
(sitemap.xml/robots.txt), or production/deployment hardening. Your call
on what's next.
