---
title: 'Multi-Channel Fault-Tolerant Notification Dispatch'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: 'c4a3c60f1691ac7e26c6e1e4eedf615cd7c9587b'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/coordinator.py'
  - 'custom_components/garmin_ha_ai/const.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Home Assistant users want freshly generated AI health reports automatically dispatched to their configured notification channels (e.g., HA mobile app `notify.mobile_app_phone` or HA persistent notification). If a notification target is misconfigured or fails (e.g. `ServiceNotFound`), the failure must not crash or prevent sensor state updates.

**Approach:**
1. Implement `async_dispatch_notification(self, report: AIHealthReport) -> None` in `GarminDataUpdateCoordinator`.
2. Read target configuration from `self.entry.options` / `self.entry.data` using `CONF_NOTIFICATION_TARGETS` (or `CONF_NOTIFICATION_TARGET`).
3. Support target types:
   - `"persistent_notification"`: Calls `persistent_notification.create` service.
   - Target formatted as `notify.<service_name>` (e.g. `notify.mobile_app_phone`): Extracts domain `notify` and service `mobile_app_phone` and calls `hass.services.async_call`.
4. Wrap notification service calls in `try...except (ServiceNotFound, HomeAssistantError, Exception) as err:` block: log a warning on error and continue gracefully without raising.
5. Invoke `async_dispatch_notification` inside `async_generate_report` after report generation completes.

## Boundaries & Constraints

**Always:**
- Catch all `ServiceNotFound`, `HomeAssistantError`, or unexpected exceptions during notification dispatch and log a warning.
- Ensure sensor state updates and `latest_report` updates succeed regardless of notification delivery status.
- Support `persistent_notification` and dynamic `notify.<service>` targets.
- Log dispatch status at `LOGGER.info` when notification succeeds.

**Ask First:**
- Modifying default notification title or template structure.

**Never:**
- Allow a notification failure to raise an exception or abort report generation.
- Attempt to dispatch notifications if no target is configured (empty string or empty list).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Persistent Notification | Target: `"persistent_notification"` | Calls `persistent_notification.create` with report text | Log success |
| Mobile App Target | Target: `"notify.mobile_app_phone"` | Calls `notify.mobile_app_phone` service with short & long summary | Log success |
| Invalid Service Target | Target: `"notify.non_existent_target"` | `ServiceNotFound` raised during dispatch | Warning logged, sensor state remains updated |
| Notification Disabled | Target: `""` or `None` | Dispatch skipped immediately | No service call attempted |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/coordinator.py` -- Implementation of `async_dispatch_notification()` and integration into `async_generate_report()`.
- `custom_components/garmin_ha_ai/const.py` -- `CONF_NOTIFICATION_TARGETS` configuration key.
- `tests/test_coordinator.py` -- Unit tests for notification dispatch, target parsing, fault tolerance on `ServiceNotFound`, and disabled notification handling.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/coordinator.py` -- Implement `async_dispatch_notification()` method supporting `persistent_notification` and `notify.<service>` targets with `try...except` fault tolerance.
- [x] `tests/test_coordinator.py` -- Write unit tests for notification dispatch success, `ServiceNotFound` handling, and target parsing.

**Acceptance Criteria:**
- Given a valid report and target `"notify.mobile_app_phone"`, notification service is called with report summary.
- Given an invalid notification target raising `ServiceNotFound`, a warning is logged while report sensors update normally.
- Given empty target configuration, notification dispatch is safely skipped.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. pytest tests/test_coordinator.py` -- expected: 100% pass on coordinator unit tests.
- `PYTHONPATH=. pytest` -- expected: 100% pass on all integration tests.

## Suggested Review Order

**Fault-Tolerant Notification Dispatch Logic**

- `async_dispatch_notification` method with `persistent_notification` and `notify.<service>` targets plus `try...except` fault tolerance
  [`coordinator.py:67`](../../custom_components/garmin_ha_ai/coordinator.py#L67)

- Notification dispatch invocation inside `async_generate_report`
  [`coordinator.py:151`](../../custom_components/garmin_ha_ai/coordinator.py#L151)

**Unit Tests**

- Unit test suite for notification dispatch targets, empty target skipping, and `ServiceNotFound` fault tolerance
  [`test_coordinator.py:184`](../../tests/test_coordinator.py#L184)

