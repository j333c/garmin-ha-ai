"""Tests for Garmin HA AI button entity platform."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.garmin_ha_ai.button import (
    GarminAIAskQuestionButton,
    GarminAIGenerateReportButton,
    async_setup_entry,
)
from custom_components.garmin_ha_ai.const import DOMAIN


def test_button_setup_entry() -> None:
    """Test button async_setup_entry registers both report and ask question buttons."""

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

        assert len(added_entities) == 2
        gen_btn = added_entities[0]
        ask_btn = added_entities[1]

        assert isinstance(gen_btn, GarminAIGenerateReportButton)
        assert gen_btn.unique_id == "test_entry_id_generate_report"
        assert gen_btn.name == "Garmin AI Generate Report"

        assert isinstance(ask_btn, GarminAIAskQuestionButton)
        assert ask_btn.unique_id == "test_entry_id_ask_question"
        assert ask_btn.name == "Garmin AI Ask Question"

    asyncio.run(run())


def test_button_async_press() -> None:
    """Test button async_press calls coordinator methods."""

    async def run() -> None:
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.title = "Test User"

        mock_coordinator = MagicMock()
        mock_coordinator.async_generate_report = AsyncMock()
        mock_coordinator.async_ask_question = AsyncMock()

        gen_btn = GarminAIGenerateReportButton(mock_coordinator, mock_entry)
        await gen_btn.async_press()
        mock_coordinator.async_generate_report.assert_called_once_with(force=True)

        ask_btn = GarminAIAskQuestionButton(mock_coordinator, mock_entry)
        await ask_btn.async_press()
        mock_coordinator.async_ask_question.assert_called_once()

    asyncio.run(run())
