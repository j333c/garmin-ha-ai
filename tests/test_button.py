"""Tests for Garmin HA AI button entity platform."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.garmin_ha_ai.button import (
    GarminAIGenerateReportButton,
    async_setup_entry,
)
from custom_components.garmin_ha_ai.const import DOMAIN


def test_button_setup_entry() -> None:
    """Test button async_setup_entry registers GarminAIGenerateReportButton."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.title = "Test User"

        mock_coordinator = MagicMock()
        mock_hass.data = {DOMAIN: {"test_entry_id": {"coordinator": mock_coordinator}}}

        added_entities = []

        def add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, add_entities)

        assert len(added_entities) == 1
        button = added_entities[0]
        assert isinstance(button, GarminAIGenerateReportButton)
        assert button.unique_id == "test_entry_id_generate_report"
        assert button.name == "Garmin AI Generate Report"

    asyncio.run(run())


def test_button_async_press() -> None:
    """Test button async_press calls coordinator.async_generate_report with force=True."""

    async def run() -> None:
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.title = "Test User"

        mock_coordinator = MagicMock()
        mock_coordinator.async_generate_report = AsyncMock()

        button = GarminAIGenerateReportButton(mock_coordinator, mock_entry)
        await button.async_press()

        mock_coordinator.async_generate_report.assert_called_once_with(force=True)

    asyncio.run(run())
