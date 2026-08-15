---
id: SPEC-garmin-ha-ai
companions:
  - ../planning-artifacts/ux-designs/ux-garmin-ha-ai-2026-08-15/DESIGN.md
  - ../planning-artifacts/ux-designs/ux-garmin-ha-ai-2026-08-15/EXPERIENCE.md
  - ../planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/ARCHITECTURE-SPINE.md
  - ../planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/solution-design-garmin-ha-ai-2026-08-15.md
sources:
  - ../planning-artifacts/prds/prd-garmin-ha-ai-2026-08-14/prd.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# SPEC — Garmin Home Assistant AI Integration (`garmin-ha-ai`)

## Why

Fitness enthusiasts and athletes tracking metrics on Garmin Connect lack privacy-first, automated AI health coaching integrated into their smart homes. Commercial fitness apps lock personalized advice behind expensive monthly subscriptions and cloud silos. `garmin-ha-ai` solves this pain and captures an opportunity by fetching daily Garmin statistics (sleep, stress, HRV, body battery, workouts) directly into Home Assistant and leveraging user-controlled LLM APIs (Google Gemini or local/generic OpenAI endpoints) to deliver contextual morning briefings, recovery guidance, and interactive Q&A without subscription fees or data lock-in.

## Capabilities

- **CAP-1**
  - **intent:** User can authenticate Garmin Connect credentials via UI Config Flow (with MFA PIN verification step and explicit timeout recovery) so that Home Assistant securely obtains and persists OAuth tokens in local storage without keeping raw passwords.
  - **success:** Config Flow completes `step_mfa` (with retry/resend options on timeout), saves tokens to `.storage/garmin_ha_ai_tokens.json`, silently refreshes expired tokens, or triggers `async_step_reauth` on revoked sessions.

- **CAP-2**
  - **intent:** Integration automatically extracts daily fitness and health metrics from Garmin Connect for a specified date (aligned to `hass.config.time_zone`) so that health statistics are normalized for LLM prompt assembly and entity updates.
  - **success:** Ingests steps, distance, calories, resting HR, average stress, sleep score, body battery min/max, HRV status, weight, and all logged activities into a structured `GarminDailyMetrics` object with nullable metric fields handling unworn watch days.

- **CAP-3**
  - **intent:** User can set and modify background sync schedules via Options Flow so that metric extraction and AI report generation occur automatically at specified times or intervals.
  - **success:** Scheduled timer triggers coordinator sync at the exact configured schedule (default 06:00 AM), and calling `garmin_ha_ai.generate_report` executes an immediate debounced manual refresh (`_is_generating` guard).

- **CAP-4**
  - **intent:** System sends structured prompt payloads combining current metrics, 7-day trend history, user goals, and directives to the active AI provider (Google Gemini or OpenAI-compatible endpoint with configurable timeout) so that personal health summaries and workout advice are generated.
  - **success:** Valid API key returns a structured `AIHealthReport` containing both a concise 1-2 sentence dashboard summary and a full Markdown report, protected by context truncation guards.

- **CAP-5**
  - **intent:** System stores daily metric snapshots locally in Home Assistant `.storage/garmin_ha_ai_history.json` with a user-configurable retention window (default 30 days) and `asyncio.Lock()` protection so that historical trend context is available offline without hitting Garmin cloud rate limits or risking JSON write corruption.
  - **success:** Snapshots up to N days are preserved locally, handles clean-install missing storage gracefully, and enables instant clamped context assembly during AI queries.

- **CAP-6**
  - **intent:** Integration registers native Home Assistant sensor entities for individual Garmin metrics, AI report summaries, and last sync timestamps so that health data can be rendered on Lovelace dashboards and used in automations.
  - **success:** Numeric sensors (`sensor.garmin_steps`, `sensor.garmin_sleep_score`, etc.) render valid states, `sensor.garmin_ai_health_report_short` state is truncated to <255 chars (`short_summary[:250] + "..."`), and `sensor.garmin_ai_health_report_long` stores the full Markdown report in `extra_state_attributes["full_report"]`.

- **CAP-7**
  - **intent:** Integration dispatches generated AI health reports to configured Home Assistant notification targets so that morning briefings arrive via push notifications or email.
  - **success:** Report generation executes a call to configured `notify` services with short and long report payloads, catching `ServiceNotFound`/`HomeAssistantError` to protect sync pipeline continuity.

- **CAP-8**
  - **intent:** User can submit custom health or workout questions via service `garmin_ha_ai.ask_question` with automatic 7-day metric grounding so that personalized AI answers are returned directly in service response data and updated on `sensor.garmin_ai_last_answer` or an optional `response_entity`.
  - **success:** Service call accepts `question`, `days_history` (clamped to available history), and optional `response_entity`, returns `{"answer": "...", "question": "..."}` as direct service response data (`SupportsResponse.OPTIONAL`), and updates entities within <10 seconds.

- **CAP-9**
  - **intent:** User can configure credentials, AI provider options, API keys, fitness goals, focus directives, and notification targets through Home Assistant UI forms without editing YAML configuration files.
  - **success:** Config Flow completes initial setup; Options Flow updates runtime parameters dynamically post-installation.

- **CAP-10**
  - **intent:** Developer can package all integration code under `custom_components/garmin_ha_ai/` with a valid `manifest.json` so that the custom component installs cleanly via HACS or manual copy.
  - **success:** Home Assistant Core loads `garmin_ha_ai` cleanly with all declared PyPI dependencies (`garminconnect`, `google-genai`, `httpx`).

## Constraints

- MUST be packaged exclusively as a Home Assistant custom component located under `custom_components/garmin_ha_ai/`.
- MUST use `python-garminconnect` for cloud ingestion and store OAuth tokens in `.storage/garmin_ha_ai_tokens.json`. Plaintext credentials MUST NOT be retained in persistent storage.
- MUST support Google Gemini API via `google-genai` SDK and generic OpenAI-compatible `/v1/chat/completions` API via `httpx` async client with configurable HTTP request timeout (default 30s).
- MUST protect entity state strings from exceeding Home Assistant's 255-character hard limit by truncating short summary states (`short_summary[:250] + "..."`) and placing full rich Markdown reports in `extra_state_attributes["full_report"]`.
- Service `garmin_ha_ai.ask_question` MUST use `supports_response=SupportsResponse.OPTIONAL`, clamp `days_history` to available history, and pull historical metrics from local `.storage` cache protected by `asyncio.Lock()` to prevent Garmin API rate limiting and store file corruption.

## Non-goals

- Direct Bluetooth/ANT+ pairing with Garmin hardware (all data ingestion occurs via Garmin Connect cloud APIs).
- Providing medical diagnosis, treatment plans, or clinical advice (the component provides wellness/fitness coaching only).
- Multi-user Garmin account profile switching per single integration entry in v1.

## Success signal

User completes UI setup in under 3 minutes, wakes up to an automated daily morning health briefing card and push notification on their phone with sleep/HRV recovery advice, and gets answers to interactive questions ("Should I do heavy squats today?") grounded in their Garmin metrics within <10 seconds.

