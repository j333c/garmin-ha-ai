---
name: 'garmin-ha-ai'
type: architecture-spine
purpose: build-substrate
altitude: feature
paradigm: 'Layered Adapter Architecture with DataUpdateCoordinator & Strategy Pattern'
scope: 'Garmin Home Assistant AI Integration'
status: final
created: '2026-08-15'
updated: '2026-08-15'
binds: ['FR-1', 'FR-2', 'FR-3', 'FR-4', 'FR-5', 'FR-6', 'FR-7', 'FR-8', 'FR-9', 'FR-10', 'FR-11', 'FR-12', 'FR-13', 'FR-14', 'FR-15', 'FR-16', 'FR-17', 'FR-18']
sources: ['planning_artifacts/prds/prd-garmin-ha-ai-2026-08-14/prd.md', 'planning_artifacts/ux-designs/ux-garmin-ha-ai-2026-08-15/DESIGN.md']
companions: ['solution-design-garmin-ha-ai-2026-08-15.md']
---

# Architecture Spine — garmin-ha-ai

## Design Paradigm

`garmin-ha-ai` follows a **Layered Adapter Architecture** built natively on Home Assistant's `DataUpdateCoordinator` pattern with a pluggable **Strategy Pattern** for AI providers.

```text
+-----------------------------------------------------------------------+
|                 Home Assistant UI / Entities / Services               |
|      (sensor.py, services.py, config_flow.py, options_flow.py)       |
+------------------------------------+----------------------------------+
                                     |
                                     v
+-----------------------------------------------------------------------+
|                    GarminDataUpdateCoordinator                        |
|        (Schedules background fetching, triggers AI analysis)          |
+-------------------+--------------------------------+------------------+
                    |                                |
                    v                                v
+-----------------------+               +-------------------------------+
|   garmin_client.py    |               |          ai_engine/           |
| (python-garminconnect)|               | (Gemini & OpenAI Providers)   |
+-----------+-----------+               +---------------+---------------+
            |                                           |
            v                                           v
+-----------------------+               +-------------------------------+
|  Garmin Connect Cloud |               |  LLM APIs (Gemini / OpenAI)   |
+-----------------------+               +-------------------------------+
                                |
                                v
+-----------------------------------------------------------------------+
|                         storage.py (HA Store)                         |
|   (.storage/garmin_ha_ai_tokens.json & garmin_ha_ai_history.json)      |
+-----------------------------------------------------------------------+
```

### Module Responsibilities
- **`custom_components/garmin_ha_ai/__init__.py`**: Component entry point managing setup, unload, service registration, and entry updates.
- **`config_flow.py` & `options_flow.py`**: UI forms for initial credential setup, MFA callback handling, provider selection, and runtime options (goals, schedule, retention window).
- **`coordinator.py`**: `GarminDataUpdateCoordinator` orchestrating periodic data ingestion and scheduled daily report generation.
- **`garmin_client.py`**: Authentication adapter around `python-garminconnect`, token refresh, MFA PIN resolution, and raw payload normalization into `GarminDailyMetrics`.
- **`storage.py`**: Encapsulates Home Assistant `Store` helper for persisting OAuth tokens (`garmin_ha_ai_tokens`) and local N-day metric snapshots (`garmin_ha_ai_history`).
- **`ai_engine/`**: Pluggable AI engine package containing `base.py` (`BaseAIProvider`), `gemini.py` (`GeminiProvider`), `openai.py` (`OpenAIProvider`), and `prompt.py` (context prompt assembly).
- **`sensor.py`**: Home Assistant sensor entity implementations for Garmin metrics and AI report states.
- **`services.py`**: Home Assistant service definitions for `garmin_ha_ai.ask_question` and `garmin_ha_ai.generate_report`.
- **`const.py`**: Constants, domain identifiers, default values, and config keys.

---

## Invariants & Rules

### AD-1 — Layered Adapter with DataUpdateCoordinator Strategy Pattern
- **Binds:** `all`
- **Prevents:** Monolithic tightly-coupled entity code, un-testable business logic, and tangled LLM client calls.
- **Rule:** Integration components MUST be split into distinct layers: `garmin_client.py` (ingestion), `ai_engine/` (AI analysis), `storage.py` (local persistence), `coordinator.py` (orchestration), and HA platform modules (`sensor.py`, `services.py`). No direct API calls may be made inside entity classes.

### AD-2 — Local JSON Snapshot Store with Configurable Retention
- **Binds:** `storage.py`, `services.py`, `options_flow.py`
- **Prevents:** Rate-limiting by Garmin API during interactive Q&A service calls and loss of historical trend context during network outages.
- **Rule:** Daily metrics MUST be saved locally to HA `.storage/garmin_ha_ai_history.json`. Retention defaults to 30 days and MUST be configurable by the user via Options Flow (`retention_days`). Interactive Q&A MUST query this local store for historical context rather than hitting Garmin cloud APIs.

### AD-3 — Dual Native Driver AI Engine Architecture
- **Binds:** `ai_engine/`
- **Prevents:** Bloating custom component dependencies with heavy frameworks like LangChain or LlamaIndex.
- **Rule:** AI provider drivers MUST be lightweight and native. Google Gemini integration MUST use the official `google-genai` SDK. OpenAI-compatible integration MUST use `httpx` async client targeting standard `/v1/chat/completions` endpoints.

### AD-4 — OAuth Token Persistence & MFA Authentication Flow
- **Binds:** `config_flow.py`, `garmin_client.py`, `storage.py`
- **Prevents:** Storing plaintext user passwords in config files and losing login sessions across Home Assistant restarts.
- **Rule:** Credentials MUST be authenticated via `python-garminconnect`. If an MFA challenge is returned, `config_flow` MUST transition to step `step_mfa`. On auth success, DI OAuth tokens MUST be saved to HA `.storage/garmin_ha_ai_tokens.json`. Expired access tokens MUST be refreshed silently using refresh tokens. If tokens are invalidated, the coordinator MUST raise `ConfigEntryAuthFailed` to trigger native HA re-auth UI.

### AD-5 — Entity State Protection & Extra State Attributes for Reports
- **Binds:** `sensor.py`, `coordinator.py`
- **Prevents:** Home Assistant core error `InvalidStateError` caused by state string lengths exceeding HA's 255-character hard limit.
- **Rule:** `sensor.garmin_ai_health_report_short` state MUST contain a concise summary (<255 characters). `sensor.garmin_ai_health_report_long` state MUST contain a short summary header/timestamp, while the full rich Markdown report MUST be stored in `extra_state_attributes["full_report"]`.

### AD-6 — Modern HA Service Response Support (`SupportsResponse.OPTIONAL`)
- **Binds:** `services.py`, `ai_engine/`
- **Prevents:** Clunky asynchronous event dispatching for interactive Q&A service callers.
- **Rule:** Service `garmin_ha_ai.ask_question` MUST register using `supports_response=SupportsResponse.OPTIONAL`. When invoked, it MUST return a dictionary `{"answer": "...", "question": "...", "context_days": N}` directly to the caller, while updating entity `sensor.garmin_ai_last_answer`.

### Dependency Topology Rule

```mermaid
graph TD
    ConfigFlow[config_flow.py / options_flow.py] --> Storage[storage.py]
    ConfigFlow --> GarminClient[garmin_client.py]
    
    Coordinator[coordinator.py] --> GarminClient
    Coordinator --> AIEngine[ai_engine/]
    Coordinator --> Storage
    
    Sensors[sensor.py] --> Coordinator
    Services[services.py] --> AIEngine
    Services --> Storage
    Services --> Coordinator
    
    GarminClient --> GarminAPI[Garmin Connect Cloud]
    AIEngine --> GeminiAPI[Google Gemini API]
    AIEngine --> OpenAIAPI[OpenAI-Compatible Endpoint]
```

---

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| Naming | Domain `garmin_ha_ai`, snake_case Python modules, lower_snake_case HA entity IDs (`sensor.garmin_steps`, `sensor.garmin_ai_health_report_short`). |
| Data & Formats | Dates in ISO 8601 (`YYYY-MM-DD`). Metric units standard SI (`steps`, `bpm`, `kg`, `km`, `%`). |
| State & Mutation | State updates handled strictly via `GarminDataUpdateCoordinator`. Service calls trigger async AI tasks. |
| Error Handling | Ingestion errors raise `UpdateFailed`. Auth failure raises `ConfigEntryAuthFailed`. LLM timeouts retry up to 2 times with exponential backoff. |

---

## Stack

| Name | Version | Role |
| --- | --- | --- |
| Python | `>= 3.12` | Runtime Language |
| Home Assistant Core | `>= 2024.1.0` | Target Host Platform |
| `garminconnect` | `>= 0.3.10` | Garmin Connect API Client |
| `google-genai` | `>= 1.0.0` | Google Gemini SDK Driver |
| `httpx` | `>= 0.27.0` | OpenAI Async HTTP Client Driver |
| `voluptuous` | Native HA | Data Validation Schema Engine |

---

## Structural Seed

### Source Directory Scaffolding

```text
custom_components/garmin_ha_ai/
  __init__.py           # Component setup, unload, entry listener & service registration
  manifest.json         # HA component manifest & PyPI dependencies
  config_flow.py        # UI setup wizard & MFA callback flow
  options_flow.py       # UI options flow for runtime settings & retention window
  const.py              # Global domain constants, defaults & schema keys
  coordinator.py        # GarminDataUpdateCoordinator implementation
  garmin_client.py      # python-garminconnect auth & data fetch adapter
  storage.py            # HA .storage helper wrapper for tokens & history JSON
  sensor.py             # Sensor platform entities (metrics & AI reports)
  services.py           # HA service handlers (ask_question, generate_report)
  ai_engine/
    __init__.py         # AI Engine factory initializer
    base.py             # BaseAIProvider abstract protocol interface
    gemini.py           # GeminiProvider driver (google-genai)
    openai.py           # OpenAIProvider driver (httpx async)
    prompt.py           # Prompt assembler & context formatter
```

### Core Data Models

```python
@dataclass
class GarminDailyMetrics:
    date: str  # YYYY-MM-DD
    steps: int
    distance_meters: float
    calories: int
    resting_hr: int
    avg_stress: int
    sleep_score: int
    body_battery_min: int
    body_battery_max: int
    hrv_status: str
    weight_kg: float | None
    activities: list[dict]

@dataclass
class AIHealthReport:
    timestamp: str  # ISO 8601
    short_summary: str
    full_report: str
    provider_used: str
    model_used: str
```

---

## Capability → Architecture Map

| Capability / Area | Lives in | Governed by |
| --- | --- | --- |
| Credential & MFA Auth (FR-1, FR-16) | `config_flow.py`, `garmin_client.py` | AD-4 |
| Metric Extraction (FR-2) | `garmin_client.py` | AD-1 |
| Scheduled Polling & Options (FR-3, FR-17) | `coordinator.py`, `options_flow.py` | AD-1, AD-2 |
| Offline Resilience (FR-4) | `coordinator.py`, `storage.py` | AD-2 |
| Gemini AI Provider (FR-5) | `ai_engine/gemini.py` | AD-3 |
| Generic OpenAI Provider (FR-6) | `ai_engine/openai.py` | AD-3 |
| Prompt Assembly (FR-7) | `ai_engine/prompt.py` | AD-1, AD-2 |
| Metric & AI Report Entities (FR-9, FR-10, FR-11) | `sensor.py` | AD-5 |
| Multi-Channel Delivery (FR-12) | `coordinator.py` | AD-5 |
| Interactive Q&A Service (FR-14, FR-15) | `services.py`, `storage.py` | AD-2, AD-6 |
| Custom Component Packaging (FR-18) | `manifest.json` | AD-1, Stack |

---

## Deferred

| Item | Deferred Reason | Revisit Condition |
| --- | --- | --- |
| Direct Bluetooth Hardware Pairing | Ingestion relies on Garmin Cloud API via `python-garminconnect`. Direct BT pairing is complex and unnecessary for daily health summaries. | User explicitly requests local offline BLE watch syncing in v2. |
| Multi-Account Profile Switching | Single Garmin user profile per integration entry in v1 simplifies token storage and entity naming. | User requests multiple Garmin accounts on a single Home Assistant instance. |
