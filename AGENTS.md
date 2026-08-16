<!-- bmad:context -->
<!-- Verified 2026-08-16 against 7ba7e56. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## garmin-ha-ai

Home Assistant custom component integration for Garmin Connect health data and AI analysis. Python 3.12+, Home Assistant Custom Component integration structure. Specifications live in `_bmad-output/specs/spec-garmin-ha-ai/SPEC.md`, architecture in `_bmad-output/planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/ARCHITECTURE-SPINE.md`.

## Policy

- Never log Garmin credentials, MFA tokens, or raw user health payload data — sanitize all logs.
- Never make blocking synchronous network or I/O calls in the main event loop — use Home Assistant async executor wrappers (`hass.async_add_executor_job`).

## Where things are

- Component lifecycle & services: `custom_components/garmin_ha_ai/__init__.py`, `services.py`, `services.yaml`
- Configuration & options flows: `custom_components/garmin_ha_ai/config_flow.py`, `options_flow.py`
- Polling coordinator & sensors: `custom_components/garmin_ha_ai/coordinator.py`, `sensor.py`
- AI Engine drivers & prompt assembler: `custom_components/garmin_ha_ai/ai_engine/`
- Local storage & Garmin adapter: `custom_components/garmin_ha_ai/storage.py`, `garmin_client.py`
- Unit, contract & E2E tests: `tests/` (`tests/api/`, `tests/e2e/`)

## Running and verifying

- Run `pytest` to execute all 93 unit, API contract, and E2E lifecycle tests.

## Conventions that differ from defaults

- Store long AI response narratives in entity extra state attributes; Home Assistant entity state strings strictly truncate after 255 characters (enforce <=250 chars).
- Access local storage via Home Assistant `Store` helper (`homeassistant.helpers.storage.Store`); never perform raw file I/O directly.
- Ground AI context in local rolling history (`garmin_ha_ai_history.json`) via `GarminStorage` rather than making repeated cloud requests to Garmin Connect.

## Known pitfalls

- Handle Garmin MFA authentication gracefully via reauth flow; session tokens periodically expire requiring user re-authentication.
- AI provider HTTP 429 quota exhaustion or timeouts must raise integration-level exceptions (`AIEngineQuotaError`, `AIEngineTimeoutError`) without crashing the coordinator polling engine.

<!-- /bmad:context -->
