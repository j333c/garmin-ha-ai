---
title: 'Last Answer Sensor Entity & Interactive Lovelace Q&A Card Pattern'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: '23eae888a8ec12ce363365b597e56020d556a7c7'
review_loop_iteration: 0
context:
  - 'custom_components/garmin_ha_ai/sensor.py'
  - 'custom_components/garmin_ha_ai/services.py'
  - 'custom_components/garmin_ha_ai/coordinator.py'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Home Assistant users need a dedicated sensor entity (`sensor.garmin_ai_last_answer`) to display recent AI Q&A answers and inspect full response Markdown in attributes, as well as a documented interactive Lovelace dashboard card pattern to ask questions directly from the UI.

**Approach:**
1. Implement `GarminAILastAnswerSensor` in `custom_components/garmin_ha_ai/sensor.py` inheriting from `CoordinatorEntity` and `SensorEntity`. The native value returns a 250-character truncated summary (or status message), while `extra_state_attributes` contains `full_answer` (rich Markdown), `question`, and `timestamp`. Register `GarminAILastAnswerSensor` in `async_setup_entry`.
2. Update `GarminDataUpdateCoordinator` (`coordinator.py`) with `latest_answer: dict[str, Any] | None` and method `async_set_latest_answer(question: str, answer: str)` that updates `latest_answer` and calls `async_update_listeners()`.
3. In `services.py`, when `garmin_ha_ai.ask_question` executes, call `await coordinator.async_set_latest_answer(question, answer_text)` to propagate the latest question & answer state to `sensor.garmin_ai_last_answer`.
4. Document the Interactive Lovelace Q&A Card pattern in `docs/lovelace_qa_card.md` using native Home Assistant card configuration (markdown card + service call button / input card pattern).

## Boundaries & Constraints

**Always:**
- Truncate native state string of `GarminAILastAnswerSensor` to <250 characters (`[:247] + "..."`) to avoid Home Assistant `InvalidStateError` (< 255 chars).
- Store complete Markdown answer in `extra_state_attributes["full_answer"]`, original question in `extra_state_attributes["question"]`, and ISO timestamp in `extra_state_attributes["timestamp"]`.
- Update `sensor.garmin_ai_last_answer` state automatically whenever `garmin_ha_ai.ask_question` completes.
- Register `GarminAILastAnswerSensor` under unique ID `{entry.entry_id}_ai_last_answer`.

**Ask First:**
- Adding additional required parameters or state attributes to `sensor.garmin_ai_last_answer`.

**Never:**
- Allow `native_value` string length to exceed 255 characters.
- Perform blocking I/O or synchronous HTTP calls.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Initial State (No Question Asked) | Integration loaded, no Q&A executed yet | `native_value` = `"No question asked yet"`, `extra_state_attributes` = `{}` | N/A |
| Q&A Service Executed | `ask_question` completes with `question="How was my sleep?"` and 400-char answer | `native_value` = truncated 250-char answer, `full_answer` in attributes = full 400-char Markdown | N/A |
| Exception in Q&A | AI Engine throws error during `ask_question` | `sensor.garmin_ai_last_answer` retains previous state; service raises `HomeAssistantError` | Handled in `services.py` |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/sensor.py` -- Implementation of `GarminAILastAnswerSensor` class and inclusion in `async_setup_entry`.
- `custom_components/garmin_ha_ai/coordinator.py` -- Addition of `latest_answer` state attribute and `async_set_latest_answer()` method to notify entity listeners.
- `custom_components/garmin_ha_ai/services.py` -- Update `handle_ask_question` to update coordinator with question and answer.
- `docs/lovelace_qa_card.md` -- Lovelace interactive dashboard card pattern documentation.
- `tests/test_sensor.py` -- Unit tests for `GarminAILastAnswerSensor` initial state, truncation, attributes, and update listener trigger.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/coordinator.py` -- Add `latest_answer` attribute and `async_set_latest_answer(question: str, answer: str)` method.
- [x] `custom_components/garmin_ha_ai/sensor.py` -- Implement `GarminAILastAnswerSensor` entity and add to `async_setup_entry`.
- [x] `custom_components/garmin_ha_ai/services.py` -- Update `handle_ask_question` to update `coordinator.async_set_latest_answer`.
- [x] `docs/lovelace_qa_card.md` -- Create documentation for the Lovelace Q&A dashboard card pattern.
- [x] `tests/test_sensor.py` -- Add unit tests for `GarminAILastAnswerSensor`.

**Acceptance Criteria:**
- Given a user invoking service `garmin_ha_ai.ask_question`, when the service completes, then `sensor.garmin_ai_last_answer` updates its state to a truncated summary (<250 chars) and populates `extra_state_attributes["full_answer"]` with the full Markdown text and `extra_state_attributes["question"]` with the question.
- Given no question has been asked yet, then `sensor.garmin_ai_last_answer` state is `"No question asked yet"`.
- Given the interactive Lovelace Q&A card pattern configuration, users can submit questions and view answers on their Home Assistant dashboard.

## Spec Change Log

*No changes yet.*

## Verification

**Commands:**
- `PYTHONPATH=. uv run --python 3.14 --with google-genai --with garminconnect --with httpx --with pytest-homeassistant-custom-component python -m pytest -W ignore::pytest.PytestRemovedIn9Warning tests/test_sensor.py` -- expected: 100% pass on sensor unit tests.
- `PYTHONPATH=. uv run --python 3.14 --with google-genai --with garminconnect --with httpx --with pytest-homeassistant-custom-component python -m pytest -W ignore::pytest.PytestRemovedIn9Warning` -- expected: 100% pass on full test suite.

## Suggested Review Order

**Last Answer Sensor & Coordinator Integration**

- Implement `GarminAILastAnswerSensor` entity with state truncation (< 250 chars) and Markdown attributes.
  [`sensor.py:216`](../../custom_components/garmin_ha_ai/sensor.py#L216)

- Store latest answer state and trigger listener update on coordinator.
  [`coordinator.py:175`](../../custom_components/garmin_ha_ai/coordinator.py#L175)

- Propagate Q&A result from `ask_question` service to coordinator.
  [`services.py:117`](../../custom_components/garmin_ha_ai/services.py#L117)

**Documentation & Testing**

- Interactive Lovelace Q&A card pattern YAML configuration guide.
  [`lovelace_qa_card.md:1`](../../docs/lovelace_qa_card.md#L1)

- Unit test coverage for `GarminAILastAnswerSensor` state, truncation, and attributes.
  [`test_sensor.py:129`](../../tests/test_sensor.py#L129)

- Unit test verification of coordinator answer state call during service execution.
  [`test_services.py:99`](../../tests/test_services.py#L99)

