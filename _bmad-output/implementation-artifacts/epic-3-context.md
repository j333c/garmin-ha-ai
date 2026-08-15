# Epic 3 Context: Interactive Health Q&A & Local History Management

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Enable users to ask context-grounded health and fitness questions on demand via service `garmin_ha_ai.ask_question` or interactive Lovelace Q&A cards. The Q&A system grounds responses using locally cached 30-day historical metrics (`.storage/garmin_ha_ai_history.json` guarded by `asyncio.Lock()`) without making live Garmin cloud calls. Additionally, provide a dynamic UI Options Flow (`options_flow.py`) to manage goals, AI directives, sync schedules, and historical retention windows post-installation.

## Stories

- Story 3.1: Interactive Q&A Service Registration & History Grounding (`services.py`)
- Story 3.2: Last Answer Sensor Entity & Interactive Lovelace Q&A Card Pattern
- Story 3.3: UI Options Flow & Retention Window Management (`options_flow.py`)

## Requirements & Constraints

- **FR-14 / Service Contract**: Register service `garmin_ha_ai.ask_question` accepting `question` (string, required), `days_history` (integer, default 7), and optional `response_entity`. Must return `{"answer": "...", "question": "..."}` directly with `SupportsResponse.OPTIONAL` and update target sensor entity state.
- **FR-15 / History Grounding**: Fetch up to N days of cached metrics from local `.storage/garmin_ha_ai_history.json` (guarded by `asyncio.Lock()`), clamp `days_history` to available history length, and format into prompt context before calling AI driver.
- **FR-17 / Post-Setup Reconfiguration**: Provide Options Flow (`options_flow.py`) for updating target weight, workout targets, coaching directives, sync schedules, notification targets, and retention window (`retention_days`: 7-90 days, default 30). Saving options must trigger pruning of stored historical snapshots.
- **NFR-3 / Latency Target**: Q&A service execution must complete and return response data within < 10 seconds.
- **NFR-6 & NFR-7 / Privacy & Async Enforcement**: No live Garmin cloud network calls during Q&A. All storage and AI engine calls must be fully async.

## Technical Decisions

- **Service Registration**: Services defined and registered in `custom_components/garmin_ha_ai/services.py` during integration setup (`async_setup_entry`).
- **Storage Access**: Read historical metric snapshots via `GarminStorage` helper (`storage.py`) using `asyncio.Lock()` to prevent race conditions. Gracefully handle missing or empty history files.
- **AI Driver Reuse**: Obtain configured AI Engine instance (`GeminiProvider` or `OpenAIProvider`) from entry runtime data (`hass.data[DOMAIN][entry_id]`).
- **State Protection**: When updating `sensor.garmin_ai_last_answer`, state string contains brief status/summary (<255 chars) while complete response text is stored in `extra_state_attributes["full_answer"]`.

## UX & Interaction Patterns

- **Interactive Q&A Card**: Dashboard card pattern using `paper-input` text field and "Ask Coach" submit button invoking `garmin_ha_ai.ask_question`.
- **Options Flow UI**: Standard Home Assistant Options Flow wizard accessible via Settings -> Devices & Services -> Configure.

## Cross-Story Dependencies

- **Story 3.1 -> Story 3.2**: Backend service `garmin_ha_ai.ask_question` must exist before dashboard Q&A card interactions can be finalized.
- **Story 3.1 & 3.3 -> Local Storage**: Both Q&A history grounding and retention window pruning rely on `GarminStorage` (`storage.py`).
