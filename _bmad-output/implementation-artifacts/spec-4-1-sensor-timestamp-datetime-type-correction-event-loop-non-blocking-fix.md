---
title: 'Sensor Timestamp Datetime Type Correction & Event Loop Non-Blocking Fix'
type: 'bugfix'
created: '2026-08-16'
status: 'done'
context:
  - 'custom_components/garmin_ha_ai/sensor.py'
  - 'custom_components/garmin_ha_ai/coordinator.py'
  - 'custom_components/garmin_ha_ai/ai_engine/gemini.py'
  - 'custom_components/garmin_ha_ai/ai_engine/__init__.py'
---

## Intent

**Problem:**
1. In `sensor.py`, `GarminAILastUpdateSensor` has `_attr_device_class = SensorDeviceClass.TIMESTAMP`, but its `native_value` returns an ISO formatted string (`str`) from `coordinator.last_update_time`. Home Assistant's sensor platform expects a `datetime.datetime` object with timezone (`tzinfo`) for timestamp sensors, causing `ValueError: Invalid datetime: ... resulting in 'str' object has no attribute 'tzinfo'`.
2. When `GeminiProvider` is initialized, `genai.Client(api_key=api_key)` performs synchronous SSL certificate loading (`load_verify_locations`) directly on the event loop, causing `Detected blocking call to load_verify_locations ... inside the event loop`.

**Approach:**
1. Update `coordinator.py` so `self.last_update_time` is stored as a `datetime.datetime` object (via `dt_util.now()`). In `sensor.py`, ensure `GarminAILastUpdateSensor.native_value` returns `datetime.datetime | None`, using `dt_util.parse_datetime` if a string is encountered.
2. In `ai_engine/gemini.py`, instantiate `genai.Client` asynchronously off the event loop or within `hass.async_add_executor_job` so synchronous SSL/file discovery does not block Home Assistant's event loop.
3. Add unit test coverage in `tests/test_sensor.py` and `tests/test_ai_engine.py`.

## Tasks & Acceptance

- [x] Update `coordinator.py` to store `last_update_time` as a `datetime.datetime` object with timezone.
- [x] Update `sensor.py` `GarminAILastUpdateSensor.native_value` to guarantee a `datetime.datetime` return value.
- [x] Update `ai_engine/gemini.py` to ensure `genai.Client` is created off the event loop via executor.
- [x] Add unit tests verifying `GarminAILastUpdateSensor.native_value` is a `datetime.datetime` with `tzinfo`.
