---
title: 'Story 1.7: Native Garmin Metric Sensor Entities (sensor.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '78d234045148c24493c2ac299379a3164790c50f'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Standard Home Assistant dashboards need native `SensorEntity` instances for Garmin daily metrics (steps, resting HR, sleep score, stress level, weight, body battery) configured with appropriate units of measurement, device classes, and state classes.

**Approach:** Implement `custom_components/garmin_ha_ai/sensor.py` providing `GarminSensorEntity` extending `CoordinatorEntity` and `SensorEntity`. Update `__init__.py` to manage `async_setup_entry` loading the sensor platform.

## Boundaries & Constraints

**Always:** Inherit from `CoordinatorEntity` to auto-receive updates from `GarminDataUpdateCoordinator`. Use `SensorEntityDescription` for sensor definitions. Assign standard unit strings (e.g., `bpm`, `kg`, `steps`, `%`). Keep state strings within standard limits.

**Ask First:** Adding new un-scoped sensor types.

**Never:** Raise unhandled exceptions inside entity `native_value` getters. Access storage directly from entity getters.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Metric Updated | Coordinator data contains fresh metrics | Entities update `native_value` and attributes | Return `None` if metric value is `None` |
| Coordinator Unavailable | Coordinator update failed | Entities mark state as unavailable | Handled by `CoordinatorEntity` base class |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/sensor.py` -- Sensor platform implementation and `GarminSensorEntity`.
- `custom_components/garmin_ha_ai/__init__.py` -- Component setup loading sensor platform.
- `tests/test_sensor.py` -- Unit tests for sensor initialization and state updates.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/sensor.py` -- Implement sensor platform and entity classes.
- [x] `custom_components/garmin_ha_ai/__init__.py` -- Wire entry setup (`async_setup_entry` and `async_unload_entry`).
- [x] `tests/test_sensor.py` -- Add unit tests for sensor setup and entity state rendering.

**Acceptance Criteria:**
- Given a running `garmin_ha_ai` integration
- When coordinator metrics update
- Then entities `sensor.garmin_steps`, `sensor.garmin_resting_hr`, `sensor.garmin_sleep_score`, `sensor.garmin_stress_level`, `sensor.garmin_weight`, and `sensor.garmin_body_battery` update their states and attributes in the HA Entity Registry

## Verification

**Commands:**
- `python3 -m py_compile custom_components/garmin_ha_ai/sensor.py` -- expected: Compilation succeeds with exit code 0
- `PYTHONPATH=. uv run pytest tests/` -- expected: All unit tests pass with exit code 0

**Manual checks (if no CLI):**
- Verify sensor entities reflect coordinator metric values correctly.

## Suggested Review Order

**Sensor Platform & Entities**

- Garmin metric sensor definitions and `GarminSensorEntity` implementation.
  [`sensor.py:1`](../../custom_components/garmin_ha_ai/sensor.py#L1)

**Integration Entry Setup Wiring**

- `async_setup_entry` setup of storage, client, coordinator, and sensor platform.
  [`__init__.py:17`](../../custom_components/garmin_ha_ai/__init__.py#L17)

**Unit Test Suite**

- Unit tests for sensor registration, state attributes, and null handling.
  [`test_sensor.py:14`](../../tests/test_sensor.py#L14)
