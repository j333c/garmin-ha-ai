---
title: 'Options Flow Time Picker & Schedule Selector Refinement'
type: 'feature'
created: '2026-08-16'
status: 'done'
context:
  - 'custom_components/garmin_ha_ai/options_flow.py'
  - 'custom_components/garmin_ha_ai/strings.json'
  - 'custom_components/garmin_ha_ai/translations/en.json'
  - 'custom_components/garmin_ha_ai/translations/de.json'
---

## Intent

**Problem:**
In Settings -> Options, the "Tägliche Abrufzeit" / Polling Schedule setting is a free text input field instead of an interactive time picker widget.

**Approach:**
1. Update `options_flow.py` to use `selector({"time": {}})` for `CONF_POLLING_SCHEDULE`.
2. Update translations in `strings.json`, `translations/en.json`, and `translations/de.json`.
3. Ensure both `HH:MM:SS` and `HH:MM` time strings are accepted and normalized.

## Tasks & Acceptance

- [x] Update `options_flow.py` with `TimeSelector`.
- [x] Update translation JSON files.
- [x] Add tests in `tests/test_options_flow.py`.
