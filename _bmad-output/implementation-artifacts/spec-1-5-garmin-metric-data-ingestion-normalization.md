---
title: 'Story 1.5: Garmin Metric Data Ingestion & Normalization'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '5852d9c19a0c92474b1c7457b4b3860f2df9a63d'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Raw Garmin API response payloads vary in structure, contain missing or null keys, and need to be normalized into a typed dataclass so that downstream Home Assistant sensor entities, history storage, and AI analysis receive consistent metric data.

**Approach:** Implement `GarminDailyMetrics` dataclass in `custom_components/garmin_ha_ai/models.py` (or `garmin_client.py`) and add `async_fetch_daily_metrics` method to `GarminClient` that ingests daily stats (steps, distance_km, calories, resting HR, stress, sleep score, HRV status, body battery min/max, weight_kg, and activities) safely using `hass.async_add_executor_job`.

## Boundaries & Constraints

**Always:** Support missing or null fields gracefully without crashing. Return typed `GarminDailyMetrics` instances. Execute synchronous `garminconnect` API requests inside executor jobs. Sanitize log outputs.

**Ask First:** Modifying key metric dataclass field names.

**Never:** Block the main event loop during API calls. Store raw un-sanitized API payloads in Home Assistant state.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Complete Daily Payload | Valid date, all API fields populated | `GarminDailyMetrics` with all fields set | N/A |
| Partial / Missing Fields | Missing sleep or weight data | `GarminDailyMetrics` with missing fields set to `None` | Default gracefully without raising KeyError |
| API Transport Error | Network timeout during metric fetch | Re-raises `GarminConnectConnectionError` | Handled by coordinator retry engine |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/models.py` -- Define `GarminDailyMetrics` dataclass with type hints and helper `to_dict()` serialization.
- `custom_components/garmin_ha_ai/garmin_client.py` -- Add `async_fetch_daily_metrics(target_date)` method.
- `tests/test_garmin_client.py` -- Extend unit tests to verify daily metric ingestion and payload normalization.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/models.py` -- Create dataclasses for `GarminDailyMetrics`.
- [x] `custom_components/garmin_ha_ai/garmin_client.py` -- Add `async_fetch_daily_metrics` method wrapped in executor job.
- [x] `tests/test_garmin_client.py` -- Add unit tests verifying complete and partial payload normalization.

**Acceptance Criteria:**
- Given an authenticated Garmin Connect session
- When daily metrics are fetched for a target date
- Then the client extracts steps, distance (km), total calories, resting heart rate, average stress score, sleep score, HRV status, body battery (min/max), weight (kg), and logged activities into a structured `GarminDailyMetrics` dataclass instance

## Verification

**Commands:**
- `python3 -m py_compile custom_components/garmin_ha_ai/models.py` -- expected: Compilation succeeds with exit code 0
- `PYTHONPATH=. uv run pytest tests/` -- expected: All unit tests pass with exit code 0

**Manual checks (if no CLI):**
- Verify `GarminDailyMetrics` handles missing payload fields gracefully.

## Suggested Review Order

**Garmin Data Models**

- Strongly-typed `GarminDailyMetrics` dataclass definition with dict serialization.
  [`models.py:1`](../../custom_components/garmin_ha_ai/models.py#L1)

**Daily Metrics Ingestion Method**

- `async_fetch_daily_metrics` method in `GarminClient` normalizing daily API data.
  [`garmin_client.py:110`](../../custom_components/garmin_ha_ai/garmin_client.py#L110)

**Unit Test Suite**

- Unit tests verifying normalization of daily stats and activities.
  [`test_garmin_client.py:196`](../../tests/test_garmin_client.py#L196)
