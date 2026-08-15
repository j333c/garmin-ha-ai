---
title: 'Story 1.2: Local Storage & Token Persistence Helper (storage.py)'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '00f90f026aa978a647bfb9fa760cc61f950e56f9'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The integration requires persisting Garmin OAuth tokens and daily metric history snapshots locally in Home Assistant `.storage/` safely without data race corruption or storing plaintext passwords.

**Approach:** Implement `custom_components/garmin_ha_ai/storage.py` using Home Assistant `Store` helpers (`homeassistant.helpers.storage.Store`), guarded by `asyncio.Lock()` to serialize all read/write I/O and return empty dictionaries when files are missing on a clean installation.

## Boundaries & Constraints

**Always:** Access local storage via Home Assistant `Store` helper (`homeassistant.helpers.storage.Store`); never perform raw file I/O directly. Guard disk operations with `asyncio.Lock()`. Sanitize/protect sensitive tokens. Return empty dictionaries if storage files do not exist.

**Ask First:** Changing storage file keys or structure schema.

**Never:** Store plaintext passwords or raw unencrypted credentials in storage files. Perform blocking synchronous file I/O in the main event loop.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Load Tokens (Clean Install) | `.storage/garmin_ha_ai_tokens.json` does not exist | Returns `{}` (empty dict) | Missing file handled gracefully without raising exception |
| Save Tokens | Dict containing Garmin OAuth token data | Data saved to `.storage/garmin_ha_ai_tokens.json` under `asyncio.Lock()` | Lock released even if save fails |
| Load History (Clean Install) | `.storage/garmin_ha_ai_history.json` does not exist | Returns `{}` (empty dict) | Missing file handled gracefully without raising exception |
| Concurrent Read/Write | Multiple tasks attempting to load/save simultaneously | Disk operations executed sequentially via `asyncio.Lock()` | Prevents data race conditions and file corruption |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/storage.py` -- Storage helper module managing token and history persistence via HA `Store` and `asyncio.Lock()`.
- `custom_components/garmin_ha_ai/const.py` -- Defines `STORAGE_KEY_TOKENS`, `STORAGE_KEY_HISTORY`, `STORAGE_VERSION`.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/storage.py` -- Create `GarminStorage` class -- Implements `async_load_tokens`, `async_save_tokens`, `async_load_history`, `async_save_history`, and `async_prune_history` using HA `Store` helpers and `asyncio.Lock()`.
- [x] `tests/test_storage.py` -- Create storage unit tests -- Verifies load/save operations, missing file handling, and lock serialization.

**Acceptance Criteria:**
- Given `storage.py` initializing Home Assistant `Store` helpers
- When data read or write operations occur
- Then all disk I/O operations are serialized using `asyncio.Lock()`
- And missing storage files on clean installation return empty dictionary data structures without raising unhandled errors

## Design Notes

`GarminStorage` class design:
```python
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

class GarminStorage:
    def __init__(self, hass: HomeAssistant) -> None:
        self._token_store = Store(hass, STORAGE_VERSION, STORAGE_KEY_TOKENS)
        self._history_store = Store(hass, STORAGE_VERSION, STORAGE_KEY_HISTORY)
        self._token_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()

    async def async_load_tokens(self) -> dict[str, Any]:
        async with self._token_lock:
            data = await self._token_store.async_load()
            return data if data is not None else {}

    async def async_save_tokens(self, tokens: dict[str, Any]) -> None:
        async with self._token_lock:
            await self._token_store.async_save(tokens)
```

## Verification

**Commands:**
- `python3 -m py_compile custom_components/garmin_ha_ai/storage.py` -- expected: Compilation succeeds with exit code 0

**Manual checks (if no CLI):**
- Verify `storage.py` uses `homeassistant.helpers.storage.Store` and wraps reads/writes in `asyncio.Lock()`.

## Suggested Review Order

**Local Storage Helper & Token Persistence**

- Storage helper class wrapping HA Store helpers and asyncio.Lock for thread-safe persistence.
  [`storage.py:17`](../../custom_components/garmin_ha_ai/storage.py#L17)

**Storage Unit Tests**

- Unit tests verifying load, save, missing file fallback, concurrency, and history pruning.
  [`test_storage.py:37`](../../tests/test_storage.py#L37)
