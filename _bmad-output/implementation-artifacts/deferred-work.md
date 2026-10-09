- source_spec: none
  summary: Dashboard Usability Overhaul — Weight Display, Resilient Gauges & Responsive Layout (Story 10.2)
  evidence: Split during Epic 10 multi-goal scope check to implement backend multilingual AI response preference (Story 10.1) first.
- source_spec: `_bmad-output/implementation-artifacts/spec-10-1-ai-response-language-preference-in-options-flow-prompt.md`
  summary: Localize notification titles and fallback messages in coordinator.py based on configured AI language.
  evidence: Surfaced during Story 10.1 adversarial code review; coordinator.py async_dispatch_notification uses hardcoded English notification title and fallback text.
