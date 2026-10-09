---
title: "AI Response Language Preference in Options Flow & Prompt Assembler"
type: "feature"
created: "2026-10-09"
status: "done"
baseline_commit: "9476ce16507c7727bb4c090b83340760c0379db5"
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:**
Daily health briefings, executive summaries, and interactive Q&A answers currently default to English prompt instructions without user configurability, requiring international users to manually prompt or translate responses.

**Approach:**
Add an `ai_language` configuration selector in the integration Options Flow supporting major languages (English, German, French, Spanish, Italian, Dutch, and System Default), resolve system language dynamically from Home Assistant configuration, and inject strict multilingual directives into prompt assembler payload blocks for reports and interactive Q&A.

## Boundaries & Constraints

**Always:**
- Persist language preference under configuration key `CONF_AI_LANGUAGE = "ai_language"` in config entry options.
- Default to `"system"` which resolves to `hass.config.language` when available, falling back safely to English (`"en"`).
- Inject language directives into Block 5 for daily reports and response instructions for interactive Q&A.
- Preserve entity state string safety (truncate summary to <250 characters via `truncate_entity_state`).
- Maintain backward compatibility for existing `assemble_report_prompt` and `assemble_qa_prompt` callers when `language` is omitted.

**Ask First:**
- Adding or altering languages beyond the specified set (`en`, `de`, `fr`, `es`, `it`, `nl`, `system`).

**Never:**
- Hardcode translations inside AI response text; language generation is handled by the LLM via prompt constraints.
- Make blocking calls to detect language.
- Break existing config entries that lack `CONF_AI_LANGUAGE` in their options.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Options Flow Selection | User selects "German (Deutsch)" (`"de"`) | Entry options updated with `{"ai_language": "de"}` | N/A |
| System Language Resolution | `CONF_AI_LANGUAGE="system"`, `hass.config.language="de"` | Prompt instructs LLM to respond in German | Falls back to English if system language unknown |
| Missing / Legacy Option | Config entry options lack `ai_language` | Defaults to `"system"`, resolving to system or English | N/A |
| Report Prompt Generation | `assemble_report_prompt(..., language="fr")` | Block 5 contains strict French output constraint for `<summary>` and markdown | N/A |
| Q&A Prompt Generation | `assemble_qa_prompt(..., language="es")` | Response instructions contain strict Spanish answer constraint | N/A |
| Summary Clamping in Foreign Language | LLM returns German summary in `<summary>...</summary>` | Parsed `short_summary` clamped <=250 chars in `parse_ai_health_report` | `truncate_entity_state` truncates safely |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/const.py` -- Define `CONF_AI_LANGUAGE = "ai_language"`, `DEFAULT_AI_LANGUAGE = "system"`, `AI_LANGUAGE_OPTIONS`, and `SUPPORTED_AI_LANGUAGES`.
- `custom_components/garmin_ha_ai/options_flow.py` -- Add `CONF_AI_LANGUAGE` dropdown selector under `async_step_init` with choices from `AI_LANGUAGE_OPTIONS`.
- `custom_components/garmin_ha_ai/ai_engine/prompt.py` -- Add `resolve_target_language()` helper; update `assemble_report_prompt` and `assemble_qa_prompt` to accept `language` and `hass` parameters and inject language rules.
- `custom_components/garmin_ha_ai/coordinator.py` -- In `_async_generate_report` (line 245) and `async_ask_question` (line 342), extract `CONF_AI_LANGUAGE` from options and forward to prompt assemblers with `self.hass`.
- `custom_components/garmin_ha_ai/strings.json` & `translations/en.json`, `translations/de.json` -- Add schema title/label for `ai_language`.
- `tests/test_prompt.py` -- Unit tests for language resolution, report prompt directive, and Q&A prompt directive.
- `tests/test_options_flow.py` -- Test options flow form schema includes `ai_language` and persists selection.
- `tests/test_coordinator.py` -- Test coordinator passes configured language to prompt assemblers.

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/const.py` -- Add `CONF_AI_LANGUAGE`, `DEFAULT_AI_LANGUAGE`, and language option mappings.
- [x] `custom_components/garmin_ha_ai/strings.json`, `translations/en.json`, `translations/de.json` -- Add localized labels for `ai_language`.
- [x] `custom_components/garmin_ha_ai/options_flow.py` -- Add language selector dropdown to `async_step_init` options schema.
- [x] `custom_components/garmin_ha_ai/ai_engine/prompt.py` -- Implement `resolve_target_language()` and inject language directives into Block 5 of `assemble_report_prompt` and response instructions of `assemble_qa_prompt`.
- [x] `custom_components/garmin_ha_ai/ai_engine/__init__.py` -- Export `resolve_target_language` if appropriate.
- [x] `custom_components/garmin_ha_ai/coordinator.py` -- Retrieve `CONF_AI_LANGUAGE` in `_async_generate_report` and `async_ask_question`, passing it into prompt generation.
- [x] `tests/test_prompt.py` -- Add unit tests verifying language directive injection for both reports and Q&A across supported language codes and system fallback.
- [x] `tests/test_options_flow.py` -- Add tests verifying `CONF_AI_LANGUAGE` default rendering and saving.
- [x] `tests/test_coordinator.py` -- Add tests verifying coordinator extracts `CONF_AI_LANGUAGE` and forwards to prompt assembler.

**Acceptance Criteria:**
- Given an Options Flow dialog for Garmin HA AI, when the user opens the dialog, then `ai_language` is present with dropdown options for System Default, English, German, French, Spanish, Italian, and Dutch.
- Given `CONF_AI_LANGUAGE` set to `"de"` (or `"system"` with HA system language `"de"`), when `assemble_report_prompt` is executed, then Block 5 explicitly mandates that the `<summary>` and all markdown sections must be written in German.
- Given `CONF_AI_LANGUAGE` set to `"es"`, when `assemble_qa_prompt` is executed, then the response instructions explicitly mandate that the answer must be written in Spanish.
- Given an existing config entry with no `ai_language` configured, when reports or Q&A prompts are generated, then prompt assembly executes without error using the default language.
- Given foreign language output inside `<summary>`, when `parse_ai_health_report` parses the response, then `short_summary` is properly extracted and clamped within 250 characters.

## Design Notes

Language resolution maps ISO-639-1 language codes to human-readable language names suitable for LLM directives:
```python
LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
}
```
When `CONF_AI_LANGUAGE` is `"system"`, the helper checks `hass.config.language` (e.g., `"de"` -> `"German"`), defaulting to `"English"` if not found or unmapped.

Block 5 injection:
```
6. LANGUAGE REQUIREMENT: You MUST generate the entire response (including the <summary>...</summary> text and all markdown sections) strictly in {target_language}. Do not output in any other language.
```

## Verification

**Commands:**
- `pytest tests/test_prompt.py tests/test_options_flow.py tests/test_coordinator.py` -- expected: All unit tests pass with 100% success.
- `pytest` -- expected: All 173+ integration and regression tests pass without breakage.

## Suggested Review Order

**Language Resolution & Prompt Assembly**

- Central resolution logic mapping ISO codes and regional locales to English names.
  [`prompt.py:35`](../../custom_components/garmin_ha_ai/ai_engine/prompt.py#L35)

- Strict markdown and summary language constraint injected into Block 5.
  [`prompt.py:342`](../../custom_components/garmin_ha_ai/ai_engine/prompt.py#L342)

- Explicit cross-lingual response instruction injected into interactive Q&A prompt.
  [`prompt.py:414`](../../custom_components/garmin_ha_ai/ai_engine/prompt.py#L414)

**Coordinator Pipeline Integration**

- Configured language extracted from options and forwarded during report generation.
  [`coordinator.py:241`](../../custom_components/garmin_ha_ai/coordinator.py#L241)

- Configured language extracted from options and forwarded during interactive Q&A.
  [`coordinator.py:347`](../../custom_components/garmin_ha_ai/coordinator.py#L347)

**Options Flow Configuration & UI**

- Stored language option validated against supported list with fallback to system.
  [`options_flow.py:125`](../../custom_components/garmin_ha_ai/options_flow.py#L125)

- Dropdown selector exposing language options in integration configuration dialog.
  [`options_flow.py:233`](../../custom_components/garmin_ha_ai/options_flow.py#L233)

- Language configuration keys, defaults, and display mappings defined.
  [`const.py:44`](../../custom_components/garmin_ha_ai/const.py#L44)

**Test Verification**

- Unit tests covering language code resolution, fallback, and regional locale tags.
  [`test_prompt.py:274`](../../tests/test_prompt.py#L274)

- Verification of report Block 5 multilingual directives across multiple languages.
  [`test_prompt.py:354`](../../tests/test_prompt.py#L354)

- Verification of interactive Q&A prompt language instructions.
  [`test_prompt.py:377`](../../tests/test_prompt.py#L377)

- UI options flow schema verification, choice inspection, and persistence tests.
  [`test_options_flow.py:201`](../../tests/test_options_flow.py#L201)

- Fallback verification when invalid language option exists in stored configuration.
  [`test_options_flow.py:238`](../../tests/test_options_flow.py#L238)

- End-to-end coordinator prompt parameter forwarding verification for reports and Q&A.
  [`test_coordinator.py:253`](../../tests/test_coordinator.py#L253)
