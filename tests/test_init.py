"""Tests for component setup, entry lifecycle, and unload."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.core import HomeAssistant
from custom_components.garmin_ha_ai import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
    async_reload_entry,
)
from custom_components.garmin_ha_ai.const import DOMAIN, PLATFORMS


@pytest.mark.asyncio
async def test_async_setup(hass: HomeAssistant) -> None:
    """Test async_setup registers domain data and services."""
    assert await async_setup(hass, {}) is True
    assert DOMAIN in hass.data


@pytest.mark.asyncio
async def test_async_setup_entry_success(hass: HomeAssistant) -> None:
    """Test async_setup_entry initializes storage, coordinator and forwards platforms."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {}
    entry.options = {}
    entry.add_update_listener = MagicMock()
    entry.async_on_unload = MagicMock()

    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    with patch(
        "custom_components.garmin_ha_ai.coordinator.GarminDataUpdateCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ) as mock_refresh:
        result = await async_setup_entry(hass, entry)

        assert result is True
        assert entry.entry_id in hass.data[DOMAIN]
        assert "storage" in hass.data[DOMAIN][entry.entry_id]
        assert "coordinator" in hass.data[DOMAIN][entry.entry_id]
        mock_refresh.assert_called_once()
        hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            entry, PLATFORMS
        )


@pytest.mark.asyncio
async def test_async_unload_entry_success(hass: HomeAssistant) -> None:
    """Test async_unload_entry cleanly tears down platforms and data."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"dummy": "data"}

    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

    result = await async_unload_entry(hass, entry)

    assert result is True
    assert entry.entry_id not in hass.data[DOMAIN]
    hass.config_entries.async_unload_platforms.assert_called_once_with(entry, PLATFORMS)
