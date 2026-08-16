"""Frontend registration for Garmin HA AI Lovelace custom cards."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

FRONTEND_URL_BASE = "/garmin_ha_ai_frontend"
FRONTEND_JS_FILE = "garmin-ha-ai-cards.js"
FRONTEND_URL = f"{FRONTEND_URL_BASE}/{FRONTEND_JS_FILE}"
FRONTEND_DIR = Path(__file__).parent / "frontend"
FRONTEND_FILE_PATH = FRONTEND_DIR / FRONTEND_JS_FILE

_FRONTEND_REGISTERED = False


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register static path and extra JS URL for custom Lovelace cards."""
    global _FRONTEND_REGISTERED

    if _FRONTEND_REGISTERED:
        return

    if not FRONTEND_FILE_PATH.exists():
        LOGGER.warning("Garmin HA AI frontend card file not found at %s", FRONTEND_FILE_PATH)
        return

    # 1. Register static path with Home Assistant HTTP server
    if hasattr(hass, "http") and hass.http is not None:
        try:
            if hasattr(hass.http, "async_register_static_paths"):
                from homeassistant.components.http import StaticPathConfig

                await hass.http.async_register_static_paths(
                    [
                        StaticPathConfig(
                            url_path=FRONTEND_URL,
                            path=str(FRONTEND_FILE_PATH),
                            cache_headers=True,
                        )
                    ]
                )
                LOGGER.debug("Registered frontend static path via async_register_static_paths: %s", FRONTEND_URL)
            elif hasattr(hass.http, "register_static_path"):
                hass.http.register_static_path(
                    FRONTEND_URL,
                    str(FRONTEND_FILE_PATH),
                    cache_headers=True,
                )
                LOGGER.debug("Registered frontend static path via register_static_path: %s", FRONTEND_URL)
        except Exception as err:
            LOGGER.warning("Could not register static path for Garmin HA AI cards: %s", err)

    # 2. Add extra JS URL to Home Assistant frontend so Lovelace loads it automatically
    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, FRONTEND_URL)
        LOGGER.info("Successfully registered Garmin HA AI custom Lovelace cards: %s", FRONTEND_URL)
        _FRONTEND_REGISTERED = True
    except (ImportError, AttributeError, Exception) as err:
        LOGGER.debug("Could not add extra JS URL to frontend (may be running in test or headless mode): %s", err)
        _FRONTEND_REGISTERED = True
