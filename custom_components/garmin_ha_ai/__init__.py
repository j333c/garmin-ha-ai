"""The Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, LOGGER, PLATFORMS, SERVICE_GENERATE_REPORT
from .coordinator import GarminDataUpdateCoordinator
from .garmin_client import GarminClient
from .storage import GarminStorage


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Garmin HA AI component."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_generate_report(call: ServiceCall) -> None:
        """Handle generate_report service call."""
        domain_data = hass.data.get(DOMAIN, {})
        for entry_id, entry_data in domain_data.items():
            if isinstance(entry_data, dict) and "coordinator" in entry_data:
                coordinator: GarminDataUpdateCoordinator = entry_data["coordinator"]
                await coordinator.async_generate_report(force=True)

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_REPORT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GENERATE_REPORT,
            handle_generate_report,
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Garmin HA AI from a config entry."""
    hass.data.setdefault(DOMAIN, {})

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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Garmin HA AI config entry."""
    LOGGER.debug("Unloading Garmin HA AI entry: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
