"""Button platform for Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GarminDataUpdateCoordinator
from .helpers import get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Garmin HA AI button entities from a config entry.

    Provides on-demand triggers in the Home Assistant UI for report generation
    and interactive Q&A submission.
    """
    coordinator: GarminDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        GarminAIGenerateReportButton(coordinator, entry),
        GarminAIAskQuestionButton(coordinator, entry),
    ])


class GarminAIGenerateReportButton(
    CoordinatorEntity[GarminDataUpdateCoordinator], ButtonEntity
):
    """Button entity to trigger on-demand AI Health Report generation.

    When pressed in the UI or triggered via automation, forces immediate
    health report generation using today's latest metrics and 7-day history.
    """

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
        self._attr_device_info = get_device_info(entry)

    async def async_press(self) -> None:
        """Handle button press to generate AI health report on demand."""
        # force=True bypasses stale checks and generates a fresh report
        await self.coordinator.async_generate_report(force=True)


class GarminAIAskQuestionButton(
    CoordinatorEntity[GarminDataUpdateCoordinator], ButtonEntity
):
    """Button entity to submit current question to AI Coach on demand.

    Reads the question text from the question_input text entity buffer, queries the
    AI model with historical health context, and updates the last answer sensor.
    """

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
        self._attr_device_info = get_device_info(entry)

    async def async_press(self) -> None:
        """Handle button press to submit question to AI Coach."""
        # Delegates to coordinator.async_ask_question which reads coordinator.question_input
        await self.coordinator.async_ask_question()


