"""Tests for shared helper utilities in Garmin HA AI integration."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.garmin_ha_ai.const import DOMAIN
from custom_components.garmin_ha_ai.helpers import (
    get_device_info,
    truncate_entity_state,
)


def test_get_device_info() -> None:
    """Test get_device_info generates consistent DeviceInfo."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_123"
    mock_entry.title = "test_user@example.com"

    dev_info = get_device_info(mock_entry)
    assert dev_info["identifiers"] == {(DOMAIN, "test_entry_123")}
    assert dev_info["name"] == "Garmin AI (test_user@example.com)"
    assert dev_info["manufacturer"] == "Garmin HA AI"
    assert dev_info["model"] == "Garmin Connect Health AI Integration"


def test_truncate_entity_state_none_and_empty() -> None:
    """Test truncate_entity_state with None and empty inputs."""
    assert truncate_entity_state(None) == "No data available"
    assert truncate_entity_state("", placeholder="Fallback") == "Fallback"
    assert truncate_entity_state("   ", placeholder="Empty") == "Empty"


def test_truncate_entity_state_within_limit() -> None:
    """Test truncate_entity_state with strings within character limit."""
    short_text = "Today you walked 12,000 steps with great recovery."
    assert truncate_entity_state(short_text, max_len=250) == short_text


def test_truncate_entity_state_exceeding_limit() -> None:
    """Test truncate_entity_state with strings exceeding character limit."""
    long_text = "A" * 300
    truncated = truncate_entity_state(long_text, max_len=250)
    assert len(truncated) == 250
    assert truncated.endswith("...")
    assert truncated == "A" * 247 + "..."
