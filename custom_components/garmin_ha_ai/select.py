"""Select platform for Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REPORT_VIEW_OPTIONS
from .coordinator import GarminDataUpdateCoordinator


def _get_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return standard DeviceInfo for Garmin HA AI entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Garmin AI ({entry.title})",
        manufacturer="Garmin HA AI",
        model="Garmin Connect Health AI Integration",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Garmin HA AI select entities from a config entry."""
    coordinator: GarminDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([GarminAIReportDisplayModeSelectEntity(coordinator, entry)])


class GarminAIReportDisplayModeSelectEntity(
    CoordinatorEntity[GarminDataUpdateCoordinator], SelectEntity
):
    """Select entity allowing the user to toggle which AI report or answer is displayed."""

    _attr_icon = "mdi:view-dashboard-outline"
    _attr_options = REPORT_VIEW_OPTIONS

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_report_display_mode"
        self._attr_name = "Garmin AI Report View"
        self._attr_device_info = _get_device_info(entry)

    @property
    def current_option(self) -> str | None:
        """Return the selected report display mode."""
        return self.coordinator.report_display_mode

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        self.coordinator.set_report_display_mode(option)
