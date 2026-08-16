---
title: 'Garmin 429 Rate Limit Resilience & Auth Flow Isolation'
type: 'bugfix'
created: '2026-08-16'
status: 'done'
context:
  - 'custom_components/garmin_ha_ai/garmin_client.py'
  - 'custom_components/garmin_ha_ai/coordinator.py'
---

## Intent

**Problem:**
When Garmin Connect API returns HTTP 429 (`GarminConnectTooManyRequestsError`), the generic error handling caught it as a general failure and raised `ConfigEntryAuthFailed`, falsely triggering Home Assistant re-authentication prompts and attempting repeated logins against a rate-limited endpoint.

**Approach:**
1. Specifically catch `GarminConnectTooManyRequestsError` and 429 response messages in `garmin_client.py`.
2. Do NOT raise `ConfigEntryAuthFailed` on 429; preserve valid stored OAuth tokens and raise a rate-limit connection error / `UpdateFailed`.
3. In `coordinator.py`, catch 429 rate limit exceptions and fall back to cached local metrics without triggering auth flow alerts.

## Tasks & Acceptance

- [x] Update `garmin_client.py` to handle 429 rate limits without invalidating authentication tokens.
- [x] Update `coordinator.py` to gracefully fallback to cached metrics on rate limits.
- [x] Add tests in `tests/test_garmin_client.py` and `tests/e2e/test_e2e_resilience_and_errors.py`.
