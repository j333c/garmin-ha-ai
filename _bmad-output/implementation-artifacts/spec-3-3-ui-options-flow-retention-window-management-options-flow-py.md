---
title: 'UI Options Flow & Retention Window Management'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '76670dde17d4d32c37d4ab4eeab9731ad597358b'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Users need a way to adjust health goals, AI coaching directives, sync schedules, notification targets, and historical retention windows post-installation without deleting and re-adding the integration.

**Approach:**
1. Implement `GarminHaAiOptionsFlowHandler` in `custom_components/garmin_ha_ai/options_flow.py` and attach `async_get_options_flow` on `GarminHaAiConfigFlow`.
2. Present a dynamic options form supporting `retention_days` (7-90 days, default 30), `fitness_goals`, `coaching_directives`, `notification_targets`, and `polling_schedule`.
3. Upon saving options, invoke `GarminStorage.async_prune_history(retention_days)` to immediately purge historical metric snapshots older than the new retention threshold.
4. Register an options update listener in `__init__.py` to reload the config entry when options are updated.

## Boundaries & Constraints

**Always:**
- Expose Options Flow via `async_get_options_flow` on `GarminHaAiConfigFlow` in `config_flow.py`.
- Validate `retention_days` to stay strictly within 7 to 90 days (`MIN_RETENTION_DAYS` to `MAX_RETENTION_DAYS`).
- Call `async_prune_history(retention_days)` on option submission to trim expired history snapshots immediately.
- Pre-populate form fields with existing `config_entry.options` (falling back to `config_entry.data` or defaults).

**Ask First:**
- Adding mandatory new configuration keys to options flow that break backward compatibility.

**Never:**
- Expose or prompt for Garmin login credentials (username/password) inside the options flow.
- Allow `retention_days` outside the range of 7 to 90 days.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Open Options Form | ConfigEntry loaded | Displays form pre-filled with current or default settings | N/A |
| Save Valid Options | `retention_days=14`, updated `fitness_goals` | Updates `entry.options`, prunes snapshots older than 14 days, returns `create_entry` | N/A |
| Out of Bounds Retention Days | `retention_days=5` or `100` | Schema validation error prevents submission | Voluptuous validation error |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/options_flow.py` -- Implementation of `GarminHaAiOptionsFlowHandler(config_entries.OptionsFlow)` managing options step `init`.
- `custom_components/garmin_ha_ai/config_flow.py` -- Add `async_get_options_flow` staticmethod returning `GarminHaAiOptionsFlowHandler`.
- `custom_components/garmin_ha_ai/__init__.py` -- Add options update listener (`async_reload_entry`) in `async_setup_entry` to reload config entry and prune history when options change.
- `custom_components/garmin_ha_ai/storage.py` -- Reuse `async_prune_history(retention_days)` helper.
- `tests/test_options_flow.py` -- Unit tests for options flow form rendering, submission, schema validation, entry option saving, and history pruning execution.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/options_flow.py` -- Create `GarminHaAiOptionsFlowHandler` managing options step `init` with fields `retention_days`, `fitness_goals`, `coaching_directives`, `notification_targets`, `polling_schedule`, and triggering `async_prune_history` on save.
- [x] `custom_components/garmin_ha_ai/config_flow.py` -- Add `async_get_options_flow` static method to `GarminHaAiConfigFlow`.
- [x] `custom_components/garmin_ha_ai/__init__.py` -- Register options update listener to reload config entry and prune history when options change.
- [x] `tests/test_options_flow.py` -- Write unit tests verifying options flow initialization, schema validation, entry option saving, and history pruning execution.

**Acceptance Criteria:**
- Given an active `garmin_ha_ai` config entry, when accessing integration Options via Home Assistant UI, then the options form renders populated with current configuration values.
- Given options form submission with updated `retention_days` (e.g. 14 days), when submitted, then `entry.options` is updated and `GarminStorage.async_prune_history(14)` is called to purge snapshots older than 14 days.
- Given invalid `retention_days` (< 7 or > 90), when form is submitted, then validation fails and form is re-displayed with error.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. uv run --python 3.14 --with google-genai --with garminconnect --with httpx --with pytest-homeassistant-custom-component python -m pytest -W ignore::pytest.PytestRemovedIn9Warning tests/test_options_flow.py` -- expected: 100% pass on options flow tests.
- `PYTHONPATH=. uv run --python 3.14 --with google-genai --with garminconnect --with httpx --with pytest-homeassistant-custom-component python -m pytest -W ignore::pytest.PytestRemovedIn9Warning` -- expected: 100% pass on entire test suite.

## Suggested Review Order

**Options Flow & UI Configuration**

- Handles post-setup reconfiguration and triggers retention window history pruning on option submit.
  [`options_flow.py:27`](../../custom_components/garmin_ha_ai/options_flow.py#L27)

- Exposes Options Flow via `async_get_options_flow` on integration ConfigFlow.
  [`config_flow.py:182`](../../custom_components/garmin_ha_ai/config_flow.py#L182)

- Attaches options update listener to reload config entry and prune expired history snapshots.
  [`__init__.py:14`](../../custom_components/garmin_ha_ai/__init__.py#L14)

**Test Suite & Verification**

- Verifies options form rendering, option persistence, retention window bounds checking, and history pruning.
  [`test_options_flow.py:25`](../../tests/test_options_flow.py#L25)
