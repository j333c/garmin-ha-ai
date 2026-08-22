"""Shared helper utilities for Garmin HA AI integration."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    pass


def get_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return standard Home Assistant DeviceInfo for Garmin HA AI entities.

    This binds all entities (sensors, buttons, text inputs, selects) created by
    the integration under a single unified Device in the Home Assistant Device Registry.
    """
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Garmin AI ({entry.title})",
        manufacturer="Garmin HA AI",
        model="Garmin Connect Health AI Integration",
    )


def truncate_entity_state(
    text: str | None,
    max_len: int = 250,
    placeholder: str = "No data available",
) -> str:
    """Truncate text to fit safely within Home Assistant's 255-character state string limit.

    Home Assistant's state machine strictly limits entity states to 255 characters.
    We enforce a safety threshold of max_len (default 250 characters) to leave headroom
    and append an ellipsis ('...') if the text exceeds this limit. Full text is stored
    in entity extra_state_attributes.

    Args:
        text: The source string to be set as entity state.
        max_len: Maximum allowed character length (strictly < 255, default 250).
        placeholder: Text returned if input text is empty or None.

    Returns:
        A safely truncated string guaranteed not to exceed max_len.
    """
    if text is None:
        return placeholder

    cleaned = str(text).strip()
    if not cleaned:
        return placeholder

    # If the text exceeds the maximum character threshold, truncate and append ellipsis
    if len(cleaned) > max_len:
        return cleaned[: max_len - 3] + "..."

    return cleaned
