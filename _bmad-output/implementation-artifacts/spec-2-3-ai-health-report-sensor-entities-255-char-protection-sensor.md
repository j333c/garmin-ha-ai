---
title: 'AI Health Report Sensor Entities & 255-Char Protection (sensor.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: 'cc959bca1bff8bfb0486c4f82418238374b08598'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/models.py'
  - 'custom_components/garmin_ha_ai/sensor.py'
  - 'custom_components/garmin_ha_ai/coordinator.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Home Assistant entity `state` strings have a hard 255-character limit in HA Core database schema. Storing long AI markdown reports in an entity's `state` string triggers an unrecoverable `InvalidStateError`. Users need a short dashboard summary entity (`sensor.garmin_ai_health_report_short`) and a full report entity (`sensor.garmin_ai_health_report_long`) with state length protection.

**Approach:** Implement `GarminAIHealthReportShortSensor` and `GarminAIHealthReportLongSensor` entities in `custom_components/garmin_ha_ai/sensor.py`:
1. **Short Report Sensor (`sensor.garmin_ai_health_report_short`)**: Native value displays `short_summary` from `AIHealthReport`. Enforce strict python string truncation (`val[:247] + "..."` if `len(val) > 250`) to guarantee `native_value` stays strictly < 255 characters.
2. **Long Report Sensor (`sensor.garmin_ai_health_report_long`)**: Native value displays a brief status header (e.g. `"Report generated (2026-08-15)"`), while `extra_state_attributes["full_report"]` carries the complete rich Markdown report string.
3. Update `async_setup_entry` to register report entities.

## Boundaries & Constraints

**Always:**
- Strictly truncate `sensor.garmin_ai_health_report_short` native_value to a maximum of 250 characters (`val[:247] + "..."` if over 250 chars).
- Store full rich Markdown report text in `sensor.garmin_ai_health_report_long`'s `extra_state_attributes["full_report"]`.
- Return `"No report generated yet"` or `None` if no `AIHealthReport` object is present in coordinator data.
- Include `timestamp`, `provider_used`, and `model_used` in `extra_state_attributes`.

**Ask First:**
- Modifying character truncation threshold (default: 250 characters).

**Never:**
- Allow `sensor.garmin_ai_health_report_short` or `sensor.garmin_ai_health_report_long` state string to exceed 255 characters.
- Fail setup if report data is initially empty.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Report Available | Valid `AIHealthReport` object | Short sensor state = truncated summary (<250 chars); Long sensor `full_report` attr = full Markdown | N/A |
| Summary Exceeds 255 Chars | `short_summary` is 400 characters long | Short sensor `native_value` is truncated to 247 chars + `"..."` (total 250 chars) | No `InvalidStateError` raised |
| No Report Object | `coordinator.latest_report = None` | Sensor states display `"No report generated yet"` or `None` | No exception raised |
| Empty Summary String | `short_summary=""` | Short sensor state displays `"No summary available"` | No exception raised |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/models.py` -- `AIHealthReport` dataclass definition.
- `custom_components/garmin_ha_ai/sensor.py` -- Sensor platform setup, `GarminAIHealthReportShortSensor`, and `GarminAIHealthReportLongSensor`.
- `custom_components/garmin_ha_ai/coordinator.py` -- Data coordinator storing `latest_report: AIHealthReport | None`.
- `tests/test_sensor.py` -- Unit tests for short and long report sensors and 255-character truncation verification.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/coordinator.py` -- Ensure coordinator exposes `latest_report` attribute.
- [x] `custom_components/garmin_ha_ai/sensor.py` -- Implement `GarminAIHealthReportShortSensor` with strict 250-char truncation and `GarminAIHealthReportLongSensor` with `full_report` in `extra_state_attributes`. Update `async_setup_entry`.
- [x] `tests/test_sensor.py` -- Write unit tests verifying report sensor states, attributes, fallback for missing reports, and strict 250-character truncation protection.

**Acceptance Criteria:**
- Given a long `AIHealthReport` summary (>255 chars), `sensor.garmin_ai_health_report_short` native value is truncated to <= 250 chars.
- Given an `AIHealthReport` object, `sensor.garmin_ai_health_report_long` native value displays a brief status line, and `extra_state_attributes["full_report"]` contains the full report Markdown.
- Given no report generated yet, both report sensors handle `None` gracefully without crashing.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. pytest tests/test_sensor.py` -- expected: 100% pass on all sensor entity unit tests.
- `PYTHONPATH=. pytest` -- expected: 100% pass on all integration tests.

## Suggested Review Order

**Coordinator Data Structure**

- Expose `latest_report` on `GarminDataUpdateCoordinator`
  [`coordinator.py:37`](../../custom_components/garmin_ha_ai/coordinator.py#L37)

**AI Report Sensors**

- Short report sensor (`GarminAIHealthReportShortSensor`) with hard 250-character truncation protection
  [`sensor.py:121`](../../custom_components/garmin_ha_ai/sensor.py#L121)

- Long report sensor (`GarminAIHealthReportLongSensor`) with `full_report` Markdown in `extra_state_attributes`
  [`sensor.py:169`](../../custom_components/garmin_ha_ai/sensor.py#L169)

**Unit Tests**

- Sensor entity unit test suite validating 8 registered entities, attributes, and 255-character state protection
  [`test_sensor.py:81`](../../tests/test_sensor.py#L81)

