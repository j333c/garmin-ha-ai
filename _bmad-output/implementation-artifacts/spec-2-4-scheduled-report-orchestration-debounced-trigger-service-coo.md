---
title: 'Scheduled Report Orchestration & Debounced Trigger Service (coordinator.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: 'c37d0c6c3175d7c96fc324c0b2cd724c1d6eccb3'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/coordinator.py'
  - 'custom_components/garmin_ha_ai/ai_engine/__init__.py'
  - 'custom_components/garmin_ha_ai/ai_engine/prompt.py'
  - 'custom_components/garmin_ha_ai/__init__.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Users need both automated scheduled AI health reports generated after daily Garmin syncs and manual on-demand triggers via Home Assistant service `garmin_ha_ai.generate_report`. Without debouncing protection, rapid manual button clicks or concurrent triggers could spawn duplicate AI requests, consuming rate limits and corrupting entity state updates.

**Approach:** 
1. Implement `async_generate_report(self, force: bool = False)` in `GarminDataUpdateCoordinator`. Protect execution with an internal boolean flag `self._is_generating`. If `_is_generating` is True, log a warning and return early (`None`).
2. Data gathering & assembly: Load 7-day history from `GarminStorage`, assemble 5-block prompt context using `assemble_report_prompt`, fetch configured AI provider via `get_ai_provider`, and invoke provider `async_generate_report`.
3. Store result in `coordinator.latest_report` and notify HA listeners (`self.async_update_listeners()`).
4. Register Home Assistant service `garmin_ha_ai.generate_report` in `__init__.py` to allow manual execution.
5. Trigger automated report generation inside `coordinator._async_update_data()` following successful Garmin metrics fetch.

## Boundaries & Constraints

**Always:**
- Guard `async_generate_report` with an internal boolean lock (`self._is_generating`) to prevent concurrent duplicate executions.
- Use `try...finally` to guarantee `self._is_generating = False` is reset on method completion or error.
- Catch AI provider errors gracefully in background scheduled cycles so metric sync is never broken by an AI API failure.
- Notify HA entity listeners (`self.async_update_listeners()`) when `latest_report` updates.

**Ask First:**
- Changing default service name `garmin_ha_ai.generate_report`.

**Never:**
- Allow concurrent report generation runs.
- Log sensitive API keys or credentials during AI report orchestration.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single Manual Trigger | Service `garmin_ha_ai.generate_report` called | Report generated, `latest_report` set, sensor state updated | Log success |
| Rapid Concurrent Triggers | Service called twice within 100ms | 1st call runs; 2nd call hits `_is_generating == True` and returns immediately | Warning logged, duplicate run ignored |
| Scheduled Sync Complete | `_async_update_data()` completes | Automatically triggers `async_generate_report()` in background | Logs error if AI fails, metrics remain updated |
| Missing AI API Key | API key unconfigured or empty string | Raises/logs `AIEngineError` gracefully | `latest_report` remains unchanged |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/coordinator.py` -- Implementation of `_is_generating` lock, `async_generate_report()`, and background scheduled trigger in `_async_update_data()`.
- `custom_components/garmin_ha_ai/__init__.py` -- Registration of Home Assistant service `garmin_ha_ai.generate_report`.
- `custom_components/garmin_ha_ai/const.py` -- `SERVICE_GENERATE_REPORT` constant (`"generate_report"`).
- `tests/test_coordinator.py` -- Unit tests for `async_generate_report`, debouncing lock, service call registration, and error handling.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/coordinator.py` -- Implement `_is_generating` lock, `async_generate_report()`, and auto-trigger in `_async_update_data()`.
- [x] `custom_components/garmin_ha_ai/__init__.py` -- Register service `garmin_ha_ai.generate_report` calling coordinator `async_generate_report`.
- [x] `tests/test_coordinator.py` -- Write unit tests for debounced report generation, duplicate trigger prevention, scheduled triggers, and service calls.

**Acceptance Criteria:**
- Given rapid duplicate calls to `async_generate_report`, the `_is_generating` lock rejects concurrent runs and logs a warning.
- Given completion of daily metrics fetch, `coordinator` automatically generates a report.
- Calling service `garmin_ha_ai.generate_report` triggers report generation and updates report sensors.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. pytest tests/test_coordinator.py` -- expected: 100% pass on coordinator unit tests.
- `PYTHONPATH=. pytest` -- expected: 100% pass on all integration tests.

## Suggested Review Order

**Report Generation & Debouncing Logic**

- `async_generate_report` method with `_is_generating` boolean lock and prompt/driver assembly
  [`coordinator.py:50`](../../custom_components/garmin_ha_ai/coordinator.py#L50)

- Background report generation auto-trigger following successful metrics sync
  [`coordinator.py:112`](../../custom_components/garmin_ha_ai/coordinator.py#L112)

**Service Registration**

- Home Assistant service registration for `garmin_ha_ai.generate_report`
  [`__init__.py:16`](../../custom_components/garmin_ha_ai/__init__.py#L16)

**Unit Tests**

- Unit test suite for debounced report generation, duplicate trigger lock, missing API keys, and auto-trigger
  [`test_coordinator.py:87`](../../tests/test_coordinator.py#L87)

