"""Tests for Garmin HA AI metric sensor platform."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.garmin_ha_ai.models import GarminDailyMetrics
from custom_components.garmin_ha_ai.sensor import (
    SENSOR_DESCRIPTIONS,
    GarminSensorEntity,
    async_setup_entry,
)


def test_sensor_setup_entry() -> None:
    """Test sensor async_setup_entry registers all sensor entities."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.entry_id = "test_entry_id"

        mock_coordinator = MagicMock()
        mock_hass.data = {"garmin_ha_ai": {"test_entry_id": {"coordinator": mock_coordinator}}}

        added_entities = []

        def add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(mock_hass, mock_entry, add_entities)

        assert len(added_entities) == len(SENSOR_DESCRIPTIONS)
        assert len(added_entities) == 6

    asyncio.run(run())


def test_sensor_entity_state_and_attributes() -> None:
    """Test GarminSensorEntity native value and extra state attributes."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"

    sample_metrics = GarminDailyMetrics(
        date="2026-08-15",
        steps=12000,
        distance_km=9.5,
        total_calories=2600,
        resting_hr=56,
        sleep_score=92,
        avg_stress=22,
        body_battery_min=18,
        body_battery_max=98,
        weight_kg=74.2,
        activities=[{"name": "Evening Walk"}],
    )

    mock_coordinator = MagicMock()
    mock_coordinator.data = sample_metrics

    # Test Steps Sensor
    steps_desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "steps")
    steps_entity = GarminSensorEntity(mock_coordinator, steps_desc, mock_entry)

    assert steps_entity.native_value == 12000
    assert steps_entity.extra_state_attributes["distance_km"] == 9.5
    assert steps_entity.extra_state_attributes["total_calories"] == 2600
    assert steps_entity.extra_state_attributes["activities_count"] == 1

    # Test Body Battery Sensor
    bb_desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "body_battery_min")
    bb_entity = GarminSensorEntity(mock_coordinator, bb_desc, mock_entry)

    assert bb_entity.native_value == 18
    assert bb_entity.extra_state_attributes["body_battery_min"] == 18
    assert bb_entity.extra_state_attributes["body_battery_max"] == 98

    # Test No Data
    mock_coordinator.data = None
    assert steps_entity.native_value is None
    assert steps_entity.extra_state_attributes == {}
