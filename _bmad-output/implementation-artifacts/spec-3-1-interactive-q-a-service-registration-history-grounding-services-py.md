---
title: 'Interactive Q&A Service Registration & History Grounding'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: 'dc319409936e4d3e6cddf1e2c0a2ad4325506504'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/services.py'
  - 'custom_components/garmin_ha_ai/ai_engine/prompt.py'
  - 'custom_components/garmin_ha_ai/const.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Home Assistant users need to ask context-grounded health and workout questions on demand via service `garmin_ha_ai.ask_question` and receive answers directly in service response data without hitting live Garmin cloud APIs or waiting more than 10 seconds.

**Approach:**
1. Create `assemble_qa_prompt` in `ai_engine/prompt.py` to assemble the user question, historical metrics (past N days), fitness goals, and persona directives into a prompt payload for Q&A.
2. Implement service registration `garmin_ha_ai.ask_question` in `services.py` with `SupportsResponse.OPTIONAL` accepting parameters `question` (required), `days_history` (default 7), and optional `response_entity`.
3. In the service handler, fetch local metric history from `GarminStorage` (`.storage/garmin_ha_ai_history.json` guarded by `asyncio.Lock()`), clamp `days_history` to `min(requested_days, available_stored_days)` (7-90 max), construct the prompt via `assemble_qa_prompt`, and execute response generation via configured AI Engine driver.
4. Return `{"answer": answer_text, "question": question_text}` directly as service response data within <10 seconds.

## Boundaries & Constraints

**Always:**
- Register service `garmin_ha_ai.ask_question` with `supports_response=SupportsResponse.OPTIONAL` in `services.py`.
- Clamp `days_history` parameter to `min(requested_days, available_stored_days)` (valid range: 1 to 90).
- Load metric history from local storage using `GarminStorage` (`storage.py`) guarded by `asyncio.Lock()`.
- Return service response data dictionary `{"answer": "...", "question": "..."}` directly upon completion.
- Execute all AI engine calls asynchronously without blocking the main event loop.

**Ask First:**
- Adding additional required parameters to `garmin_ha_ai.ask_question`.

**Never:**
- Make live Garmin cloud network calls during Q&A execution.
- Raise unhandled exceptions on empty or missing history files; fallback to zero/available history gracefully.
- Block the Home Assistant event loop with synchronous I/O or HTTP calls.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Standard Q&A Request | `question="Should I run today?"`, `days_history=7` | Returns `{"answer": "...", "question": "Should I run today?"}` based on 7-day history | N/A |
| History Overflow Clamping | `days_history=100`, 14 stored days available | Clamps `days_history` to 14 days, returns answer | N/A |
| Empty / Missing History | `days_history=7`, no stored history file | Assembles prompt with zero history message, returns answer | Graceful fallback, no exception |
| Missing API Key | Service invoked when `ai_api_key` is empty/unset | Service call raises `HomeAssistantError` | `HomeAssistantError("AI API key is not configured.")` |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/services.py` -- Implementation of `async_setup_services` and service handler `async_handle_ask_question` registering `garmin_ha_ai.ask_question` with `SupportsResponse.OPTIONAL`.
- `custom_components/garmin_ha_ai/ai_engine/prompt.py` -- Implementation of `assemble_qa_prompt()` function formatting question, historical metric context, user goals, and coaching directives.
- `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Export `assemble_qa_prompt`.
- `custom_components/garmin_ha_ai/__init__.py` -- Call `async_setup_services(hass)` during component setup.
- `custom_components/garmin_ha_ai/const.py` -- Centralized definition for `SERVICE_ASK_QUESTION = "ask_question"`.
- `tests/test_services.py` -- Unit tests for `garmin_ha_ai.ask_question` service registration, response payload format, history clamping, missing API key error, and mock AI response.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/ai_engine/prompt.py` -- Add `assemble_qa_prompt()` function to assemble user question, N-day history, goals, and directives into prompt context.
- [x] `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Export `assemble_qa_prompt` from package.
- [x] `custom_components/garmin_ha_ai/services.py` -- Implement `async_setup_services()` registering `garmin_ha_ai.ask_question` with `SupportsResponse.OPTIONAL`, parameter validation, history clamping, AI execution, and response dictionary return.
- [x] `custom_components/garmin_ha_ai/__init__.py` -- Invoke `async_setup_services(hass)` in `async_setup`.
- [x] `tests/test_services.py` -- Write unit tests verifying Q&A service registration, response dictionary output, history clamping, missing history fallback, and API key validation.

**Acceptance Criteria:**
- Given `garmin_ha_ai` integration loaded, when service `garmin_ha_ai.ask_question` is called with `question` and `days_history`, then it returns `{"answer": "...", "question": "..."}` directly in service response data without hitting Garmin cloud APIs.
- Given `days_history` parameter larger than available history, then `days_history` is clamped to available days count without error.
- Given empty AI API key, calling `garmin_ha_ai.ask_question` raises `HomeAssistantError`.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. uv run --python 3.14 --with google-genai --with garminconnect --with httpx --with pytest-homeassistant-custom-component python -m pytest -W ignore::pytest.PytestRemovedIn9Warning tests/test_services.py` -- expected: 100% pass on services unit tests.
- `PYTHONPATH=. uv run --python 3.14 --with google-genai --with garminconnect --with httpx --with pytest-homeassistant-custom-component python -m pytest -W ignore::pytest.PytestRemovedIn9Warning` -- expected: 100% pass on test suite.
