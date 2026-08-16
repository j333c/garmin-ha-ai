---
title: 'On-Demand Report Button Entity & Interactive Q&A Dashboard Patterns'
type: 'feature'
created: '2026-08-16'
status: 'done'
context:
  - 'custom_components/garmin_ha_ai/button.py'
  - 'custom_components/garmin_ha_ai/__init__.py'
  - 'custom_components/garmin_ha_ai/const.py'
  - 'docs/dashboard_cards.md'
  - 'README.md'
---

## Intent

**Problem:**
1. Users want a one-click dashboard button entity to generate AI health reports on demand.
2. Users need ready-to-use Lovelace dashboard YAML examples for interactive Q&A text fields and report generation.

**Approach:**
1. Add `Platform.BUTTON` to `PLATFORMS` in `const.py`.
2. Implement `button.py` with `GarminAIGenerateReportButton` entity calling `coordinator.async_generate_report(force=True)`.
3. Create `docs/dashboard_cards.md` and update `README.md` with complete Lovelace dashboard card configurations for on-demand report button and interactive text-input Q&A.

## Tasks & Acceptance

- [x] Implement `custom_components/garmin_ha_ai/button.py`.
- [x] Register button platform in `const.py` and `__init__.py`.
- [x] Create `docs/dashboard_cards.md`.
- [x] Add tests in `tests/test_button.py`.
