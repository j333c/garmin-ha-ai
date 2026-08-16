"""The Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

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
    """Handle options update by reloading config entry and pruning history."""
    storage = GarminStorage(hass)
    retention_days = entry.options.get(
        CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS
    )
    await storage.async_prune_history(retention_days)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Garmin HA AI component."""
    hass.data.setdefault(DOMAIN, {})
    await async_setup_services(hass)
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Garmin HA AI from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await async_setup_frontend(hass)

    storage = GarminStorage(hass)
    client = GarminClient(hass, storage)
    coordinator = GarminDataUpdateCoordinator(hass, entry, client, storage)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "client": client,
        "coordinator": coordinator,
    }

    LOGGER.debug("Setting up Garmin HA AI entry: %s", entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Garmin HA AI config entry."""
    LOGGER.debug("Unloading Garmin HA AI entry: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
