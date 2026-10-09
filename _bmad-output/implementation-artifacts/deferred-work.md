- source_spec: none
  summary: Dashboard Usability Overhaul — Weight Display, Resilient Gauges & Responsive Layout (Story 10.2)
  evidence: Split during Epic 10 multi-goal scope check to implement backend multilingual AI response preference (Story 10.1) first.
- source_spec: `_bmad-output/implementation-artifacts/spec-10-1-ai-response-language-preference-in-options-flow-prompt.md`
  summary: Localize notification titles and fallback messages in coordinator.py based on configured AI language.
  evidence: Surfaced during Story 10.1 adversarial code review; coordinator.py async_dispatch_notification uses hardcoded English notification title and fallback text.

## Deferred from: code review of spec-10-1-ai-response-language-preference-in-options-flow-prompt.md (2026-10-09)

- **Language override in services**: Support ad-hoc `language` parameter in `services.py` and `services.yaml` for `garmin_ha_ai.ask_question` and `garmin_ha_ai.generate_report` (`custom_components/garmin_ha_ai/services.py:27`).
- **Language selection in onboarding wizard**: Expose `CONF_AI_LANGUAGE` selector during initial integration setup flow (`custom_components/garmin_ha_ai/config_flow.py:86`).
- **Additional UI translations**: Add complete UI translation catalogs for `fr.json`, `es.json`, `it.json`, and `nl.json` (`custom_components/garmin_ha_ai/translations/`).
