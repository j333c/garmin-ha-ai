"""Tests for the Garmin HA AI analytics engine."""
from __future__ import annotations

import pytest

from custom_components.garmin_ha_ai.analytics import (
    _classify_hrv_trend,
    calculate_baseline_analytics,
    format_baseline_analytics_block,
)
from custom_components.garmin_ha_ai.models import GarminDailyMetrics


def test_calculate_baseline_analytics_empty():
    """Test analytics calculation with empty history."""
    res = calculate_baseline_analytics(None, None)
    assert res["days_analyzed"] == 0
    assert res["mean_sleep_score"] is None
    assert res["mean_resting_hr"] is None
    assert res["mean_avg_stress"] is None
    assert res["mean_steps"] is None
    assert res["hrv_trend"] == "Unknown (No HRV data recorded)"

    formatted = format_baseline_analytics_block(res)
    assert "No sufficient 7-day history" in formatted


def test_calculate_baseline_analytics_with_data():
    """Test analytics calculation with a realistic 7-day history."""
    history = [
        GarminDailyMetrics(
            date=f"2026-08-{10+i:02d}",
            steps=8000 + i * 500,
            sleep_score=75 + i,
            resting_hr=55 - (i % 2),
            avg_stress=25 + (i % 5),
            total_calories=2200 + i * 50,
            hrv_status="BALANCED",
            activities=[
                {
                    "name": "Morning Run",
                    "type": "running",
                    "duration_min": 30,
                    "calories": 300,
                    "avg_hr": 145,
                    "max_hr": 165,
                    "aerobic_training_effect": 3.2,
                }
            ],
        )
        for i in range(7)
    ]

    current = GarminDailyMetrics(
        date="2026-08-17",
        steps=12000,
        sleep_score=85,
        resting_hr=52,
        avg_stress=20,
        total_calories=2500,
        hrv_status="BALANCED",
    )

    res = calculate_baseline_analytics(current, history, step_goal=10000, sleep_target=80)
    assert res["days_analyzed"] == 7
    assert res["mean_steps"] == 9500  # avg of 8000..11000
    assert res["step_delta_vs_avg"] == 2500  # 12000 - 9500
    assert res["step_delta_vs_goal"] == 2000  # 12000 - 10000
    assert res["mean_sleep_score"] == 78.0  # avg of 75..81
    assert res["sleep_delta_vs_avg"] == 7.0  # 85 - 78
    assert res["sleep_delta_vs_target"] == 5  # 85 - 80
    assert res["total_weekly_activities"] == 7
    assert res["total_weekly_duration_min"] == 210.0
    assert "Stable & Balanced" in res["hrv_trend"]

    formatted = format_baseline_analytics_block(res)
    assert "Past 7 days recorded" in formatted
    assert "Sleep Score Baseline: 7-day Avg = 78.0" in formatted
    assert "+2500 steps" in formatted
    assert "7-Day Training Volume: 7 activities (210.0 min" in formatted


def test_classify_hrv_trend_transitions():
    """Test HRV trend transitions classification."""
    # Recovering to balanced
    assert "Improving" in _classify_hrv_trend("BALANCED", ["UNBALANCED", "LOW", "UNBALANCED"])

    # Consistent balanced
    assert "Stable & Balanced" in _classify_hrv_trend("BALANCED", ["BALANCED", "BALANCED"])

    # Degrading to unbalanced
    assert "Declining" in _classify_hrv_trend("UNBALANCED", ["BALANCED", "BALANCED"])

    # Consistently unbalanced
    assert "Consistently Unbalanced" in _classify_hrv_trend("UNBALANCED", ["UNBALANCED", "UNBALANCED"])

    # Low status
    assert "Low" in _classify_hrv_trend("LOW", ["LOW"])
