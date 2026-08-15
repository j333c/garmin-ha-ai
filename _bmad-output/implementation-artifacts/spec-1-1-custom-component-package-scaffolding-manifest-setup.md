---
title: 'Story 1.1: Custom Component Package Scaffolding & Manifest Setup'
type: 'feature'
created: '2026-08-15'
status: 'done'
baseline_commit: 'aed1a876d465b93518baa6139a9aef4c5d04f85c'
review_loop_iteration: 0
context: ['AGENTS.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The `garmin-ha-ai` custom component needs a standard Home Assistant integration directory structure, manifest configuration, and global constant definitions so Home Assistant Core recognizes the integration and manages its dependencies.

**Approach:** Create `custom_components/garmin_ha_ai/` package containing `manifest.json` with required PyPI packages (`garminconnect`, `google-genai`, `httpx`), `const.py` for global constants and defaults, and `__init__.py` with standard component setup/unload lifecycle handlers.

## Boundaries & Constraints

**Always:** Follow Home Assistant Custom Component integration structure standards. Maintain `domain: garmin_ha_ai`. Sanitize all logs. Never perform blocking synchronous network or file I/O in the main event loop.

**Ask First:** Changing dependency versions or domain name.

**Never:** Store plaintext passwords or sensitive credentials in constants or manifest.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Component Load | Home Assistant startup scanning `custom_components/garmin_ha_ai/` | Manifest validated, PyPI requirements (`garminconnect`, `google-genai`, `httpx`) resolved | Log error in HA logs if manifest JSON syntax is invalid |
| Setup Entry | ConfigEntry passed to `async_setup_entry` | Config entry runtime data stored in `hass.data[DOMAIN][entry.entry_id]` | Returns `False` if setup fails |
| Unload Entry | ConfigEntry unloaded via HA UI | Data cleaned up from `hass.data[DOMAIN]`, returns `True` | Returns `False` if unloading entry fails |

</frozen-after-approval>

## Code Map

- `custom_components/garmin_ha_ai/manifest.json` -- HA Integration Manifest defining domain, dependencies, version, and config flow flags.
- `custom_components/garmin_ha_ai/const.py` -- Centralized domain constants, config keys, default values, AI provider identifiers.
- `custom_components/garmin_ha_ai/__init__.py` -- Integration entry point managing setup, entry lifecycle (`async_setup_entry`, `async_unload_entry`).

## Tasks & Acceptance

**Execution:**
- [x] `custom_components/garmin_ha_ai/manifest.json` -- Create integration manifest -- Defines domain `garmin_ha_ai`, version `1.0.0`, `config_flow: true`, and PyPI requirements (`garminconnect>=0.3.10`, `google-genai>=1.0.0`, `httpx>=0.27.0`).
- [x] `custom_components/garmin_ha_ai/const.py` -- Create domain constants -- Centralizes `DOMAIN`, configuration option keys, default settings, AI provider constants.
- [x] `custom_components/garmin_ha_ai/__init__.py` -- Create component lifecycle entrypoint -- Implements `async_setup`, `async_setup_entry`, and `async_unload_entry`.

**Acceptance Criteria:**
- Given a standard Home Assistant Core installation, when the package is placed under `custom_components/garmin_ha_ai/`, then Home Assistant loads `manifest.json` with `domain: garmin_ha_ai`, version `1.0.0`, `config_flow: true`, and PyPI requirements (`garminconnect>=0.3.10`, `google-genai>=1.0.0`, `httpx>=0.27.0`).
- Given the `garmin_ha_ai` integration code, when imported, then `const.py` provides centralized definitions for `DOMAIN`, configuration keys, default options, and provider constants.

## Design Notes

Centralized constants in `const.py`:
- `DOMAIN = "garmin_ha_ai"`
- `CONF_GARMIN_USERNAME = "username"`
- `CONF_GARMIN_PASSWORD = "password"`
- `CONF_AI_PROVIDER = "ai_provider"`
- `CONF_AI_API_KEY = "ai_api_key"`
- `CONF_AI_MODEL = "ai_model"`
- `CONF_AI_BASE_URL = "ai_base_url"`
- `PROVIDER_GEMINI = "gemini"`
- `PROVIDER_OPENAI = "openai"`
- `DEFAULT_AI_MODEL_GEMINI = "gemini-2.0-flash"`
- `DEFAULT_POLLING_INTERVAL_HOURS = 24`

## Verification

**Manual checks (if no CLI):**
- Validate `manifest.json` is valid JSON and contains required keys (`domain`, `name`, `config_flow`, `requirements`, `version`).
- Validate `__init__.py` and `const.py` parse without Python syntax errors (`python3 -m py_compile custom_components/garmin_ha_ai/__init__.py custom_components/garmin_ha_ai/const.py`).

## Suggested Review Order

**Component Scaffolding & Manifest**

- Defines integration domain, metadata, and dependencies required by Home Assistant Core.
  [`manifest.json:1`](../../custom_components/garmin_ha_ai/manifest.json#L1)

- Establishes global domain constants, configuration keys, default options, and provider identifiers.
  [`const.py:1`](../../custom_components/garmin_ha_ai/const.py#L1)

- Implements standard Home Assistant component setup and entry lifecycle handlers.
  [`__init__.py:1`](../../custom_components/garmin_ha_ai/__init__.py#L1)

