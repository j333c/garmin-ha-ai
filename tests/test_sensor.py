"""Tests for Garmin HA AI metric sensor platform."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.garmin_ha_ai.const import (
    REPORT_VIEW_LONG,
    REPORT_VIEW_QA,
    REPORT_VIEW_SHORT,
)
from custom_components.garmin_ha_ai.models import AIHealthReport, GarminDailyMetrics
from custom_components.garmin_ha_ai.sensor import (
    SENSOR_DESCRIPTIONS,
    GarminAIHealthReportLongSensor,
    GarminAIHealthReportShortSensor,
    GarminAILastAnswerSensor,
    GarminAISelectedReportSensor,
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

        # 6 metric sensors + 2 report sensors + 1 last answer sensor + 1 last update sensor + 1 selected report sensor = 11 total
        assert len(added_entities) == len(SENSOR_DESCRIPTIONS) + 5
        assert len(added_entities) == 11

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

    # Case 3: Error state tracking
    mock_coordinator.latest_error = "Gemini model is currently experiencing high demand (503 Service Unavailable)."
    mock_coordinator.last_error_time = "2026-08-16T13:30:00Z"
    assert "last_error" in long_sensor.extra_state_attributes
    assert "503" in long_sensor.extra_state_attributes["last_error"]
    assert long_sensor.extra_state_attributes["last_error_time"] == "2026-08-16T13:30:00Z"


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

    # Case 3: Error state tracking
    mock_coordinator.latest_error = "AI Engine error: quota exceeded"
    mock_coordinator.last_error_time = "2026-08-16T14:00:00Z"
    assert "last_error" in answer_sensor.extra_state_attributes
    assert answer_sensor.extra_state_attributes["last_error"] == "AI Engine error: quota exceeded"
    assert answer_sensor.extra_state_attributes["last_error_time"] == "2026-08-16T14:00:00Z"



def test_garmin_ai_last_update_sensor() -> None:
    """Test GarminAILastUpdateSensor returns datetime object with tzinfo."""
    from datetime import datetime, timezone
    from custom_components.garmin_ha_ai.sensor import GarminAILastUpdateSensor

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_coordinator = MagicMock()

    # Case 1: No update yet
    mock_coordinator.last_update_time = None
    sensor = GarminAILastUpdateSensor(mock_coordinator, mock_entry)
    assert sensor.native_value is None

    # Case 2: Datetime object
    now_dt = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    mock_coordinator.last_update_time = now_dt
    assert sensor.native_value == now_dt
    assert sensor.native_value.tzinfo is not None

    # Case 3: ISO string fallback parsing
    mock_coordinator.last_update_time = "2026-08-16T12:00:00+00:00"
    parsed_dt = sensor.native_value
    assert isinstance(parsed_dt, datetime)
    assert parsed_dt.year == 2026


def test_garmin_ai_selected_report_sensor() -> None:
    """Test GarminAISelectedReportSensor dynamically returns content matching the selected mode."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    mock_coordinator = MagicMock()

    sample_report = AIHealthReport(
        timestamp="2026-08-16T08:00:00Z",
        short_summary="Short summary: Recovery is strong today.",
        full_report="# Full Report\n\n- Sleep: Great\n- Stress: Low",
        provider_used="gemini",
        model_used="gemini-2.0-flash",
    )
    mock_coordinator.latest_report = sample_report
    mock_coordinator.latest_answer = {
        "question": "Can I do intervals today?",
        "answer": "Yes, your readiness is optimal.",
        "timestamp": "2026-08-16T08:30:00Z",
    }

    sensor = GarminAISelectedReportSensor(mock_coordinator, mock_entry)

    # 1. Mode: Short Summary
    mock_coordinator.report_display_mode = REPORT_VIEW_SHORT
    assert sensor.native_value == REPORT_VIEW_SHORT
    assert sensor.extra_state_attributes["report_text"] == "Short summary: Recovery is strong today."
    assert sensor.extra_state_attributes["display_mode"] == REPORT_VIEW_SHORT
    assert sensor.extra_state_attributes["timestamp"] == "2026-08-16T08:00:00Z"

    # 2. Mode: Long Report
    mock_coordinator.report_display_mode = REPORT_VIEW_LONG
    assert sensor.native_value == REPORT_VIEW_LONG
    assert sensor.extra_state_attributes["report_text"] == "# Full Report\n\n- Sleep: Great\n- Stress: Low"
    assert sensor.extra_state_attributes["display_mode"] == REPORT_VIEW_LONG

    # 3. Mode: Latest Q&A Answer
    mock_coordinator.report_display_mode = REPORT_VIEW_QA
    assert sensor.native_value == REPORT_VIEW_QA
    assert "Can I do intervals today?" in sensor.extra_state_attributes["report_text"]
    assert "Yes, your readiness is optimal." in sensor.extra_state_attributes["report_text"]
    assert sensor.extra_state_attributes["timestamp"] == "2026-08-16T08:30:00Z"

    # 4. Fallback when report or answer is empty
    mock_coordinator.latest_report = None
    mock_coordinator.latest_answer = None

    mock_coordinator.report_display_mode = REPORT_VIEW_SHORT
    assert sensor.extra_state_attributes["report_text"] == "No report generated yet."

    mock_coordinator.report_display_mode = REPORT_VIEW_LONG
    assert sensor.extra_state_attributes["report_text"] == "No report generated yet."

    mock_coordinator.report_display_mode = REPORT_VIEW_QA
    assert sensor.extra_state_attributes["report_text"] == "No question asked yet."




