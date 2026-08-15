# Epic 2 Context: Automated AI Coaching Reports & Multi-Channel Delivery

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Provide daily automated and manually triggered AI health briefings using either Google Gemini (`google-genai` SDK) or generic OpenAI-compatible APIs (`httpx` async client). Reports are synthesized from daily health metrics, 7-day local history, personal goals, and coaching directives. Concise summaries populate Home Assistant report sensors (`sensor.garmin_ai_health_report_short` strictly truncated to <255 chars, `sensor.garmin_ai_health_report_long` with full Markdown in extra attributes) and dispatch to configured notification channels (push, persistent, email) with fault isolation and debouncing.

## Stories

- Story 2.1: Pluggable AI Engine Drivers (Gemini SDK & Generic OpenAI HTTPX)
- Story 2.2: 5-Block Prompt Context Assembler (`prompt.py`)
- Story 2.3: AI Health Report Sensor Entities & 255-Char Protection (`sensor.py`)
- Story 2.4: Scheduled Report Orchestration & Debounced Trigger Service (`coordinator.py`)
- Story 2.5: Multi-Channel Fault-Tolerant Notification Dispatch

## Requirements & Constraints

- **Primary AI Provider (Gemini)**: Support Google Gemini API using official `google-genai` SDK with configured API key (default model: `gemini-2.0-flash`).
- **Generic OpenAI Provider**: Support OpenAI-compatible API endpoints using `httpx` async client with custom Base URL, API Key, and Model ID.
- **5-Block Prompt Assembly**: Payload includes (1) current day metrics, (2) 7-day metric history/trends from local store, (3) user goals, (4) persona directives, and (5) output structure rules. Automatically truncate prompt context if token limit thresholds are reached.
- **Error Handling & Retries**: Timeout or 5xx HTTP/API errors trigger up to 2 retries with exponential backoff before marking report state as error.
- **Entity State Length Protection (AD-5)**: Home Assistant state strings hard-truncate after 255 characters. `sensor.garmin_ai_health_report_short` state MUST be strictly truncated in Python (`[:250] + "..."`) to prevent `InvalidStateError`. `sensor.garmin_ai_health_report_long` state displays a short header while its `extra_state_attributes["full_report"]` carries the full Markdown report text.
- **Integration Status Sensor**: Maintain `sensor.garmin_ai_last_update` timestamp showing last successful Garmin sync and AI report generation.
- **Debounced Generation (AD-7)**: Maintain an in-flight `_is_generating` boolean lock in `coordinator.py` to prevent redundant concurrent report generation from rapid manual UI trigger button clicks.
- **Fault-Tolerant Notification Dispatch (AD-7)**: Dispatch generated reports to configured notification targets (e.g. `notify.mobile_app_phone`, persistent notification, email). Catch `ServiceNotFound` and `HomeAssistantError` as logged warnings without breaking entity state updates.
- **Non-Blocking Main Event Loop**: No synchronous network or file I/O operations inside HA main event loop.

## Technical Decisions

- **Dual Native Driver AI Engine (AD-3)**: Lightweight native drivers in `custom_components/garmin_ha_ai/ai_engine/`:
  - `base.py` (`BaseAIProvider` abstract protocol interface)
  - `gemini.py` (`GeminiProvider` using `google-genai`)
  - `openai.py` (`OpenAIProvider` using `httpx.AsyncClient` targeting `/v1/chat/completions` with default 30s timeout)
  - `prompt.py` (5-block prompt assembler and context estimator/truncator)
- **Data Models**:
  - `AIHealthReport`: dataclass with `timestamp: str`, `short_summary: str`, `full_report: str`, `provider_used: str`, `model_used: str`.
- **Sanitizing Logs**: Never log API keys, credentials, or raw health payload dumps in system logs.

## Cross-Story Dependencies

- Story 2.1 provides the base provider drivers (`GeminiProvider`, `OpenAIProvider`) used by `coordinator.py` and service triggers in later stories.
- Story 2.2 builds `prompt.py` which consumes `GarminDailyMetrics` (from Epic 1) and local history snapshot JSON (from `storage.py`).
- Story 2.3 creates the sensor entities (`sensor.py`) updated by `coordinator.py` in Story 2.4.
- Story 2.4 ties data ingestion to report generation in `coordinator.py`.
- Story 2.5 integrates notification dispatch into the `coordinator.py` report generation workflow.
