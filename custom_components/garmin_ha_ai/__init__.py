"""The Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER, PLATFORMS


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Garmin HA AI component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Garmin HA AI from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    LOGGER.debug("Setting up Garmin HA AI entry: %s", entry.entry_id)

    # Forward setup to platforms once implemented
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Garmin HA AI config entry."""
    LOGGER.debug("Unloading Garmin HA AI entry: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
