---
title: "Garmin MFA Session Resume & Decoupled Verification Fix"
type: "bugfix"
created: "2026-11-06"
status: "done"
baseline_commit: "c6ae69ce70a2c55022b7bd3db2f294009ab2baba"
review_loop_iteration: 0
context:
  - "custom_components/garmin_ha_ai/garmin_client.py"
  - "custom_components/garmin_ha_ai/config_flow.py"
  - "custom_components/garmin_ha_ai/exceptions.py"
  - "custom_components/garmin_ha_ai/manifest.json"
  - "tests/test_garmin_client.py"
  - "tests/test_config_flow.py"
  - "tests/e2e/test_e2e_full_lifecycle.py"
  - "tests/e2e/test_e2e_resilience_and_errors.py"
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:**
When a user with Garmin Two-Factor Authentication (MFA) enabled submits their 6-digit MFA passcode in the Home Assistant setup wizard (or re-auth flow), the flow fails with `Invalid 6-digit MFA passcode. Please try again.` and triggers a duplicate email with a new verification code.
In `custom_components/garmin_ha_ai/garmin_client.py`:
1. `client.login(mfa_code=mfa_code)` is called, but `garminconnect.Garmin.login()` does not accept `mfa_code` as a keyword argument (signature: `login(self, /, tokenstore: str | None = None)`), raising `TypeError`.
2. The `except TypeError:` fallback calls `client.login()` with email/password on a fresh `Garmin()` instance, triggering a brand-new login challenge on Garmin SSO, immediately invalidating the previous code and emailing a second MFA passcode to the user.
3. In headless Home Assistant execution, `python-garminconnect`'s default interactive `prompt_mfa = input` raises an EOF or auth error, caught at `garmin_client.py:458` logging `Garmin authentication failed` and raising `ConfigEntryAuthFailed`.
4. In `config_flow.py`, `ConfigEntryAuthFailed` maps to error code `"invalid_mfa"`, displaying `"Invalid 6-digit MFA passcode. Please try again."` in an endless loop.
5. Unit tests in `tests/test_garmin_client.py` missed this because `Garmin.login` was mocked with a loose `MagicMock()` that accepted `mfa_code="123456"`.

**Approach:**
1. Upgrade `garminconnect` requirement in `custom_components/garmin_ha_ai/manifest.json` to `>=0.3.20` to support modern decoupled session resumption.
2. In `custom_components/garmin_ha_ai/garmin_client.py`:
   - Initialize `Garmin(email=username, password=password, return_on_mfa=True)` during initial login.
   - When MFA is triggered, capture the serializable `client_state` dict returned with `"needs_mfa"` and pass it via `GarminMfaRequired(message, client_state=client_state)`.
   - In `async_login_with_credentials(..., mfa_code, client_state)`: when `mfa_code` and `client_state` are provided, instantiate `Garmin()` and invoke `client.resume_login(client_state, mfa_code)` in the executor thread without re-authenticating credentials or starting a new session.
3. In `custom_components/garmin_ha_ai/exceptions.py`:
   - Update `GarminMfaRequired` to accept and store optional `client_state: dict[str, Any] | None = None`.
4. In `custom_components/garmin_ha_ai/config_flow.py`:
   - Store `client_state` on `self._mfa_client_state` during `async_step_user` and `async_step_reauth_confirm` when `GarminMfaRequired` is caught.
   - Pass `client_state=self._mfa_client_state` into `client.async_login_with_credentials()` in `async_step_mfa`.
5. Update unit and E2E tests across `tests/test_garmin_client.py`, `tests/test_config_flow.py`, and `tests/e2e/` to reflect the decoupled `return_on_mfa` and `resume_login` contract.

## Boundaries & Constraints

**Always:**
- Use Home Assistant executor wrappers (`hass.async_add_executor_job`) for all synchronous network calls in `python-garminconnect`.
- Treat `client_state` with high security: keep it in-memory only on the flow instance (`self._mfa_client_state`) and never log its contents (contains session cookies).
- Maintain backward compatibility in `GarminClient.async_login_with_credentials`: accept `client_state: dict[str, Any] | None = None` alongside `mfa_code: str | None = None`.
- Ensure all 181+ tests pass via `pytest`.

**Ask First:**
- Any change to the UI strings, error translation keys, or config flow step IDs (`user`, `mfa`, `reauth`).

**Never:**
- Call `Garmin.login(mfa_code=...)` or call `login()` without `client_state` during the MFA submission step.
- Log raw MFA codes, user credentials, or `client_state` cookies.
- Block the Home Assistant event loop with synchronous network calls.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Credential Login without MFA | Valid username & password, no 2FA on account | `client.login()` returns `(None, None)` or clean client, tokens serialized, config entry created | `ConfigEntryAuthFailed` on invalid credentials |
| Credential Login with MFA Challenge | Valid username & password, 2FA enabled | `client.login()` returns `("needs_mfa", client_state)`, raises `GarminMfaRequired(..., client_state=...)` | Caught by `config_flow.py`, preserves `self._mfa_client_state`, transitions to `step_id="mfa"` |
| Valid MFA Passcode Submission | `mfa_code="123456"`, `client_state={...}` | `client.resume_login(client_state, "123456")` completes auth, tokens serialized & saved, config entry created | If `resume_login` fails with auth error, raise `ConfigEntryAuthFailed`, UI displays `invalid_mfa` |
| Invalid / Expired MFA Passcode | Expired or incorrect `mfa_code="000000"`, valid `client_state` | `client.resume_login()` raises `GarminConnectAuthenticationError`, mapped to `ConfigEntryAuthFailed` | UI displays `invalid_mfa` ("Invalid 6-digit MFA passcode. Please try again."), allows retry with existing or refreshed state |
| Re-authentication Flow with MFA | Existing entry, new password triggers MFA | Reauth step captures `client_state`, transitions to `async_step_mfa`, resumes session, reloads entry | If reauth fails, shows error alert without corrupting stored entry |
| Legacy / Missing client_state Fallback | `mfa_code` provided but `client_state=None` | Graceful fallback or clear error rather than unhandled exception | Raise `GarminMfaRequired` or `ConfigEntryAuthFailed` prompting fresh login |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/manifest.json` -- Bump `garminconnect` dependency to `>=0.3.20`.
- `custom_components/garmin_ha_ai/exceptions.py` -- Update `GarminMfaRequired` constructor to accept and store `client_state: dict[str, Any] | None = None`.
- `custom_components/garmin_ha_ai/garmin_client.py`:
  - Update `async_login_with_credentials` signature to `(username, password, mfa_code=None, client_state=None)`.
  - In `_credential_login`:
    - When `mfa_code` and `client_state` are provided: instantiate `client = Garmin()` and call `client.resume_login(client_state, mfa_code)`.
    - When starting initial login: instantiate `client = Garmin(email=username, password=password, return_on_mfa=True)`. Call `res = client.login()`. If `isinstance(res, tuple)` and `res[0] == "needs_mfa"`, raise `GarminMfaRequired("Garmin MFA required", client_state=res[1])`.
- `custom_components/garmin_ha_ai/config_flow.py`:
  - In `__init__`: initialize `self._mfa_client_state: dict[str, Any] | None = None`.
  - In `async_step_user`: catch `GarminMfaRequired as err`, store `self._mfa_client_state = err.client_state`.
  - In `async_step_mfa`: pass `client_state=self._mfa_client_state` into `client.async_login_with_credentials(username, password, mfa_code=mfa_code, client_state=self._mfa_client_state)`.
  - In `async_step_reauth_confirm`: catch `GarminMfaRequired as err`, store `self._mfa_client_state = err.client_state`.
- `tests/test_garmin_client.py` -- Update MFA unit tests to mock `login()` returning `("needs_mfa", client_state)` and test `resume_login(client_state, mfa_code)` invocation.
- `tests/test_config_flow.py` -- Update tests for `async_step_user` and `async_step_mfa` ensuring `client_state` is preserved and passed to client.
- `tests/e2e/test_e2e_full_lifecycle.py` & `tests/e2e/test_e2e_resilience_and_errors.py` -- Verify E2E flows handle MFA challenge and submission with `client_state`.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/manifest.json` -- Update requirement `garminconnect>=0.3.20`.
- [x] `custom_components/garmin_ha_ai/exceptions.py` -- Add `client_state` attribute to `GarminMfaRequired`.
- [x] `custom_components/garmin_ha_ai/garmin_client.py` -- Implement decoupled MFA login using `return_on_mfa=True` and `resume_login(client_state, mfa_code)`.
- [x] `custom_components/garmin_ha_ai/config_flow.py` -- Retain `self._mfa_client_state` across user/reauth and MFA steps and pass to `async_login_with_credentials`.
- [x] `tests/test_garmin_client.py` -- Update unit tests asserting `resume_login` contract.
- [x] `tests/test_config_flow.py` -- Update config flow tests verifying MFA state handling.
- [x] `tests/e2e/test_e2e_full_lifecycle.py` -- Verify E2E lifecycle with decoupled MFA.
- [x] `tests/e2e/test_e2e_resilience_and_errors.py` -- Verify reauth flow with decoupled MFA.

**Acceptance Criteria:**
- Given a user setting up Garmin HA AI with MFA enabled on their Garmin account
- When they enter their username and password
- Then Garmin initiates the 2FA challenge, the integration captures `client_state`, and the user is presented with the 6-digit MFA passcode form without blocking HA's event loop
- When the user submits the 6-digit MFA passcode received from Garmin
- Then authentication resumes via `resume_login(client_state, mfa_code)` against the existing session
- And no secondary MFA email is sent by Garmin
- And OAuth tokens are saved to local storage, creating the config entry successfully.
- Given an invalid MFA passcode submitted
- Then `ConfigEntryAuthFailed` is raised and the user is shown `invalid_mfa` without crashing the coordinator or leaking session state.
- Given all 181+ tests in the test suite
- When running `pytest`
### Review Findings

- [x] [Review][Patch] Reject login attempts with ConfigEntryAuthFailed when mfa_code provided without client_state instead of triggering duplicate email [custom_components/garmin_ha_ai/garmin_client.py:424]
- [x] [Review][Patch] Raise ConfigEntryAuthFailed if resume_login is missing or unsupported [custom_components/garmin_ha_ai/garmin_client.py:422]
- [x] [Review][Patch] Clear self._mfa_client_state upon entry creation and reauth completion to eliminate stale session cookies [custom_components/garmin_ha_ai/config_flow.py:140,212]
- [x] [Review][Patch] Add info log in async_step_reauth_confirm when MFA challenge triggered [custom_components/garmin_ha_ai/config_flow.py:189]
- [x] [Review][Patch] Add unit test asserting return_on_mfa=True is passed to Garmin constructor [tests/test_garmin_client.py:579]
- [x] [Review][Patch] Add unit test verifying resume_login authentication failure raises ConfigEntryAuthFailed [tests/test_garmin_client.py:176]
- [x] [Review][Patch] Update E2E lifecycle and resilience tests to assert decoupled client_state handling [tests/e2e/test_e2e_full_lifecycle.py:62, tests/e2e/test_e2e_resilience_and_errors.py:87]
- [x] [Review][Patch] Widen client_state type annotation to Any to support all serializable session state payloads [custom_components/garmin_ha_ai/exceptions.py:27, custom_components/garmin_ha_ai/garmin_client.py:408]

## Verification

**Commands:**
```bash
.venv/bin/pytest
```

## Suggested Review Order

**Decoupled MFA Session Resumption**

- Entry point: capture decoupled session state with `return_on_mfa=True` and resume session via `resume_login`
  [`garmin_client.py:415`](../../custom_components/garmin_ha_ai/garmin_client.py#L415)

- Store decoupled `client_state` payload in `GarminMfaRequired` exception
  [`exceptions.py:27`](../../custom_components/garmin_ha_ai/exceptions.py#L27)

- Preserve `_mfa_client_state` across config/reauth wizard steps and clean up on completion
  [`config_flow.py:73`](../../custom_components/garmin_ha_ai/config_flow.py#L73)

**Package Requirements & Peripherals**

- Bump `garminconnect` dependency to `>=0.3.20` for decoupled MFA support
  [`manifest.json:10`](../../custom_components/garmin_ha_ai/manifest.json#L10)

- Unit tests for session resumption, missing state rejection, and constructor parameters
  [`test_garmin_client.py:137`](../../tests/test_garmin_client.py#L137)

- Unit tests for config flow state preservation and reauth verification
  [`test_config_flow.py:77`](../../tests/test_config_flow.py#L77)

- End-to-end lifecycle and resilience tests asserting decoupled MFA flow
  [`test_e2e_full_lifecycle.py:62`](../../tests/e2e/test_e2e_full_lifecycle.py#L62)
