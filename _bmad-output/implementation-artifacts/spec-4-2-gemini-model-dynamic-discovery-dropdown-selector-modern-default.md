---
title: 'Gemini Model Dynamic Discovery, Dropdown Selector & Modern Model Default'
type: 'feature'
created: '2026-08-16'
status: 'done'
context:
  - 'custom_components/garmin_ha_ai/ai_engine/gemini.py'
  - 'custom_components/garmin_ha_ai/ai_engine/base.py'
  - 'custom_components/garmin_ha_ai/ai_engine/openai.py'
  - 'custom_components/garmin_ha_ai/options_flow.py'
  - 'custom_components/garmin_ha_ai/const.py'
---

## Intent

**Problem:**
1. Default Gemini model `gemini-2.0-flash` returned 404 NOT_FOUND (`model is no longer available`).
2. When non-transient client errors occur (404 Not Found, 400 Bad Request, 401 Unauthorized, 403 Forbidden), `async_with_retry` retries them 3 times with exponential backoff, producing confusing log spam.
3. Users currently have to type model names in a free-text input rather than choosing from a dynamic list of valid models.

**Approach:**
1. Update `DEFAULT_AI_MODEL_GEMINI` in `const.py` to `gemini-2.5-flash`.
2. Implement dynamic model discovery API helper (`async_list_models`) in `ai_engine/gemini.py` that queries the Gemini API for available `generateContent` models using executor jobs, falling back to known active models.
3. In `options_flow.py`, use `SelectSelector` for `CONF_AI_MODEL` with dynamically populated options.
4. Define `AIEngineClientError` in `ai_engine/base.py` and exclude it from `async_with_retry` to fast-fail on 4xx client errors.

## Tasks & Acceptance

- [x] Update `const.py` default model and fallback model lists.
- [x] Define `AIEngineClientError` and exclude from retry backoff.
- [x] Implement dynamic model enumeration helper in `ai_engine/gemini.py`.
- [x] Update `options_flow.py` with `SelectSelector` dropdown for AI models.
- [x] Add tests in `tests/test_ai_engine.py` and `tests/test_options_flow.py`.
