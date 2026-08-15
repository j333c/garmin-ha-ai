"""Tests for Garmin HA AI metric sensor platform."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.garmin_ha_ai.models import AIHealthReport, GarminDailyMetrics
from custom_components.garmin_ha_ai.sensor import (
    SENSOR_DESCRIPTIONS,
    GarminAIHealthReportLongSensor,
    GarminAIHealthReportShortSensor,
    GarminAILastAnswerSensor,
    GarminSensorEntity,
    async_setup_entry,
)


def test_sensor_setup_entry() -> None:
    """Test sensor async_setup_entry registers metric and report sensor entities."""

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

        # 6 metric sensors + 2 report sensors + 1 last answer sensor = 9 total
        assert len(added_entities) == len(SENSOR_DESCRIPTIONS) + 3
        assert len(added_entities) == 9

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


def test_ai_health_report_sensors() -> None:
    """Test short and long AI Health Report sensors and 255-character protection."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_coordinator = MagicMock()

    # Case 1: No report generated yet
    mock_coordinator.latest_report = None
    short_sensor = GarminAIHealthReportShortSensor(mock_coordinator, mock_entry)
    long_sensor = GarminAIHealthReportLongSensor(mock_coordinator, mock_entry)

    assert short_sensor.native_value == "No report generated yet"
    assert short_sensor.extra_state_attributes == {}
    assert long_sensor.native_value == "No report generated yet"
    assert long_sensor.extra_state_attributes == {}

    # Case 2: Extremely long report summary (> 255 chars)
    very_long_summary = "A" * 400
    full_markdown_report = "# Daily Health Report\n\n" + ("Detailed analysis text.\n" * 50)
    sample_report = AIHealthReport(
        timestamp="2026-08-15T06:00:00Z",
        short_summary=very_long_summary,
        full_report=full_markdown_report,
        provider_used="gemini",
        model_used="gemini-2.0-flash",
    )
    mock_coordinator.latest_report = sample_report

    # Short sensor MUST be strictly truncated to <= 250 characters
    short_val = short_sensor.native_value
    assert short_val is not None
    assert len(short_val) == 250
    assert short_val.endswith("...")
    assert short_sensor.extra_state_attributes["provider_used"] == "gemini"

    # Long sensor carries status in state and full markdown in extra attributes
    assert long_sensor.native_value == "Report generated (2026-08-15)"
    assert long_sensor.extra_state_attributes["full_report"] == full_markdown_report
    assert long_sensor.extra_state_attributes["model_used"] == "gemini-2.0-flash"


def test_garmin_ai_last_answer_sensor() -> None:
    """Test GarminAILastAnswerSensor initialization, truncation, and extra attributes."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_coordinator = MagicMock()

    # Case 1: No question asked yet
    mock_coordinator.latest_answer = None
    answer_sensor = GarminAILastAnswerSensor(mock_coordinator, mock_entry)

    assert answer_sensor.native_value == "No question asked yet"
    assert answer_sensor.extra_state_attributes == {}

    # Case 2: Extremely long answer (> 255 characters)
    very_long_answer = "Answer details: " + ("X" * 300)
    mock_coordinator.latest_answer = {
        "question": "Should I train hard today?",
        "answer": very_long_answer,
        "timestamp": "2026-08-15T22:00:00Z",
    }

    # State must be strictly truncated to <= 250 characters
    val = answer_sensor.native_value
    assert val is not None
    assert len(val) == 250
    assert val.endswith("...")
    assert answer_sensor.extra_state_attributes["full_answer"] == very_long_answer
    assert answer_sensor.extra_state_attributes["question"] == "Should I train hard today?"
    assert answer_sensor.extra_state_attributes["timestamp"] == "2026-08-15T22:00:00Z"


