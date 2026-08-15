# Solution Design Document — Garmin Home Assistant AI Integration (`garmin-ha-ai`)

**Document Status:** Final  
**Date:** 2026-08-15  
**Target Platform:** Home Assistant Core (2024.1+)  
**Companion Artifact to:** [`ARCHITECTURE-SPINE.md`](file:///home/jens/Projekte/garmin-ha-ai/_bmad-output/planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/ARCHITECTURE-SPINE.md)

---

## 1. Executive Summary & Technical Vision

The `garmin-ha-ai` integration bridges personal fitness metrics from Garmin Connect cloud services with advanced Large Language Model (LLM) providers (Google Gemini and generic OpenAI-compatible endpoints) directly inside Home Assistant. 

### Core Goals
- **Local Control & Privacy**: Store OAuth tokens and 30-day daily metric snapshots locally within Home Assistant's `.storage` directory.
- **Automated AI Coaching**: Schedule daily metrics ingestion and LLM prompt assembly to generate concise dashboard summaries and deep Markdown health reports.
- **Interactive Q&A Service**: Expose native Home Assistant service `garmin_ha_ai.ask_question` returning grounded responses based on historical Garmin data without live API overhead.
- **Native HA Experience**: Built using `DataUpdateCoordinator`, standard UI Config Flow/Options Flow, and Material Design icons/badges compatible with any Lovelace theme.

---

## 2. System Architecture & Component Model

The integration is implemented as a Home Assistant custom component under `custom_components/garmin_ha_ai/`.

```
                       +-----------------------------------+
                       |    Home Assistant Core Runtime    |
                       +-----------------+-----------------+
                                         |
            +----------------------------+----------------------------+
            |                            |                            |
            v                            v                            v
+-----------------------+    +-----------------------+    +-----------------------+
|  config_flow.py /     |    |    services.py        |    |      sensor.py        |
|  options_flow.py      |    |  (ask_question,       |    | (Metrics, AI Reports, |
|  (UI Setup & Settings)|    |   generate_report)    |    |  Last Sync Timestamp) |
+-----------+-----------+    +-----------+-----------+    +-----------+-----------+
            |                            |                            |
            +----------------------------+----------------------------+
                                         |
                                         v
                       +-----------------------------------+
                       |    GarminDataUpdateCoordinator    |
                       |         (coordinator.py)          |
                       +-----------------+-----------------+
                                         |
            +----------------------------+----------------------------+
            |                            |                            |
            v                            v                            v
+-----------------------+    +-----------------------+    +-----------------------+
|   garmin_client.py    |    |      storage.py       |    |      ai_engine/       |
| (python-garminconnect)|    | (HA Store Wrapper)    |    | (Gemini & OpenAI)     |
+-----------+-----------+    +-----------+-----------+    +-----------+-----------+
            |                            |                            |
            v                            v                            v
+-----------------------+    +-----------------------+    +-----------------------+
| Garmin Connect Cloud  |    | Home Assistant        |    | Google Gemini /       |
| API                   |    | .storage/ Directory   |    | OpenAI endpoints      |
+-----------------------+    +-----------------------+    +-----------------------+
```

---

## 3. Data Ingestion & Garmin Authentication Lifecycle

### 3.1 Authentication & MFA Flow
Authentication utilizes `python-garminconnect`. 

1. **Initial Setup (Config Flow)**:
   - User inputs Garmin email and password.
   - If Garmin Connect triggers a 2FA/MFA challenge, `config_flow.py` yields step `step_mfa` prompting for the 6-digit verification code.
   - Upon successful login, DI OAuth access and refresh tokens are retrieved.
2. **Token Persistence**:
   - Tokens are serialized and stored securely in HA `.storage/garmin_ha_ai_tokens.json` via `storage.py`.
   - Plaintext passwords are not retained in long-term storage.
3. **Session Recovery & Silent Refresh**:
   - On Home Assistant restart or scheduled polling, tokens are loaded from `.storage`.
   - Expired tokens auto-refresh silently via refresh tokens.
   - If refresh fails (e.g. password change), the coordinator raises `ConfigEntryAuthFailed`, triggering a native Home Assistant re-authentication notification.

### 3.2 Metric Extraction
The coordinator extracts daily summary statistics for the target date:
- Steps, total distance, total calories burned
- Resting Heart Rate (RHR), average stress score
- Sleep score, body battery (min/max), HRV status
- Weight (kg), logged workout activities

---

## 4. Multi-LLM Provider Engine Architecture

The AI layer in `custom_components/garmin_ha_ai/ai_engine/` follows a Strategy pattern:

```
                  +--------------------------------+
                  |  BaseAIProvider (Abstract Interface)
                  +---------------+----------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
+-----------------------+                   +-----------------------+
|    GeminiProvider     |                   |    OpenAIProvider     |
|   (google-genai SDK)  |                   |  (httpx Async Client) |
+-----------------------+                   +-----------------------+
```

### 4.1 Drivers
- **Google Gemini Driver (`gemini.py`)**: Interacts with `google-genai` SDK using the user's API key. Default model: `gemini-2.0-flash`.
- **OpenAI-Compatible Driver (`openai.py`)**: Interacts with any OpenAI `/v1/chat/completions` API via `httpx` async client. Supports Ollama, LM Studio, vLLM, or OpenAI endpoints.

### 4.2 Prompt Engineering & Context Assembly (`prompt.py`)
Prompts combine 5 structured blocks:
1. **System Persona**: Role directive (e.g., "You are an elite endurance coach...").
2. **Current Day Metrics**: Today's steps, HR, sleep, stress, body battery.
3. **Historical Context**: Past N days (default 7 days) of metrics retrieved from local `.storage`.
4. **User Goals & Directives**: Target weight, weekly workout targets, focus area.
5. **Output Formatting Instruction**: Mandates separation into concise summary and rich Markdown.

---

## 5. Home Assistant Integration & Entities

### 5.1 Entity Roster

| Entity ID | Type | State Value | Extra State Attributes |
| --- | --- | --- | --- |
| `sensor.garmin_steps` | Numeric Sensor | Count (e.g., `8540`) | `unit_of_measurement: steps`, `state_class: total_increasing` |
| `sensor.garmin_sleep_score` | Numeric Sensor | Score (e.g., `88`) | `unit_of_measurement: %`, `state_class: measurement` |
| `sensor.garmin_resting_hr` | Numeric Sensor | BPM (e.g., `54`) | `unit_of_measurement: bpm` |
| `sensor.garmin_stress_level` | Numeric Sensor | Level (e.g., `28`) | `unit_of_measurement: %` |
| `sensor.garmin_body_battery` | Numeric Sensor | Level (e.g., `75`) | `min`, `max` |
| `sensor.garmin_weight` | Numeric Sensor | Weight in kg (e.g., `74.5`) | `unit_of_measurement: kg` |
| `sensor.garmin_ai_health_report_short` | Text Sensor | Brief summary (<255 chars) | `timestamp`, `provider` |
| `sensor.garmin_ai_health_report_long` | Text Sensor | Status header (`Report Ready`) | `full_report` (Rich Markdown string) |
| `sensor.garmin_ai_last_answer` | Text Sensor | Answer snippet | `last_question`, `full_answer`, `timestamp` |
| `sensor.garmin_ai_last_update` | Timestamp Sensor | ISO timestamp | `status` |

### 5.2 Protection Against HA 255-Character State Limit
Home Assistant restricts standard entity state values to 255 characters. To avoid `InvalidStateError`:
- `sensor.garmin_ai_health_report_short` state is truncated/formatted to stay strictly under 255 chars.
- `sensor.garmin_ai_health_report_long` stores its header as the state string and places the entire multi-paragraph Markdown report in `extra_state_attributes["full_report"]`.

### 5.3 Services

#### 1. `garmin_ha_ai.generate_report`
Triggers immediate Garmin metric ingestion and AI health report generation.

#### 2. `garmin_ha_ai.ask_question`
- **Parameters**: `question` (string, required), `days_history` (int, default 7), `response_entity` (optional).
- **Execution**: Assembles prompt with question + local 7-day metric snapshots, queries AI engine, updates `sensor.garmin_ai_last_answer`, and returns `{"answer": "...", "question": "..."}` as direct service response data (`SupportsResponse.OPTIONAL`).

---

## 6. Data Persistence & Retention Management

To prevent rate-limiting by Garmin Connect API and ensure fast offline prompt assembly, `storage.py` manages two JSON files inside Home Assistant's `.storage/` directory:

1. **`.storage/garmin_ha_ai_tokens.json`**: Holds DI OAuth access/refresh token structures.
2. **`.storage/garmin_ha_ai_history.json`**: Holds a rolling daily snapshot map keyed by `YYYY-MM-DD`.

### Retention Strategy
- Retention period defaults to **30 days**.
- Users can customize retention (e.g., 7 to 90 days) via UI Options Flow (`options_flow.py`).
- Daily maintenance runs automatically prune entries older than `retention_days`.

---

## 7. Security, Privacy & Failure Modes

### Security & Privacy
- **Direct Cloud Communication**: Communication occurs directly between Home Assistant, Garmin Connect APIs, and the configured LLM API (Google Gemini or custom OpenAI endpoint). No third-party relay servers exist.
- **Local Storage**: All health data and tokens reside exclusively on the user's Home Assistant instance.

### Resilience & Error Matrix

| Failure Mode | Integration Handling | User Impact |
| --- | --- | --- |
| Garmin API Offline / Rate Limited | Coordinator caches last valid metrics, logs warning, keeps entities `available = True`. | Dashboard shows last valid data; retry on next schedule. |
| Garmin Password Changed / Invalid Token | `python-garminconnect` raises auth error; coordinator raises `ConfigEntryAuthFailed`. | HA UI shows "Re-authenticate" notification. |
| LLM API Quota / Timeout | Exponential backoff retry (up to 2 attempts). On persistent fail, error state logged. | Metric sensors update; AI report sensor shows error state. |
| Network Outage during Q&A | `ask_question` service returns error message gracefully without crashing HA. | UI card displays error toast. |

---

## 8. Deployment & Packaging Checklist

The component adheres to HACS (Home Assistant Community Store) packaging standards:

```text
custom_components/garmin_ha_ai/
  manifest.json
  __init__.py
  config_flow.py
  options_flow.py
  const.py
  coordinator.py
  garmin_client.py
  storage.py
  sensor.py
  services.py
  ai_engine/
    __init__.py
    base.py
    gemini.py
    openai.py
    prompt.py
```

### Dependencies (`manifest.json`)
- `garminconnect>=0.3.10`
- `google-genai>=1.0.0`
- `httpx>=0.27.0`

---

*This Solution Design Document completes the technical architecture phase for `garmin-ha-ai`.*
