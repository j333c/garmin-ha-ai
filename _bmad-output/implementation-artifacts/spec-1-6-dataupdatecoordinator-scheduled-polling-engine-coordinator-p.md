---
title: 'Story 1.6: DataUpdateCoordinator & Scheduled Polling Engine (coordinator.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '47a6b2e6dc5e89f4a2ec9fdb6e11905cf12b4897'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Home Assistant entity state updates must be synchronized through a centralized `DataUpdateCoordinator` that manages polling schedules, persists daily snapshots into local storage (`garmin_ha_ai_history.json`), and handles network glitches and rate-limits gracefully without crashing.

**Approach:** Implement `GarminDataUpdateCoordinator` in `custom_components/garmin_ha_ai/coordinator.py` extending `DataUpdateCoordinator[GarminDailyMetrics]`. It uses `GarminClient.async_fetch_daily_metrics` to ingest data and updates `GarminStorage` history on each poll cycle.

## Boundaries & Constraints

**Always:** Inherit from `homeassistant.helpers.update_coordinator.DataUpdateCoordinator`. Raise `UpdateFailed` on network or API failures to retain previous entity states. Raise `ConfigEntryAuthFailed` on authentication expiration. Save daily metric snapshots to local history storage.

**Ask First:** Changing update interval defaults or storage retention limits.

**Never:** Store raw credentials or tokens in entity states or coordinator logs. Allow unhandled network exceptions to crash Home Assistant.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Scheduled Poll Success | Timer fires or manual refresh requested | Fetches daily metrics, saves to history, updates entities | Log debug summary |
| Network Outage / Rate Limit | Connection error during fetch | Previous sensor states preserved | Raise `UpdateFailed`, log warning |
| Session Expired | Auth error from Garmin | Triggers re-authentication flow | Raise `ConfigEntryAuthFailed` |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/coordinator.py` -- Implementation of `GarminDataUpdateCoordinator`.
- `custom_components/garmin_ha_ai/garmin_client.py` -- Provides `async_fetch_daily_metrics`.
- `custom_components/garmin_ha_ai/storage.py` -- Provides `async_save_daily_metrics`.
- `tests/test_coordinator.py` -- Unit tests for polling, storage persistence, and failure recovery.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/coordinator.py` -- Create `GarminDataUpdateCoordinator` class.
- [x] `tests/test_coordinator.py` -- Create unit tests verifying scheduled polling, storage save, and error handling.

**Acceptance Criteria:**
- Given a configured integration entry
- When the scheduled polling timer fires
- Then `coordinator.py` executes data ingestion, saves daily metric snapshots into `.storage/garmin_ha_ai_history.json`, and updates entity states
- And if a network outage or Garmin rate-limit occurs, previous sensor states remain available with logged warnings without crashing Home Assistant Core

## Verification

**Commands:**
- `python3 -m py_compile custom_components/garmin_ha_ai/coordinator.py` -- expected: Compilation succeeds with exit code 0
- `PYTHONPATH=. uv run pytest tests/` -- expected: All unit tests pass with exit code 0

**Manual checks (if no CLI):**
- Verify coordinator gracefully wraps connection errors with `UpdateFailed`.

## Suggested Review Order

**Garmin DataUpdateCoordinator**

- `GarminDataUpdateCoordinator` managing background polling and storage snapshots.
  [`coordinator.py:27`](../../custom_components/garmin_ha_ai/coordinator.py#L27)

**Unit Test Suite**

- Unit tests for coordinator update cycle, storage persistence, and failure recovery.
  [`test_coordinator.py:14`](../../tests/test_coordinator.py#L14)
