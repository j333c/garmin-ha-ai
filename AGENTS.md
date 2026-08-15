<!-- bmad:context -->
<!-- Verified 2026-08-15 against 1395bc7. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## garmin-ha-ai

Home Assistant custom component integration for Garmin Connect health data and AI analysis. Python 3.12+, Home Assistant Custom Component integration structure. Specifications live in `_bmad-output/specs/spec-garmin-ha-ai/SPEC.md`, architecture in `_bmad-output/planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/ARCHITECTURE-SPINE.md`.

## Policy

- Never log Garmin credentials, MFA tokens, or raw user health payload data — sanitize all logs.
- Never make blocking synchronous network or I/O calls in the main event loop — use Home Assistant async executor wrappers.

## Where things are

- Integration entry points: `custom_components/garmin_ha_ai/__init__.py` and `config_flow.py` [TODO: created during implementation]
- Specifications & API contracts: `_bmad-output/specs/spec-garmin-ha-ai/SPEC.md`
- Architecture & solution design: `_bmad-output/planning-artifacts/architecture/architecture-garmin-ha-ai-2026-08-15/ARCHITECTURE-SPINE.md`

## Running and verifying

- TODO: Run `pytest` inside the python virtual environment once test suites are created during implementation.

## Conventions that differ from defaults

- Store long AI response narratives in entity extra state attributes; Home Assistant entity state strings truncate after 255 characters.
- Access local storage via Home Assistant `Store` helper (`homeassistant.helpers.storage.Store`); never perform raw file I/O directly.

## Known pitfalls

- Handle Garmin MFA authentication gracefully via reauth flow; session tokens periodically expire requiring user re-authentication.

<!-- /bmad:context -->
