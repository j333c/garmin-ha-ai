"""Tests for Garmin HA AI text entity platform."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.garmin_ha_ai.const import DOMAIN
from custom_components.garmin_ha_ai.text import (
    GarminAIQuestionTextEntity,
    async_setup_entry,
)


def test_text_setup_entry() -> None:
    """Test text async_setup_entry registers GarminAIQuestionTextEntity."""

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
        text_entity = added_entities[0]
        assert isinstance(text_entity, GarminAIQuestionTextEntity)
        assert text_entity.unique_id == "test_entry_id_question_input"
        assert text_entity.name == "Garmin AI Question"

    asyncio.run(run())


def test_text_entity_native_value_and_set_value() -> None:
    """Test GarminAIQuestionTextEntity native value and async_set_value."""

    async def run() -> None:
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"
        mock_entry.title = "Test User"

        mock_coordinator = MagicMock()
        mock_coordinator.question_input = "Initial question?"

        text_entity = GarminAIQuestionTextEntity(mock_coordinator, mock_entry)
        assert text_entity.native_value == "Initial question?"

        await text_entity.async_set_value("New question for AI?")
        mock_coordinator.set_question_input.assert_called_once_with("New question for AI?")

    asyncio.run(run())
