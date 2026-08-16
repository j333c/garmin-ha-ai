"""Frontend registration for Garmin HA AI Lovelace custom cards."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

FRONTEND_URL_BASE = "/garmin_ha_ai_frontend"
FRONTEND_JS_FILE = "garmin-ha-ai-cards.js"
FRONTEND_URL = f"{FRONTEND_URL_BASE}/{FRONTEND_JS_FILE}"
FRONTEND_DIR = Path(__file__).parent / "frontend"
FRONTEND_FILE_PATH = FRONTEND_DIR / FRONTEND_JS_FILE
MANIFEST_PATH = Path(__file__).parent / "manifest.json"

VERSION = "0.1.4"
if MANIFEST_PATH.exists():
    try:
        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        VERSION = manifest_data.get("version", "0.1.4")
    except Exception:
        pass

FRONTEND_URL_VERSIONED = f"{FRONTEND_URL}?v={VERSION}"

_FRONTEND_REGISTERED = False


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register static path and extra JS URL for custom Lovelace cards."""
    global _FRONTEND_REGISTERED

    if _FRONTEND_REGISTERED:
        return

    if not FRONTEND_FILE_PATH.exists():
        LOGGER.warning("Garmin HA AI frontend card file not found at %s", FRONTEND_FILE_PATH)
        return

    # 1. Register static paths with Home Assistant HTTP server
    if hasattr(hass, "http") and hass.http is not None:
        try:
            if hasattr(hass.http, "async_register_static_paths"):
                from homeassistant.components.http import StaticPathConfig

                await hass.http.async_register_static_paths(
                    [
                        StaticPathConfig(
                            url_path=FRONTEND_URL_BASE,
                            path=str(FRONTEND_DIR),
                            cache_headers=False,
                        ),
                        StaticPathConfig(
                            url_path=FRONTEND_URL,
                            path=str(FRONTEND_FILE_PATH),
                            cache_headers=False,
                        ),
                    ]
                )
                LOGGER.debug("Registered frontend static paths via async_register_static_paths: %s", FRONTEND_URL_BASE)
            elif hasattr(hass.http, "register_static_path"):
                hass.http.register_static_path(
                    FRONTEND_URL_BASE,
                    str(FRONTEND_DIR),
                    cache_headers=False,
                )
                LOGGER.debug("Registered frontend static path via register_static_path: %s", FRONTEND_URL_BASE)
        except Exception as err:
            LOGGER.warning("Could not register static path for Garmin HA AI cards: %s", err)

    # 2. Copy to /config/www/garmin-ha-ai-cards.js as fallback if www directory exists
    try:
        def _copy_to_www() -> None:
            if hasattr(hass, "config") and hasattr(hass.config, "path"):
                www_dir = Path(hass.config.path("www"))
                if www_dir.exists() and www_dir.is_dir():
                    dest_file = www_dir / FRONTEND_JS_FILE
                    import shutil
                    shutil.copyfile(FRONTEND_FILE_PATH, dest_file)
                    LOGGER.debug("Copied frontend cards file to %s", dest_file)

        await hass.async_add_executor_job(_copy_to_www)
    except Exception as err:
        LOGGER.debug("Could not copy cards file to www directory: %s", err)

    # 3. Add extra JS URL to Home Assistant frontend so Lovelace loads it automatically
    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, FRONTEND_URL_VERSIONED)
        LOGGER.info("Successfully registered Garmin HA AI custom Lovelace cards: %s", FRONTEND_URL_VERSIONED)
        _FRONTEND_REGISTERED = True
    except (ImportError, AttributeError, Exception) as err:
        LOGGER.debug("Could not add extra JS URL to frontend (may be running in test or headless mode): %s", err)
        _FRONTEND_REGISTERED = True

    # 4. Auto-register in Lovelace resources storage if available
    try:
        lovelace_data = hass.data.get("lovelace")
        if lovelace_data and hasattr(lovelace_data, "resources"):
            resources = lovelace_data.resources
            if hasattr(resources, "async_create_item") and hasattr(resources, "async_items"):
                items = resources.async_items()
                if not any(item.get("url", "").startswith(FRONTEND_URL) for item in items):
                    await resources.async_create_item({"res_type": "module", "url": FRONTEND_URL_VERSIONED})
                    LOGGER.debug("Auto-registered Garmin HA AI cards in Lovelace resources")
    except Exception as err:
        LOGGER.debug("Lovelace resources auto-registration skipped: %s", err)
