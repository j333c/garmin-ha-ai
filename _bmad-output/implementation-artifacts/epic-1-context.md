# Epic 1 Context: Integration Setup, Garmin Auth & Health Metric Ingestion Foundation

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

User can configure the `garmin-ha-ai` integration via Home Assistant UI Config Flow (Garmin credentials, 120s MFA callback, AI provider selection, and initial goals), authenticate securely with Garmin Connect, persist OAuth tokens and daily metric history snapshots locally in `.storage/` via `storage.py` guarded by `asyncio.Lock()`, handle auth failures gracefully via `ConfigEntryAuthFailed` and native `async_step_reauth`, and fetch daily health metrics onto native Home Assistant sensor entities (`sensor.garmin_steps`, `sensor.garmin_sleep_score`, etc.) with rate-limit and offline resilience.

## Stories

- Story 1.1: Custom Component Package Scaffolding & Manifest Setup
- Story 1.2: Local Storage & Token Persistence Helper (`storage.py`)
- Story 1.3: Garmin Client Authentication Adapter & Token Lifecycle (`garmin_client.py`)
- Story 1.4: UI Config Flow & MFA Setup Wizard (`config_flow.py`)
- Story 1.5: Garmin Metric Data Ingestion & Normalization
- Story 1.6: DataUpdateCoordinator & Scheduled Polling Engine (`coordinator.py`)
- Story 1.7: Native Garmin Metric Sensor Entities (`sensor.py`)

## Requirements & Constraints

- Credentials, tokens, and metric history must be stored exclusively on local Home Assistant storage (`.storage/`). Plaintext passwords must never be stored in persistent storage or memory after setup.
- All disk I/O operations in local storage must be guarded by `asyncio.Lock()` to prevent concurrent read/write corruption.
- Silent OAuth token refresh using refresh tokens must be attempted before falling back to full re-authentication.
- Authentication failures (password change/token expiry) must raise `ConfigEntryAuthFailed` to trigger HA native `async_step_reauth`.
- UI Config Flow must handle 120-second MFA passcode countdown with retry options.
- Data ingestion must handle Garmin API rate limits and network offline states gracefully by preserving previous cached metric states and logging warnings.
- Home Assistant main event loop must remain non-blocking; all network and disk I/O operations must use async/executor wrappers.

## Technical Decisions

- Package directory structure under `custom_components/garmin_ha_ai/` (`__init__.py`, `config_flow.py`, `coordinator.py`, `garmin_client.py`, `storage.py`, `sensor.py`, `const.py`).
- Dependencies: `garminconnect>=0.3.10`, `google-genai>=1.0.0`, `httpx>=0.27.0`.
- Store tokens in `.storage/garmin_ha_ai_tokens.json` and history in `.storage/garmin_ha_ai_history.json` using `homeassistant.helpers.storage.Store`.
- Dataclass `GarminDailyMetrics` normalizes daily metrics (steps, distance, calories, RHR, stress, sleep score, HRV, body battery min/max, weight, workouts).
- `GarminDataUpdateCoordinator` handles scheduled background polling (default 06:00 AM daily or periodic interval).

## Cross-Story Dependencies

- Story 1.1 provides the manifest and `const.py` constants used by all subsequent stories.
- Story 1.2 (`storage.py`) is required by Story 1.3 (`garmin_client.py`) for persisting tokens and Story 1.6 (`coordinator.py`) for storing daily metrics.
- Story 1.3 (`garmin_client.py`) is required by Story 1.4 (`config_flow.py`) and Story 1.5/1.6 (`coordinator.py`).
- Story 1.5 (`GarminDailyMetrics`) is required by Story 1.6 (`coordinator.py`).
- Story 1.6 (`coordinator.py`) is required by Story 1.7 (`sensor.py`).

### Review Findings

- [x] [Review][Patch] Implement `GarminStorage.async_save_daily_metrics` to merge daily snapshots into historical store [`custom_components/garmin_ha_ai/storage.py:80`]
- [x] [Review][Patch] Allow `GarminConnectMfaRequired` and `GarminConnectConnectionError` to propagate in `GarminClient.async_login_with_credentials` [`custom_components/garmin_ha_ai/garmin_client.py:82`]
- [x] [Review][Patch] Re-raise connection and authentication exceptions in `GarminClient._fetch_sync` instead of swallowing into null metrics [`custom_components/garmin_ha_ai/garmin_client.py:134`]
- [x] [Review][Patch] Add MFA challenge handling in `config_flow.py` `async_step_reauth_confirm` [`custom_components/garmin_ha_ai/config_flow.py:149`]
- [x] [Review][Patch] Add `SensorStateClass`, `SensorDeviceClass`, and `device_info` to `GarminSensorEntity` [`custom_components/garmin_ha_ai/sensor.py:25`]
- [x] [Review][Patch] Guard `metrics.activities is None` in steps sensor attributes [`custom_components/garmin_ha_ai/sensor.py:118`]
- [x] [Review][Patch] Add automated history retention pruning during coordinator polling cycle [`custom_components/garmin_ha_ai/coordinator.py:60`]
- [x] [Review][Patch] Add test coverage for reauth flow, partial metric payloads, and component setup/unload lifecycle [`tests/test_config_flow.py:140`]


