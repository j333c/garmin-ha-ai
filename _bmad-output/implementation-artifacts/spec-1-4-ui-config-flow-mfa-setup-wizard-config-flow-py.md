---
title: 'Story 1.4: UI Config Flow & MFA Setup Wizard (config_flow.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '084da69738cffdcc88045e1a081944fcc5b6852d'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Users need an intuitive, UI-guided setup wizard in Home Assistant to configure Garmin Connect credentials, submit 6-digit MFA passcodes when required, select their AI Provider (Gemini or OpenAI), enter AI API keys, and configure initial fitness goals.

**Approach:** Implement `custom_components/garmin_ha_ai/config_flow.py` with multi-step support (`async_step_user`, `async_step_mfa`, `async_step_reauth`), using `voluptuous` schemas for input validation, `GarminClient` for credentials/MFA verification, and `strings.json` for UI labels.

## Boundaries & Constraints

**Always:** Use Home Assistant `config_entries.ConfigFlow` standards. Mask API keys and passwords in UI input forms. Handle MFA prompts with step transition (`async_step_mfa`). Support reauth flow (`async_step_reauth`).

**Ask First:** Changing schema fields or supported AI provider types.

**Never:** Store raw passwords in `ConfigEntry.data` (store OAuth tokens via `GarminStorage`). Perform synchronous I/O in config flow steps.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Single-Step Auth (No MFA) | Valid email, password, AI provider & key | Validates credentials, creates config entry | Show error on invalid credentials |
| MFA Required | Email & password require MFA | Transition to `async_step_mfa` for 6-digit passcode | Present MFA step with retry on wrong passcode |
| Invalid Credentials | Wrong password | Stays on user step | Show `invalid_auth` error alert |
| Re-authentication Flow | Triggered by `ConfigEntryAuthFailed` | Prompts user to update credentials/tokens | Update existing config entry data |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/config_flow.py` -- Config flow handler class `GarminHaAiConfigFlow` supporting user setup step, MFA step, and reauth step.
- `custom_components/garmin_ha_ai/garmin_client.py` -- Used by config flow to authenticate credentials and verify MFA passcodes.
- `custom_components/garmin_ha_ai/const.py` -- Domain constants, AI provider choices, and default schema keys.
- `custom_components/garmin_ha_ai/strings.json` -- UI translation strings for config flow step titles, labels, and error messages.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/strings.json` -- Create UI translation strings for setup wizard steps and error codes.
- [x] `custom_components/garmin_ha_ai/config_flow.py` -- Create `GarminHaAiConfigFlow` class -- Implements `async_step_user`, `async_step_mfa`, `async_step_reauth`, and `async_step_reauth_confirm`.
- [x] `tests/test_config_flow.py` -- Create unit test suite -- Verifies full setup flow, MFA branch, reauth flow, and invalid credential error handling.

**Acceptance Criteria:**
- Given a user adding "Garmin HA AI" via Settings -> Devices & Services
- When entering Garmin email/password and (if triggered) 6-digit MFA passcode
- Then the Config Flow validates credentials, prompts for AI Provider selection (Gemini vs OpenAI) and initial goals, and creates the config entry upon success
- And if MFA input times out or credentials fail, clear UI error alerts and retry options are presented without restarting the setup wizard

## Verification

**Commands:**
- `python3 -m py_compile custom_components/garmin_ha_ai/config_flow.py` -- expected: Compilation succeeds with exit code 0
- `PYTHONPATH=. uv run pytest tests/test_config_flow.py` -- expected: All unit tests pass with exit code 0

**Manual checks (if no CLI):**
- Verify `config_flow.py` handles user, MFA, and reauth steps cleanly.
- Verify `strings.json` includes translations for step titles and errors.

## Suggested Review Order

**UI Translation Strings**

- UI step titles, field labels, and error message translations.
  [`strings.json:1`](../../custom_components/garmin_ha_ai/strings.json#L1)

**Config Flow Setup Wizard & MFA Handler**

- Multi-step UI config flow handler for setup, MFA passcode validation, and re-authentication.
  [`config_flow.py:35`](../../custom_components/garmin_ha_ai/config_flow.py#L35)

**Unit Test Suite**

- Unit tests for initial form render, credential login, MFA step, and error handling.
  [`test_config_flow.py:53`](../../tests/test_config_flow.py#L53)
