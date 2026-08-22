# Error Handling Taxonomy, Localization & Dual-Mode Polling

## Centralized Exception Taxonomy (`exceptions.py`)

All exceptions raised by the Garmin Connect API and AI Engine are centralized into a clean, strongly typed hierarchy:

- `GarminAIError` (Base HomeAssistantError)
  - `GarminError`: Base class for Garmin Connect operations
    - `GarminAuthError`: Raised on invalid/revoked credentials (inherits `ConfigEntryAuthFailed`).
    - `GarminMfaRequired`: Intercepts 2FA verification challenges.
    - `GarminRateLimitError`: Raised on HTTP 429 rate limits, preserving cached data without deleting tokens.
    - `GarminConnectionError`: Raised on network failures.
    - `GarminDataParsingError`: Raised on unexpected payload schemas.
    - `GarminSessionExpiredError`: Raised when stored session tokens require re-authentication.
  - `AIEngineError`: Base class for AI provider drivers
    - `AIEngineAuthError`: Raised on API key invalidation (401/403).
    - `AIEngineQuotaError`: Raised when model quotas are exhausted (429).
    - `AIEngineTimeoutError`: Raised when generation exceeds timeout threshold.
    - `AIEngineModelNotFoundError`: Raised for deprecated or invalid model IDs (404).
    - `AIEngineClientError`: Raised for non-transient 4xx client errors (fails fast without retry loops).
    - `AIEngineConnectionError`: Raised on endpoint connection failures.

## Full UI Localization (English & German)

All integration components—Config Flow, Options Flow, entities, select options, and Developer Tools services—are 100% localized in:
- `translations/en.json` (English)
- `translations/de.json` (German)
- `strings.json` (Canonical Home Assistant strings template)

## Dual-Mode Polling Engine

Configure your sync cadence in Options Flow with two flexible modes:
1. **Daily Fixed Time**: Syncs daily at a chosen time (e.g. 06:00:00) using Home Assistant's native `TimeSelector`.
2. **Periodic Interval**: Syncs recurringly across configurable intervals (every 1, 3, 6, 12, or 24 hours).
