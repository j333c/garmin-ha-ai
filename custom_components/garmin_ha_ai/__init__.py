"""The Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_RETENTION_DAYS,
    DEFAULT_RETENTION_DAYS,
    DOMAIN,
    LOGGER,
    PLATFORMS,
)
from .coordinator import GarminDataUpdateCoordinator
from .frontend import async_setup_frontend
from .garmin_client import GarminClient
from .services import async_setup_services
from .storage import GarminStorage


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update by reloading config entry and pruning history.

    Invoked whenever the user modifies settings via the integration Options flow.
    """
    storage = GarminStorage(hass)
    retention_days = entry.options.get(
        CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS
    )
    await storage.async_prune_history(retention_days)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Garmin HA AI component at Home Assistant startup.

    Registers custom services (generate_report, ask_question) and frontend card assets.
    """
    hass.data.setdefault(DOMAIN, {})
    await async_setup_services(hass)
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Garmin HA AI from a config entry.

    Initializes local storage, Garmin API adapter, DataUpdateCoordinator, and forwards
    entity setup to all supported platforms (sensor, button, text, select).
    """
    hass.data.setdefault(DOMAIN, {})
    await async_setup_frontend(hass)

    # 1. Instantiate persistence, API client, and update coordinator
    storage = GarminStorage(hass)
    client = GarminClient(hass, storage)
    coordinator = GarminDataUpdateCoordinator(hass, entry, client, storage)

    # 2. Perform initial background fetch to populate coordinator data
    await coordinator.async_config_entry_first_refresh()

    # 3. Store instances in hass.data registry for cross-component access
    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "client": client,
        "coordinator": coordinator,
    }

    LOGGER.debug("Setting up Garmin HA AI entry: %s", entry.entry_id)

    # 4. Attach update listener for dynamic options reload
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # 5. Forward setup to entity platforms (sensor, button, text, select)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Garmin HA AI config entry and clean up data storage."""
    LOGGER.debug("Unloading Garmin HA AI entry: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok

