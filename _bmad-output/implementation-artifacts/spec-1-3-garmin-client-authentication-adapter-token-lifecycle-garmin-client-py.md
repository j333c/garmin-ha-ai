---
title: 'Story 1.3: Garmin Client Authentication Adapter & Token Lifecycle (garmin_client.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '4d7efc4be3cefb1eec1485e89e720c9c482f8da6'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The integration needs an authentication adapter around `garminconnect.Garmin` that manages OAuth token persistence, silent token refreshes, MFA authentication challenges, and raises `ConfigEntryAuthFailed` when session tokens expire or become invalid.

**Approach:** Implement `custom_components/garmin_ha_ai/garmin_client.py` wrapping synchronous `garminconnect.Garmin` calls in `hass.async_add_executor_job`, interacting with `GarminStorage` for token load/save, sanitizing all log outputs, and raising `ConfigEntryAuthFailed` on permanent authentication failures.

## Boundaries & Constraints

**Always:** Use `hass.async_add_executor_job` for all `garminconnect` synchronous library calls. Sanitize logs so Garmin passwords and tokens are never logged. Save updated tokens to `GarminStorage` after successful login/refresh. Raise `ConfigEntryAuthFailed` on unrecoverable authentication errors.

**Ask First:** Modifying token storage keys or changing authentication library.

**Never:** Store or log plaintext passwords in memory longer than the login execution. Perform synchronous blocking network calls on the main HA event loop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Token Resume (Success) | Valid OAuth tokens in `GarminStorage` | Client initialized from stored tokens without credentials | Log debug message, return authenticated client |
| Token Resume (Expired / Invalid) | Stored tokens revoked or expired | Attempts silent refresh; if refresh fails, raises `ConfigEntryAuthFailed` | Catch `GarminConnectAuthenticationError`, raise `ConfigEntryAuthFailed` |
| Credential Login (Success) | Username, password provided | Authenticates with Garmin, extracts tokens, saves to `GarminStorage` | Return token dict |
| MFA Required | Login triggers MFA prompt | Returns MFA challenge requirement indicator for Config Flow | Handled by caller to prompt user for MFA code |
| Permanent Auth Failure | Invalid username/password | Raises `ConfigEntryAuthFailed` | Sanitize error log, raise `ConfigEntryAuthFailed` |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/garmin_client.py` -- Garmin authentication adapter wrapping `garminconnect.Garmin` with async executor wrappers, token persistence via `GarminStorage`, and `ConfigEntryAuthFailed` exception mapping.
- `custom_components/garmin_ha_ai/storage.py` -- Storage helper used to persist and load token dictionaries (`async_load_tokens`, `async_save_tokens`).
- `custom_components/garmin_ha_ai/const.py` -- Domain constants and logger instance.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/garmin_client.py` -- Create `GarminClient` class -- Implements `async_login_with_credentials`, `async_login_with_tokens`, `async_get_client`, and token refresh logic wrapped in `hass.async_add_executor_job`.
- [x] `tests/test_garmin_client.py` -- Create unit test suite -- Tests token resume, credential login, MFA handling, log sanitization, and `ConfigEntryAuthFailed` propagation.

**Acceptance Criteria:**
- Given valid stored OAuth tokens in `.storage/garmin_ha_ai_tokens.json`
- When the Garmin client initializes or tokens approach expiration
- Then `garmin_client.py` silently refreshes access tokens without requiring plaintext passwords
- And if authentication fails permanently (password change or token revocation), the client raises `ConfigEntryAuthFailed` to trigger native HA re-authentication UI

## Design Notes

`GarminClient` structure:
```python
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from garminconnect import Garmin, GarminConnectAuthenticationError
from .storage import GarminStorage

class GarminClient:
    def __init__(self, hass: HomeAssistant, storage: GarminStorage) -> None:
        self.hass = hass
        self.storage = storage
        self.client: Garmin | None = None

    async def async_login_with_tokens(self) -> bool:
        tokens = await self.storage.async_load_tokens()
        if not tokens:
            return False
        # Initialize client with tokens in executor job...
```

## Verification

**Commands:**
- `python3 -m py_compile custom_components/garmin_ha_ai/garmin_client.py` -- expected: Compilation succeeds with exit code 0
- `PYTHONPATH=. uv run pytest tests/test_garmin_client.py` -- expected: All unit tests pass with exit code 0

**Manual checks (if no CLI):**
- Verify no passwords or tokens are printed in logger statements.
- Verify all `garminconnect` calls run via `hass.async_add_executor_job`.

## Suggested Review Order

**Garmin Client Authentication Adapter**

- Main authentication wrapper for python-garminconnect managing executor calls and token save/restore.
  [`garmin_client.py:18`](../../custom_components/garmin_ha_ai/garmin_client.py#L18)

**Unit Test Suite**

- Unit tests for token resume, credential login, MFA challenges, log sanitization, and exception mapping.
  [`test_garmin_client.py:37`](../../tests/test_garmin_client.py#L37)
