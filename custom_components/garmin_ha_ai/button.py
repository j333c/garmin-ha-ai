"""Button platform for Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
    """Set up Garmin HA AI button entities from a config entry."""
    coordinator: GarminDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        GarminAIGenerateReportButton(coordinator, entry),
        GarminAIAskQuestionButton(coordinator, entry),
    ])


class GarminAIGenerateReportButton(
    CoordinatorEntity[GarminDataUpdateCoordinator], ButtonEntity
):
    """Button entity to trigger on-demand AI Health Report generation."""

    _attr_icon = "mdi:creation"

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize Garmin AI generate report button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_generate_report"
        self._attr_name = "Garmin AI Generate Report"
        self._attr_device_info = _get_device_info(entry)

    async def async_press(self) -> None:
        """Handle button press to generate AI health report on demand."""
        await self.coordinator.async_generate_report(force=True)


class GarminAIAskQuestionButton(
    CoordinatorEntity[GarminDataUpdateCoordinator], ButtonEntity
):
    """Button entity to submit current question to AI Coach on demand."""

    _attr_icon = "mdi:send"

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize Garmin AI ask question button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ask_question"
        self._attr_name = "Garmin AI Ask Question"
        self._attr_device_info = _get_device_info(entry)

    async def async_press(self) -> None:
        """Handle button press to submit question to AI Coach."""
        await self.coordinator.async_ask_question()

