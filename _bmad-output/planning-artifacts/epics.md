---
stepsCompleted:
  - "step-01-validate-prerequisites"
  - "step-02-design-epics"
  - "step-03-create-stories"
  - "step-04-final-validation"
inputDocuments:
  - "_bmad-output/planning-artifacts/prds/prd-garmin-ha-ai-2026-08-14/prd.md"
  - "_bmad-output/planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/ARCHITECTURE-SPINE.md"
  - "_bmad-output/planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/solution-design-garmin-ha-ai-2026-08-15.md"
  - "_bmad-output/specs/spec-garmin-ha-ai/SPEC.md"
  - "_bmad-output/planning-artifacts/ux-designs/ux-garmin-ha-ai-2026-08-15/DESIGN.md"
  - "_bmad-output/planning-artifacts/ux-designs/ux-garmin-ha-ai-2026-08-15/EXPERIENCE.md"
---

# garmin-ha-ai - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for garmin-ha-ai, decomposing the requirements from the PRD, UX Design specification, and Architecture documents into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR-1: Credential & Token Authentication — System MUST authenticate with Garmin Connect via email/password and support MFA callback prompts. DI OAuth tokens MUST be saved locally to Home Assistant `.storage` (`.storage/garmin_ha_ai_tokens.json`) to maintain persistent login sessions without storing plaintext passwords in memory. Expired tokens MUST trigger automatic silent refresh using stored refresh tokens.
- FR-2: Metric Extraction — System MUST extract daily health metrics for the target date: steps, total distance, total calories, resting heart rate, average stress score, sleep score, HRV status, body battery min/max, weight (kg), and logged workout activities.
- FR-3: Flexible Polling Schedule — System MUST support configurable polling schedules: daily at specified time (default 06:00 AM), periodic interval (e.g. 6/12/24 hours), weekly, monthly, or manually triggered via service call.
- FR-4: Offline / Rate-Limit Resilience — System MUST handle network failures or Garmin API rate limits gracefully by caching the latest successfully fetched metrics and logging warnings without crashing Home Assistant.
- FR-5: Primary Provider (Google Gemini) — System MUST support Google Gemini API (using official `google-genai` SDK) configured with an API key (default model: `gemini-2.0-flash`).
- FR-6: Configurable Generic LLM Provider — System MUST support any OpenAI-compatible API endpoint via `httpx` async client by allowing custom Base URL (e.g. `http://localhost:11434/v1` or `https://api.openai.com/v1`), API key, and Model ID.
- FR-7: Prompt Context Assembly — System MUST assemble prompt payloads containing: (1) Current day metrics, (2) 7-day metric history/trends from local store, (3) User goals (fitness targets, weight goal), (4) Persona directives, and (5) Specific instructions for output structure (short summary vs deep report).
- FR-8: Response Error Handling & Retry — System MUST handle AI API timeouts or quota errors with up to 2 retries (exponential backoff) before marking report state with an error indicator.
- FR-9: Garmin Metrics Sensors — System MUST create Home Assistant sensor entities for key Garmin metrics: `sensor.garmin_steps`, `sensor.garmin_resting_hr`, `sensor.garmin_sleep_score`, `sensor.garmin_stress_level`, `sensor.garmin_weight`, `sensor.garmin_body_battery`.
- FR-10: AI Report Sensor Entities — System MUST create `sensor.garmin_ai_health_report_short` (concise dashboard text strictly truncated to <255 chars in Python) and `sensor.garmin_ai_health_report_long` (full markdown report stored in `extra_state_attributes["full_report"]`).
- FR-11: Integration Status & Last Sync Sensor — System MUST maintain `sensor.garmin_ai_last_update` showing timestamp of last successful Garmin sync and AI report generation.
- FR-12: Multi-Channel Fault-Tolerant Dispatch — System MUST support dispatching generated reports to configured Home Assistant notification targets (e.g. `notify.mobile_app_phone`, persistent notification, email). Notification failures (`ServiceNotFound` or `HomeAssistantError`) MUST be caught as logged warnings without breaking entity state updates.
- FR-13: Manual Report Trigger Service & Debouncing — System MUST expose service `garmin_ha_ai.generate_report` to allow manual execution from Lovelace buttons, automations, or scripts, protected by an in-flight debouncing lock `_is_generating`.
- FR-14: Service `garmin_ha_ai.ask_question` — System MUST register service `garmin_ha_ai.ask_question` accepting `question` (required), `days_history` (default 7), and optional `response_entity`. It MUST return response data directly (`SupportsResponse.OPTIONAL`) and update `sensor.garmin_ai_last_answer` (or `response_entity`).
- FR-15: History Injection into Q&A Prompt — System MUST automatically fetch past N days of cached Garmin metrics from local store (guarded by `asyncio.Lock()`) and append them to system prompt before invoking LLM.
- FR-16: UI Config Flow Setup & MFA Timeout Recovery — System MUST provide UI Config Flow (`config_flow.py`) for initial setup: Garmin Credentials (email, password, MFA code), AI Provider Selection (Gemini vs Custom OpenAI), API Key, and Initial Goals. If MFA times out or fails, explicit retry/resend options MUST be provided.
- FR-17: UI Options Flow Updates — System MUST provide UI Options Flow (`options_flow.py`) to allow updating goals, AI focus directives, sync schedules, retention window, and notification targets post-installation without re-entering credentials.
- FR-18: Custom Component Package & Manifest — System MUST package all code under `custom_components/garmin_ha_ai/` with valid `manifest.json` (`domain: garmin_ha_ai`, version, dependencies `garminconnect>=0.3.10`, `google-genai>=1.0.0`, `httpx>=0.27.0`).

### NonFunctional Requirements

- NFR-1: Sync Success Rate (SM-1) — System MUST achieve >= 98% successful daily Garmin data syncs without session dropouts.
- NFR-2: Report Generation Latency (SM-2) — Daily AI report MUST be generated and updated within < 15 seconds of scheduled time.
- NFR-3: Interactive Q&A Response Time (SM-3) — Service `garmin_ha_ai.ask_question` MUST return a grounded response within < 10 seconds.
- NFR-4: Deployment Ease (SM-4) — Integration setup MUST be completed via Home Assistant UI Config Flow in under 3 minutes.
- NFR-5: API Rate Limit Protection (SM-C1) — System MUST NOT over-poll Garmin API or LLM APIs (maximum 1 scheduled sync per interval unless manually triggered).
- NFR-6: Privacy & Data Locality — Credentials, tokens, and 30-day metric history MUST be stored exclusively on local Home Assistant storage (`.storage/`). No third-party cloud relay servers allowed. Logs MUST be sanitized to never record Garmin credentials, MFA PINs, or raw user health payloads.
- NFR-7: Main Loop Non-Blocking — System MUST never perform blocking synchronous network or I/O calls in the Home Assistant main event loop; all external calls MUST use async execution or HA executor wrappers.

### Additional Requirements

- ARCH-1: Layered Adapter Architecture — Package structure organized under `custom_components/garmin_ha_ai/` (`__init__.py`, `config_flow.py`, `options_flow.py`, `coordinator.py`, `garmin_client.py`, `storage.py`, `sensor.py`, `services.py`, `const.py`, `ai_engine/`).
- ARCH-2: Starter Structure — Custom component initialized from scratch under `custom_components/garmin_ha_ai/` targeting Home Assistant Core 2024.1+ standards.
- ARCH-3: Local Storage & Concurrency (AD-2) — Local JSON snapshot store (`.storage/garmin_ha_ai_history.json`) guarded by `asyncio.Lock()` with user-configurable retention window (default 30 days, configurable 7-90 days via Options Flow). Missing history files on clean install handled gracefully.
- ARCH-4: Dual Native Driver AI Engine (AD-3) — Pluggable AI engine package using `google-genai` SDK for Gemini and `httpx` async client for OpenAI-compatible `/v1/chat/completions` (30s timeout). Context prompt truncation logic in `prompt.py`.
- ARCH-5: Reauth Flow & Token Lifecycle (AD-4) — Automatic token refresh; raise `ConfigEntryAuthFailed` on token invalidation to trigger native HA re-authentication UI flow (`async_step_reauth`).
- ARCH-6: Entity State Protection (AD-5) — Strict Python truncation (`[:250] + "..."`) for `sensor.garmin_ai_health_report_short` to avoid HA 255-char `InvalidStateError`. Store full markdown in `extra_state_attributes["full_report"]` for `sensor.garmin_ai_health_report_long`.
- ARCH-7: Service Response Data & Clamping (AD-6) — Service `garmin_ha_ai.ask_question` registered with `supports_response=SupportsResponse.OPTIONAL`, clamping `days_history` to `min(requested_days, available_stored_days)`.
- ARCH-8: Debouncing & Fault Isolation (AD-7) — In-flight report debouncing lock `_is_generating`. Notification dispatch catching `ServiceNotFound` and `HomeAssistantError` with warning log.

### UX Design Requirements

- UX-DR-1: Visual Identity & Color System — Implement Theme-aware styling using CSS variables (`var(--ha-card-background)`, `var(--primary-text-color)`) and status color coding (`colors.status.optimal`: Emerald `#10B981`, `colors.status.moderate`: Amber `#F59E0B`, `colors.status.rest`: Coral `#EF4444`, `colors.status.ai_accent`: Indigo `#8B5CF6`).
- UX-DR-2: Small View Dashboard Pattern (Status Badges) — Support 2-3 glanceable status badges for Lovelace headers (Recovery & HRV badge `mdi:heart-pulse`, Sleep & Body Battery badge `mdi:battery-charging-80`, Goal Track badge `mdi:target`).
- UX-DR-3: Medium View Dashboard Pattern (Brief Recommendation Card) — Support glanceable card layout with title `🤖 AI Health Coach` displaying 2-3 lines of daily workout/recovery recommendation text from `sensor.garmin_ai_health_report_short`.
- UX-DR-4: Large View Dashboard Pattern (Full Markdown Health Report) — Support full-width/deep report card displaying rich Markdown from `sensor.garmin_ai_health_report_long` (`extra_state_attributes["full_report"]`) with H2 headers, bullet lists, 3-day workout outlook, and refresh button.
- UX-DR-5: Interactive Q&A Card Pattern — Support UI card pattern featuring text input box (`paper-input`) + "Ask Coach" submit button triggering `garmin_ha_ai.ask_question` and displaying latest answer from `sensor.garmin_ai_last_answer`.
- UX-DR-6: State Indicators & MFA Countdown Pattern — Config Flow & Options Flow UI must provide clear state feedback (MFA code prompt with 120s countdown, data sync spinners `mdi:loading`, AI generation indicator, Garmin auth error banner, rate limit warning banner).
- UX-DR-7: Accessibility & Contrast Floor — All status badges must include full text `aria-label` descriptions for screen readers, keyboard navigation support (Tab/Enter in forms), and >= 4.5:1 text color contrast.

### FR Coverage Map

- FR-1: Epic 1 - Credential & Token Authentication with MFA support and local `.storage` token persistence.
- FR-2: Epic 1 - Metric extraction (steps, RHR, stress, sleep score, HRV, body battery min/max, weight, workouts).
- FR-3: Epic 1 - Flexible polling schedule configuration (daily default 06:00 AM, interval, manual).
- FR-4: Epic 1 - Offline & rate-limit resilience with metric caching.
- FR-5: Epic 2 - Primary AI Provider integration using official `google-genai` SDK (Gemini 2.0 Flash).
- FR-6: Epic 2 - Configurable Generic OpenAI-compatible API endpoint via `httpx` async client.
- FR-7: Epic 2 - 5-Block prompt context assembly (current metrics, 7-day history, goals, directives, structure).
- FR-8: Epic 2 - AI API response error handling & exponential backoff retries.
- FR-9: Epic 1 - Native Garmin health metric sensor entities (`sensor.garmin_steps`, etc.).
- FR-10: Epic 2 - AI Report sensor entities (`sensor.garmin_ai_health_report_short` and `sensor.garmin_ai_health_report_long`).
- FR-11: Epic 2 - Integration status & last update sensor (`sensor.garmin_ai_last_update`).
- FR-12: Epic 2 - Multi-channel fault-tolerant notification dispatch (push, persistent, email).
- FR-13: Epic 2 - Manual report generation trigger service (`garmin_ha_ai.generate_report`) & debouncing.
- FR-14: Epic 3 - Interactive Q&A service (`garmin_ha_ai.ask_question`) with `SupportsResponse.OPTIONAL`.
- FR-15: Epic 3 - Historical data context injection into Q&A prompt from local store.
- FR-16: Epic 1 - UI Config Flow setup wizard (`config_flow.py`) with 120s MFA callback countdown.
- FR-17: Epic 3 - UI Options Flow settings update (`options_flow.py`) for goals, directives, and retention.
- FR-18: Epic 1 - HACS Custom Component packaging & manifest (`custom_components/garmin_ha_ai/manifest.json`).

## Epic List

### Epic 1: Integration Setup, Garmin Auth & Health Metric Ingestion Foundation
User can configure the `garmin-ha-ai` integration via Home Assistant UI Config Flow (Garmin credentials, 120s MFA callback, AI provider selection, and initial goals), authenticate securely with Garmin Connect, persist OAuth tokens and daily metric history snapshots locally in `.storage/` via `storage.py` guarded by `asyncio.Lock()`, handle auth failures gracefully via `ConfigEntryAuthFailed` and native `async_step_reauth`, and fetch daily health metrics onto native Home Assistant sensor entities (`sensor.garmin_steps`, `sensor.garmin_sleep_score`, etc.) with rate-limit and offline resilience.
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-9, FR-16, FR-18

### Epic 2: Automated AI Coaching Reports & Multi-Channel Delivery
User receives daily scheduled and manually triggered AI health briefings (via Google Gemini `google-genai` SDK or generic OpenAI `httpx` async client) grounded in daily metrics, accumulated 7-day history, personal goals, and coaching directives. Reports populate native HA report sensors (`sensor.garmin_ai_health_report_short` strictly truncated to <255 chars in Python to prevent `InvalidStateError`, `sensor.garmin_ai_health_report_long` with full markdown in extra state attributes) and dispatch to configured notification channels (push, persistent, email) catching `ServiceNotFound`/`HomeAssistantError` with debouncing (`_is_generating`) and fault isolation.
**FRs covered:** FR-5, FR-6, FR-7, FR-8, FR-10, FR-11, FR-12, FR-13

### Epic 3: Interactive Health Q&A & Local History Management
User can ask context-grounded health and workout questions on demand via service `garmin_ha_ai.ask_question` (with `SupportsResponse.OPTIONAL` direct response data and update to `sensor.garmin_ai_last_answer`) or interactive Lovelace Q&A cards. Question answering queries local 30-day historical JSON store (`.storage/garmin_ha_ai_history.json` guarded by `asyncio.Lock()` with graceful fallback on missing files) to ground queries without hitting Garmin cloud APIs. Also supports dynamic Options Flow updates (`options_flow.py`) for goals, directives, schedule, and retention window post-installation.
**FRs covered:** FR-14, FR-15, FR-17


## Epic 1: Integration Setup, Garmin Auth & Health Metric Ingestion Foundation

User can configure the `garmin-ha-ai` integration via Home Assistant UI Config Flow (Garmin credentials, 120s MFA callback, AI provider selection, and initial goals), authenticate securely with Garmin Connect, persist OAuth tokens and daily metric history snapshots locally in `.storage/` via `storage.py` guarded by `asyncio.Lock()`, handle auth failures gracefully via `ConfigEntryAuthFailed` and native `async_step_reauth`, and fetch daily health metrics onto native Home Assistant sensor entities (`sensor.garmin_steps`, `sensor.garmin_sleep_score`, etc.) with rate-limit and offline resilience.

### Story 1.1: Custom Component Package Scaffolding & Manifest Setup

As a Home Assistant user,
I want the basic custom component directory structure, domain constants, and valid `manifest.json` under `custom_components/garmin_ha_ai/`,
So that Home Assistant Core recognizes the integration and automatically installs its required PyPI dependencies (`garminconnect`, `google-genai`, `httpx`).

**Acceptance Criteria:**

**Given** a standard Home Assistant Core installation
**When** the component package is placed under `custom_components/garmin_ha_ai/`
**Then** Home Assistant loads `manifest.json` with `domain: garmin_ha_ai`, version `1.0.0`, `config_flow: true`, and PyPI requirements (`garminconnect>=0.3.10`, `google-genai>=1.0.0`, `httpx>=0.27.0`)
**And** global constants (`DOMAIN`, default configuration values, notification schema keys) are centralized in `const.py`

### Story 1.2: Local Storage & Token Persistence Helper (`storage.py`)

As a Home Assistant component system,
I want a secure local `Store` helper wrapper (`storage.py`) guarded by `asyncio.Lock()`,
So that Garmin OAuth tokens (`garmin_ha_ai_tokens.json`) and daily metric history snapshots (`garmin_ha_ai_history.json`) are safely persisted in Home Assistant `.storage` without data race corruption or storing plaintext passwords.

**Acceptance Criteria:**

**Given** `storage.py` initializing Home Assistant `Store` helpers
**When** data read or write operations occur
**Then** all disk I/O operations are serialized using `asyncio.Lock()`
**And** missing storage files on clean installation return empty dictionary data structures without raising unhandled errors

### Story 1.3: Garmin Client Authentication Adapter & Token Lifecycle (`garmin_client.py`)

As a Home Assistant component system,
I want an authentication adapter wrapping `python-garminconnect` with silent refresh, MFA callback support, and reauth exception handling,
So that persistent Garmin sessions remain valid across restarts and trigger native Home Assistant UI re-authentication (`ConfigEntryAuthFailed` / `async_step_reauth`) if credentials expire or are revoked.

**Acceptance Criteria:**

**Given** valid stored OAuth tokens in `.storage/garmin_ha_ai_tokens.json`
**When** the Garmin client initializes or tokens approach expiration
**Then** `garmin_client.py` silently refreshes access tokens without requiring plaintext passwords
**And** if authentication fails permanently (password change or token revocation), the client raises `ConfigEntryAuthFailed` to trigger native HA re-authentication UI

### Story 1.4: UI Config Flow & MFA Setup Wizard (`config_flow.py`)

As a Home Assistant user,
I want an intuitive UI Config Flow wizard supporting Garmin authentication, 120s MFA passcode countdown, AI Provider/Key selection, and initial fitness goals,
So that I can complete initial integration setup in under 3 minutes through the Home Assistant UI without manual YAML edits.

**Acceptance Criteria:**

**Given** a user adding "Garmin HA AI" via Settings -> Devices & Services
**When** entering Garmin email/password and (if triggered) 6-digit MFA passcode within 120s
**Then** the Config Flow validates credentials, prompts for AI Provider selection (Gemini vs OpenAI) and initial goals, and creates the config entry upon success
**And** if MFA input times out or credentials fail, clear UI error alerts and retry options are presented without restarting the setup wizard

### Story 1.5: Garmin Metric Data Ingestion & Normalization

As a Home Assistant component system,
I want to fetch and normalize daily health statistics into a `GarminDailyMetrics` dataclass,
So that raw Garmin API payload responses are converted into standardized, clean metric records for sensor entities and local history.

**Acceptance Criteria:**

**Given** an authenticated Garmin Connect session
**When** daily metrics are fetched for a target date
**Then** the client extracts steps, distance (km), total calories, resting heart rate, average stress score, sleep score, HRV status, body battery (min/max), weight (kg), and logged activities into a structured `GarminDailyMetrics` dataclass instance

### Story 1.6: DataUpdateCoordinator & Scheduled Polling Engine (`coordinator.py`)

As a Home Assistant user,
I want a `GarminDataUpdateCoordinator` managing background polling schedules (default daily at 06:00 AM or periodic interval) with offline and rate-limit resilience,
So that Garmin data updates reliably without over-polling or crashing on network interruptions.

**Acceptance Criteria:**

**Given** a configured integration entry
**When** the scheduled polling timer fires
**Then** `coordinator.py` executes data ingestion, saves daily metric snapshots into `.storage/garmin_ha_ai_history.json`, and updates entity states
**And** if a network outage or Garmin rate-limit occurs, previous sensor states remain available with logged warnings without crashing Home Assistant Core

### Story 1.7: Native Garmin Metric Sensor Entities (`sensor.py`)

As a Home Assistant user,
I want native Home Assistant sensor entities for key Garmin metrics (`sensor.garmin_steps`, `sensor.garmin_resting_hr`, `sensor.garmin_sleep_score`, `sensor.garmin_stress_level`, `sensor.garmin_weight`, `sensor.garmin_body_battery`),
So that I can monitor my fitness metrics directly on Lovelace dashboards with standard units and state classes.

**Acceptance Criteria:**

**Given** a running `garmin_ha_ai` integration
**When** coordinator metrics update
**Then** entities `sensor.garmin_steps`, `sensor.garmin_resting_hr`, `sensor.garmin_sleep_score`, `sensor.garmin_stress_level`, `sensor.garmin_weight`, and `sensor.garmin_body_battery` update their states and attributes in the HA Entity Registry
**And** all status badges support full text `aria-label` descriptions and high-contrast color coding

---

## Epic 2: Automated AI Coaching Reports & Multi-Channel Delivery

User receives daily scheduled and manually triggered AI health briefings (via Google Gemini `google-genai` SDK or generic OpenAI `httpx` async client) grounded in daily metrics, accumulated 7-day history, personal goals, and coaching directives. Reports populate native HA report sensors (`sensor.garmin_ai_health_report_short` strictly truncated to <255 chars in Python to prevent `InvalidStateError`, `sensor.garmin_ai_health_report_long` with full markdown in extra state attributes) and dispatch to configured notification channels (push, persistent, email) catching `ServiceNotFound`/`HomeAssistantError` with debouncing (`_is_generating`) and fault isolation.

### Story 2.1: Pluggable AI Engine Drivers (Gemini SDK & Generic OpenAI HTTPX)

As a Home Assistant component system,
I want pluggable AI engine drivers (`ai_engine/gemini.py` using official `google-genai` SDK and `ai_engine/openai.py` using `httpx` async client),
So that AI requests target Google Gemini (default `gemini-2.0-flash`) or generic OpenAI-compatible endpoints with configurable 30s timeouts and exponential backoff retry.

**Acceptance Criteria:**

**Given** configured AI provider credentials (Gemini or OpenAI API key / Base URL)
**When** the AI engine receives a prompt payload
**Then** the selected driver (`GeminiProvider` or `OpenAIProvider`) executes an asynchronous request targeting the specified endpoint
**And** API timeouts or 5xx errors trigger up to 2 retries with exponential backoff before reporting failure

### Story 2.2: 5-Block Prompt Context Assembler (`prompt.py`)

As a Home Assistant component system,
I want a prompt context assembler (`prompt.py`) constructing payloads with (1) current day metrics, (2) 7-day metric history trends, (3) user goals, (4) persona directives, and (5) structural output formatting rules,
So that AI models receive comprehensive, grounded context while adhering to model token context limits through smart truncation.

**Acceptance Criteria:**

**Given** current daily metrics, 7-day history from `.storage`, user weight/workout goals, and focus directive
**When** `prompt.py` assembles the report prompt
**Then** the resulting prompt string contains all 5 structured context blocks formatted for optimal LLM synthesis
**And** history data is truncated automatically if payload length exceeds safety thresholds

### Story 2.3: AI Health Report Sensor Entities & 255-Char Protection (`sensor.py`)

As a Home Assistant user,
I want `sensor.garmin_ai_health_report_short` and `sensor.garmin_ai_health_report_long` sensor entities,
So that I can view concise 1-2 sentence dashboard recommendations without triggering HA Core `InvalidStateError` (<255 chars) while reading full rich Markdown reports in extra state attributes.

**Acceptance Criteria:**

**Given** a generated `AIHealthReport` object
**When** report sensors update state
**Then** `sensor.garmin_ai_health_report_short` state is strictly truncated in Python (`[:250] + "..."`) to avoid Home Assistant's 255-character hard state limit
**And** `sensor.garmin_ai_health_report_long` state displays a brief status header, while its `extra_state_attributes["full_report"]` contains the complete Markdown report

### Story 2.4: Scheduled Report Orchestration & Debounced Trigger Service (`coordinator.py`)

As a Home Assistant user,
I want automated scheduled daily report generation and a manual trigger service `garmin_ha_ai.generate_report` protected by an in-flight debouncing lock (`_is_generating`),
So that my daily AI briefing updates within <15s of scheduled time and manual button clicks ignore rapid duplicate triggers.

**Acceptance Criteria:**

**Given** the completion of daily Garmin data sync
**When** scheduled report generation triggers or service `garmin_ha_ai.generate_report` is called
**Then** the AI engine generates short and long report payloads within <15 seconds (NFR-2)
**And** an internal `_is_generating` boolean lock prevents concurrent duplicate executions from rapid UI button clicks

### Story 2.5: Multi-Channel Fault-Tolerant Notification Dispatch

As a Home Assistant user,
I want generated daily AI reports dispatched to configured notification targets (mobile app push, persistent notification, or email),
So that I receive health briefings on my phone while protecting entity state updates if notification services fail.

**Acceptance Criteria:**

**Given** a generated daily AI report and configured notification target (e.g. `notify.mobile_app_phone`)
**When** the coordinator dispatches the report notification
**Then** a notification service call executes containing the short and long report summary
**And** if the notification target raises `ServiceNotFound` or `HomeAssistantError`, the exception is logged as a warning while report sensors update normally

---

## Epic 3: Interactive Health Q&A & Local History Management

User can ask context-grounded health and workout questions on demand via service `garmin_ha_ai.ask_question` (with `SupportsResponse.OPTIONAL` direct response data and update to `sensor.garmin_ai_last_answer`) or interactive Lovelace Q&A cards. Question answering queries local 30-day historical JSON store (`.storage/garmin_ha_ai_history.json` guarded by `asyncio.Lock()` with graceful fallback on missing files) to ground queries without hitting Garmin cloud APIs. Also supports dynamic Options Flow updates (`options_flow.py`) for goals, directives, schedule, and retention window post-installation.

### Story 3.1: Interactive Q&A Service Registration & History Grounding (`services.py`)

As a Home Assistant user,
I want service `garmin_ha_ai.ask_question` registered with `SupportsResponse.OPTIONAL` direct response data,
So that I can ask context-grounded workout questions (with N-day local history context) and receive answers directly in service response data within <10 seconds.

**Acceptance Criteria:**

**Given** service `garmin_ha_ai.ask_question` registered in `services.py`
**When** called with parameters `question` (string), `days_history` (default 7), and optional `response_entity`
**Then** the service fetches past N days of metrics from `.storage/garmin_ha_ai_history.json` (clamped to available history), queries the AI engine, and returns `{"answer": "...", "question": "..."}` directly as response data
**And** response time completes in <10 seconds (NFR-3) without executing external Garmin API network calls

### Story 3.2: Last Answer Sensor Entity & Interactive Lovelace Q&A Card Pattern

As a Home Assistant user,
I want `sensor.garmin_ai_last_answer` and an interactive Lovelace Q&A card pattern (`paper-input` + "Ask Coach" submit button),
So that I can ask questions directly from dashboard cards and inspect previous answers.

**Acceptance Criteria:**

**Given** a user interacting with a dashboard Q&A card
**When** submitting a question via the card input
**Then** service `garmin_ha_ai.ask_question` executes and updates `sensor.garmin_ai_last_answer` state and `extra_state_attributes["full_answer"]`
**And** the Q&A card displays the answer formatted in Markdown

### Story 3.3: UI Options Flow & Retention Window Management (`options_flow.py`)

As a Home Assistant user,
I want a UI Options Flow panel (`options_flow.py`) to update fitness goals, AI directives, polling schedule, notification targets, and local history retention (7 to 90 days),
So that I can reconfigure settings post-installation and automatically prune old historical metric JSON snapshots without re-authenticating.

**Acceptance Criteria:**

**Given** an installed `garmin_ha_ai` integration entry
**When** opening Options Flow via Settings -> Devices & Services -> Configure
**Then** the user can update target weight, workout targets, focus directive, polling schedule, and retention window (`retention_days`)
**And** saving options updates entry settings immediately and triggers historical snapshot pruning in `.storage/garmin_ha_ai_history.json`

