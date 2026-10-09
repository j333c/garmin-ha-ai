# Epic 10 Context: Multilingual AI Coaching & Dashboard Usability Revamp

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Enable users to configure their preferred coaching language in the Options Flow (English, German, French, Spanish, Italian, Dutch, or System), ensuring that daily AI health briefings, executive summaries, and interactive Q&A answers are generated strictly in their chosen language. Additionally, overhaul Lovelace frontend cards for improved desktop and mobile usability, incorporating a dedicated Weight metric display, graceful pending morning sync indicators (`⏳ Syncing...`), and thumb-friendly touch targets.

## Stories

- Story 10.1: AI Response Language Preference in Options Flow & Prompt Assembler (`options_flow.py`, `prompt.py`, `const.py`)
- Story 10.2: Dashboard Usability Overhaul — Weight Display, Resilient Gauges & Responsive Layout (`frontend/garmin-ha-ai-cards.js`)

## Requirements & Constraints

- **FR-22 / AI Response Language Preference**: Provide language selection option (`en`, `de`, `fr`, `es`, `it`, `nl`, `system`) in Options Flow (`CONF_AI_LANGUAGE`), persisting in config entry options. Inject strict multilingual directives into the AI prompt assembler (`prompt.py`) and system prompt so both the `<summary>` (and truncated state) and full markdown report conform to the selected language.
- **FR-23 / Dashboard Usability & Metric Visibility Overhaul**: Frontend cards (`garmin-ha-ai-cards.js`) must render a dedicated Weight metric pill/tile with unit `kg`. Unfinalized metrics pending morning sync must display a subtle pending indicator (`⏳ Syncing...`) instead of `--`.
- **UX-DR-1 & UX-DR-2 / Visual Identity & Touch Navigation**: Ensure high contrast, consistent theme variable utilization, and thumb-friendly touch targets (minimum 44x44px).
- **FR-10 & FR-14**: Preserve 250-character limit protection for sensor state strings while full response and long report remain in entity extra state attributes.

## Technical Decisions

- **Configuration Key**: Define `CONF_AI_LANGUAGE = "ai_language"` and supported language constants in `const.py` (default: `"system"` or `"en"`, mapped to system language or specific ISO code).
- **Prompt Directive Injection**: In `prompt.py` (`PromptAssembler` / prompt templates), add a dedicated directive block or rule enforcing response output language across both daily reports and interactive Q&A queries.
- **Options Flow UI**: Add language dropdown in `options_flow.py` within the AI configuration step or general settings step.
- **Frontend Card Updates**: Update `frontend/garmin-ha-ai-cards.js` to render the weight sensor and handle pending states gracefully.

## UX & Interaction Patterns

- **Language Selector**: Dropdown selector in Options Flow under AI Settings with human-friendly labels (e.g. English, Deutsch, Français, Español, Italiano, Nederlands, System / Default).
- **Card Badges & Pills**: Weight badge/tile alongside steps, heart rate, sleep score, and body battery.
- **Pending Sync State**: Display ⏳ Syncing... or localized pending indicator when sensor is unknown/unavailable or in initial sync.

## Cross-Story Dependencies

- **Story 10.1 -> Story 10.2**: Independent deliverables. Story 10.1 focuses on backend options flow and prompt engineering, while Story 10.2 focuses on frontend card rendering.
