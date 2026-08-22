"""Text platform for Garmin HA AI integration."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
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
    """Set up Garmin HA AI text entities from a config entry.

    Registers the interactive question input buffer for Lovelace Q&A cards.
    """
    coordinator: GarminDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([GarminAIQuestionTextEntity(coordinator, entry)])


class GarminAIQuestionTextEntity(
    CoordinatorEntity[GarminDataUpdateCoordinator], TextEntity
):
    """Text entity allowing the user to type questions for the AI coach.

    Maintains the question string in coordinator memory so that pressing the
    'Garmin AI Ask Question' button or submitting from a custom Lovelace card
    submits this exact query.
    """

    _attr_icon = "mdi:chat-question-outline"
    _attr_mode = TextMode.TEXT

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_question_input"
        self._attr_name = "Garmin AI Question"
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> str:
        """Return the current text value from coordinator state."""
        return self.coordinator.question_input

    async def async_set_value(self, value: str) -> None:
        """Set the text value in coordinator and notify listeners."""
        # Updates question buffer in coordinator state
        self.coordinator.set_question_input(value)

