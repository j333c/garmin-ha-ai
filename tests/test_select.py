"""Tests for Garmin HA AI select entity platform."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.garmin_ha_ai.const import (
    DOMAIN,
    REPORT_VIEW_LONG,
    REPORT_VIEW_OPTIONS,
    REPORT_VIEW_QA,
    REPORT_VIEW_SHORT,
)
from custom_components.garmin_ha_ai.select import (
    GarminAIReportDisplayModeSelectEntity,
    async_setup_entry,
)


def test_select_setup_entry() -> None:
    """Test select async_setup_entry registers GarminAIReportDisplayModeSelectEntity."""

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
        select_entity = added_entities[0]
        assert isinstance(select_entity, GarminAIReportDisplayModeSelectEntity)
        assert select_entity.unique_id == "test_entry_id_report_display_mode"
        assert select_entity.name == "Garmin AI Report View"
        assert select_entity.options == REPORT_VIEW_OPTIONS

    asyncio.run(run())


def test_select_entity_options_and_selection() -> None:
    """Test GarminAIReportDisplayModeSelectEntity options and async_select_option."""

    async def run() -> None:
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.title = "Test User"

        mock_coordinator = MagicMock()
        mock_coordinator.report_display_mode = REPORT_VIEW_SHORT

        select_entity = GarminAIReportDisplayModeSelectEntity(mock_coordinator, mock_entry)
        assert select_entity.current_option == REPORT_VIEW_SHORT
        assert select_entity.options == [
            REPORT_VIEW_SHORT,
            REPORT_VIEW_LONG,
            REPORT_VIEW_QA,
        ]

        await select_entity.async_select_option(REPORT_VIEW_LONG)
        mock_coordinator.set_report_display_mode.assert_called_once_with(REPORT_VIEW_LONG)

    asyncio.run(run())
