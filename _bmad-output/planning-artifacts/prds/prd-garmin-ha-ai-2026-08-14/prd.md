---
title: PRD - Garmin Home Assistant AI Integration (garmin-ha-ai)
status: final
created: 2026-08-14
updated: 2026-08-14
---

# PRD: Garmin Home Assistant AI Integration (`garmin-ha-ai`)

## 0. Document Purpose
This Product Requirements Document (PRD) defines the functional and non-functional requirements for `garmin-ha-ai`, a Home Assistant custom component that syncs health metrics from Garmin Connect and utilizes AI (Google Gemini or generic OpenAI-compatible APIs) to deliver automated insights, recommendations, and interactive Q&A. This document serves as the machine contract for downstream UX design, technical architecture (`bmad-architecture`), epic/story creation (`bmad-create-epics-and-stories`), and direct code implementation.

---

## 1. Vision
`garmin-ha-ai` transforms raw fitness tracking data into an intelligent, privacy-first personal health and fitness coach embedded inside Home Assistant. By connecting Garmin Connect metrics directly to user-selected LLM APIs (defaulting to Google Gemini via Google AI Pro), users gain actionable, context-aware advice on workouts, recovery, and lifestyle adjustments without paying recurring cloud app subscriptions or locking personal metrics into proprietary platforms.

---

## 2. Target User

### 2.1 Jobs To Be Done (JTBD)
- **Functional**: Automatically fetch daily Garmin fitness data (steps, HR, HRV, sleep, stress, body battery, activities) and store it locally inside Home Assistant without manual CSV exports.
- **Analytical**: Have an AI model analyze combined health data against personal fitness/weight goals and provide daily/weekly summaries with actionable recommendations.
- **Interactive**: Ask health and workout questions on-demand (via HA service calls or dashboards) where the AI has full context of historical Garmin metrics.
- **Integration**: Receive proactive health alerts and reports across native Home Assistant channels (dashboards, push notifications, email).
- **Deployment**: Install the custom component into standard Home Assistant (or HACS) effortlessly via UI Config Flow.

### 2.2 Non-Users (v1)
- Users seeking medical-grade diagnosis or emergency advice (the integration explicitly provides wellness coaching, not clinical diagnosis).
- Non-Home Assistant users (this component requires Home Assistant Core 2024.1+).

### 2.3 Key User Journeys

- **UJ-1. Jens configures the integration via Home Assistant UI.**
  - **Persona + context**: Jens wants to set up his Garmin account and Google Gemini API key inside Home Assistant.
  - **Entry state**: Jens installs `garmin_ha_ai` into `custom_components/` and restarts Home Assistant.
  - **Path**: Navigates to Settings -> Devices & Services -> Add Integration -> "Garmin HA AI". Enters Garmin email and password. If MFA is required, a second form prompts for the 6-digit code. Next screen prompts for AI Provider (Gemini / OpenAI), API Key, fitness/weight goals, AI focus directive, and schedule.
  - **Climax**: Integration successfully saves tokens to `.storage/garmin_ha_ai_tokens.json` and creates sensors immediately.
  - **Resolution**: Daily metrics begin syncing automatically.
  - **Edge case**: If Garmin password or MFA code is invalid, HA UI shows a clean error message and allows re-entry without restarting setup.

- **UJ-2. Morning Health & Workout Briefing.**
  - **Persona + context**: Jens wakes up and checks his Home Assistant dashboard or mobile push notification.
  - **Entry state**: Scheduled sync triggers at 07:00 AM after Garmin syncs overnight sleep and HRV data.
  - **Path**: Integration fetches latest metrics via `python-garminconnect`, assembles an LLM prompt with goals + 7-day history, calls Gemini API, and updates `sensor.garmin_ai_health_report_short` and `sensor.garmin_ai_health_report_long`.
  - **Climax**: Jens sees a concise card on his dashboard: "Recovery high (Sleep 88/100, HRV baseline). Recommended today: 45 min Zone 2 run."
  - **Resolution**: Jens plans his workout accordingly.

- **UJ-3. Interactive Health Q&A via Home Assistant Service.**
  - **Persona + context**: Jens wants to ask his AI coach whether he should skip leg day after a heavy hiking session yesterday.
  - **Entry state**: Jens opens a dashboard card or calls service `garmin_ha_ai.ask_question`.
  - **Path**: Jens submits question: *"My knees feel slightly stiff after yesterday's hike. Should I do heavy squats today?"* The service extracts the past 7 days of activity and sleep metrics, sends the combined prompt to Gemini, and returns the response.
  - **Climax**: Response arrives in seconds: *"Your hike yesterday was 14km with 650m elevation. Given your stiff knees and elevated muscle stress, swap heavy squats for light mobility work and cycling today."*
  - **Resolution**: Response is displayed in UI and saved to sensor history.

---

## 3. Glossary

- **Garmin Connect**: Garmin's cloud service hosting user fitness, activity, and health metric data.
- **python-garminconnect**: The Python 3 library used to authenticate and fetch statistics from Garmin Connect.
- **DI OAuth Tokens**: OAuth access and refresh tokens returned by Garmin SSO, stored locally to avoid re-authenticating with credentials.
- **DataUpdateCoordinator**: Home Assistant class responsible for periodically fetching data and updating entities efficiently.
- **Config Flow**: Home Assistant's UI setup wizard (`config_flow.py`) for component configuration.
- **Options Flow**: Home Assistant's UI settings panel for updating runtime parameters (goals, schedules, prompts) after initial setup.
- **AI Provider Engine**: Pluggable backend handler supporting Google Gemini (`google-genai`) or standard OpenAI API endpoints.
- **Health Report Sensor**: Home Assistant text/markdown sensors (`sensor.garmin_ai_health_report_short`, `sensor.garmin_ai_health_report_long`) holding AI generated analysis.
- **Ask Question Service**: Exposed Home Assistant service (`garmin_ha_ai.ask_question`) for on-demand interactive health queries.

---

## 4. Features

### 4.1 Garmin Connect Data Synchronization
**Description:** Fetches daily health metrics, activities, sleep, stress, and body battery from Garmin Connect using `python-garminconnect`. Realizes UJ-1, UJ-2.

#### FR-1: Credential & Token Authentication
System MUST authenticate with Garmin Connect via email/password and support MFA callback prompts. DI OAuth tokens MUST be saved locally to Home Assistant `.storage` to maintain persistent login sessions without storing plaintext passwords in memory.
- **Consequences (testable)**:
  - Valid credentials create valid token file in HA storage.
  - Expired tokens trigger automatic silent refresh using stored refresh token.
- **Out of Scope**: Storing raw Garmin passwords in persistent configuration files.

#### FR-2: Metric Extraction
System MUST extract the following metrics for the target date: steps, distance, calories, resting heart rate, average stress score, sleep score, HRV status, body battery min/max, weight, and logged activities. Realizes UJ-2.
- **Consequences (testable)**:
  - Extracted metrics are parsed into a normalized Python dataclass/dict available to the coordinator.

#### FR-3: Flexible Polling Schedule
System MUST support configurable polling schedules: daily at specified time, periodic interval (e.g. every 6/12/24 hours), weekly, monthly, or manually triggered via service call. Realizes UJ-2. `[ASSUMPTION: Default schedule is daily at 06:00 AM].`
- **Consequences (testable)**:
  - Scheduled timer fires coordinator update at exact configured schedule.

#### FR-4: Offline / Rate-Limit Resilience
System MUST handle network failures or Garmin API rate limits gracefully by caching the latest successfully fetched metrics and logging warnings without crashing Home Assistant.
- **Consequences (testable)**:
  - Network interruption leaves previous sensor states intact with `available = True` or error state.

---

### 4.2 Multi-LLM AI Engine
**Description:** Constructs prompt payloads combining Garmin metrics, user goals, and directives, and sends them to the configured AI provider. Realizes UJ-2, UJ-3.

#### FR-5: Primary Provider (Google Gemini)
System MUST support Google Gemini API (using `google-genai` SDK) configured with an API key (e.g. Google AI Pro plan). Realizes UJ-2. `[ASSUMPTION: Default model is gemini-1.5-pro or gemini-2.0-flash].`
- **Consequences (testable)**:
  - Valid Gemini API key successfully returns generated report text.

#### FR-6: Configurable Generic LLM Provider
System MUST support any OpenAI-compatible API endpoint by allowing custom Base URL (e.g. `http://localhost:11434/v1` for Ollama or `https://api.openai.com/v1`), API key, and Model ID. Realizes UJ-2.
- **Consequences (testable)**:
  - System successfully sends standard `/v1/chat/completions` request to custom base URL and parses response.

#### FR-7: Prompt Context Assembly
System MUST assemble prompt payloads containing: (1) Current day metrics, (2) 7-day metric history/trends, (3) User goals (fitness targets, weight goal), (4) Persona directives (e.g. "Focus on marathon training"), and (5) Specific instructions for output structure (short summary vs deep report). Realizes UJ-2, UJ-3.
- **Consequences (testable)**:
  - Formatted prompt string contains all 5 contextual blocks.

#### FR-8: Response Error Handling & Retry
System MUST handle AI API timeout or quota errors with up to 2 retries before marking report state with an error indicator.
- **Consequences (testable)**:
  - API 500/503 errors trigger exponential backoff retry.

---

### 4.3 Home Assistant Integration & Entities
**Description:** Exposes native Home Assistant sensors and entities. Realizes UJ-1, UJ-2.

#### FR-9: Garmin Metrics Sensors
System MUST create Home Assistant sensor entities for key Garmin metrics: `sensor.garmin_steps`, `sensor.garmin_resting_hr`, `sensor.garmin_sleep_score`, `sensor.garmin_stress_level`, `sensor.garmin_weight`, `sensor.garmin_body_battery`.
- **Consequences (testable)**:
  - Entities appear in HA Entity Registry with correct state, units (`steps`, `bpm`, `kg`, `%`), and `state_class`.

#### FR-10: AI Report Sensor Entities
System MUST create `sensor.garmin_ai_health_report_short` (concise 1-2 sentence dashboard text) and `sensor.garmin_ai_health_report_long` (full markdown report stored in state or attribute `full_report`). Realizes UJ-2.
- **Consequences (testable)**:
  - Dashboard text cards render short report cleanly without truncation.

#### FR-11: Integration Status & Last Sync Sensor
System MUST maintain `sensor.garmin_ai_last_update` showing timestamp of last successful Garmin sync and AI report generation.
- **Consequences (testable)**:
  - Timestamp updates accurately after each execution.

---

### 4.4 Automated Report Generation & Multi-Channel Delivery
**Description:** Triggers scheduled report generation and dispatches reports to configured notification channels. Realizes UJ-2.

#### FR-12: Multi-Channel Dispatch
System MUST support dispatching generated reports to configured Home Assistant notification targets (e.g. `notify.mobile_app_phone`, persistent notification, or email service `notify.email`). `[ASSUMPTION: Default delivery is dashboard entities + optional push notification].`
- **Consequences (testable)**:
  - When enabled, service call to configured notify target is executed with short/long report payload.

#### FR-13: Manual Report Trigger Service
System MUST expose service `garmin_ha_ai.generate_report` to allow manual execution from Lovelace buttons, automations, or scripts.
- **Consequences (testable)**:
  - Calling `garmin_ha_ai.generate_report` immediately executes sync + LLM report generation.

---

### 4.5 Interactive Health Q&A Service
**Description:** Allows on-demand interactive health queries with automatic Garmin data grounding. Realizes UJ-3.

#### FR-14: Service `garmin_ha_ai.ask_question`
System MUST register service `garmin_ha_ai.ask_question` accepting parameters: `question` (string, required), `days_history` (int, default 7), and `response_entity` (optional). Realizes UJ-3.
- **Consequences (testable)**:
  - Calling service returns response text in service response data and updates `sensor.garmin_ai_last_answer`.

#### FR-15: History Injection into Q&A Prompt
System MUST automatically fetch the past N days (`days_history`) of cached Garmin metrics and append them to the system prompt before invoking the LLM. Realizes UJ-3.
- **Consequences (testable)**:
  - LLM receives structured historical context alongside the user's question.

---

### 4.6 Configuration & Options Management
**Description:** UI-based setup and runtime configuration. Realizes UJ-1.

#### FR-16: UI Config Flow Setup
System MUST provide UI Config Flow (`config_flow.py`) for initial setup: Garmin Credentials (email, password, MFA code), AI Provider Selection (Gemini vs Custom OpenAI), API Key, and Initial Goals. Realizes UJ-1.
- **Consequences (testable)**:
  - User can complete full setup through HA UI without editing `configuration.yaml`.

#### FR-17: UI Options Flow Updates
System MUST provide UI Options Flow (`options_flow`) to allow updating goals, AI focus directives, sync schedules, and notification targets post-installation without re-entering credentials.
- **Consequences (testable)**:
  - Changing target weight or schedule in Options Flow takes effect immediately on next sync.

---

### 4.7 Deployment & HACS Packaging
**Description:** Standardized Home Assistant custom component packaging for instant deployment. Realizes UJ-1.

#### FR-18: Custom Component Package & Manifest
System MUST package all code under `custom_components/garmin_ha_ai/` with a valid `manifest.json` containing `domain: garmin_ha_ai`, version, dependencies (`python-garminconnect`, `google-genai`), and documentation URL. Realizes UJ-1.
- **Consequences (testable)**:
  - Component installs cleanly by copying directory into HA `custom_components/` or installing via HACS custom repository.

---

## 5. Non-Goals (Explicit)

- **Not a Medical Device**: `garmin-ha-ai` is explicitly NOT intended for medical diagnosis, treatment recommendations, or emergency response.
- **No Direct Bluetooth Watch Connection**: `garmin-ha-ai` does NOT pair directly with Garmin watches over Bluetooth/ANT+; it ingests data via Garmin Connect cloud APIs.
- **No Cloud Subscription Middleware**: `garmin-ha-ai` does NOT route data through any intermediate vendor server; communication occurs directly between Home Assistant, Garmin Connect, and the user's LLM provider.

---

## 6. MVP Scope

### 6.1 In Scope for MVP
- Custom component package under `custom_components/garmin_ha_ai/`.
- UI Config Flow for Garmin credentials (with MFA) and Google Gemini / OpenAI API key.
- Garmin metric fetching via `python-garminconnect` (steps, HR, sleep, stress, weight, activities).
- Scheduled daily AI report generation producing `sensor.garmin_ai_health_report_short` and `sensor.garmin_ai_health_report_long`.
- Service `garmin_ha_ai.ask_question` with 7-day historical context grounding.
- UI Options Flow for dynamic setting updates.
- Push notification integration via Home Assistant notify services.
- Clean Git repository setup pushed to `http://git.crins:3000/jens/garmin-ha-ai`.

### 6.2 Out of Scope for MVP
- Direct Bluetooth synchronization with Garmin hardware.
- Multi-user Garmin account switching per Home Assistant instance (single user profile per entry in v1).
- Custom fine-tuned local models (standard API endpoints supported).

---

## 7. Success Metrics

### Primary Metrics
- **SM-1: Sync Success Rate**: >= 98% successful daily Garmin data syncs without session dropouts. Validates FR-1, FR-3, FR-4.
- **SM-2: Report Generation Latency**: Daily AI report generated and updated within < 15 seconds of scheduled time. Validates FR-5, FR-7, FR-10.
- **SM-3: Interactive Q&A Response Time**: Service `garmin_ha_ai.ask_question` returns a grounded response within < 10 seconds. Validates FR-14, FR-15.

### Secondary Metrics
- **SM-4: Deployment Ease**: Setup completed via HA UI Config Flow in under 3 minutes. Validates FR-16, FR-18.

### Counter-Metrics (Do Not Optimize)
- **SM-C1: API Request Volume**: Do NOT over-poll Garmin API or LLM API (max 1 sync per scheduled interval) to prevent Garmin rate-limiting or excessive LLM token costs.

---

## 8. Open Questions

1. **Garmin MFA Timeout**: What is the optimal UI timeout duration for users entering their 6-digit MFA code during Config Flow setup? `[Default: 120 seconds]`.
2. **Historical Data Storage Horizon**: Should Home Assistant retain past Garmin metric snapshots in HA `.storage` or rely on Garmin API historical queries? `[Default: Cache 30 days locally in JSON for fast LLM context assembly]`.

---

## 9. Assumptions Index

- `[ASSUMPTION: Default schedule is daily at 06:00 AM].` (FR-3)
- `[ASSUMPTION: Default model is gemini-1.5-pro or gemini-2.0-flash].` (FR-5)
- `[ASSUMPTION: Default delivery is dashboard entities + optional push notification].` (FR-12)
- `[ASSUMPTION: Single Garmin account per Home Assistant integration entry in v1].` (Section 6.2)
