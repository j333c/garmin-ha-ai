"""Tests for Garmin client authentication adapter."""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock homeassistant package if not present in test environment
if "homeassistant" not in sys.modules:
    ha_mock = MagicMock()
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.core"] = ha_mock
    sys.modules["homeassistant.const"] = ha_mock
    sys.modules["homeassistant.config_entries"] = ha_mock
    sys.modules["homeassistant.helpers"] = ha_mock
    sys.modules["homeassistant.helpers.storage"] = ha_mock

    class MockConfigEntryAuthFailed(Exception):
        pass

    sys.modules["homeassistant.exceptions"] = MagicMock(
        ConfigEntryAuthFailed=MockConfigEntryAuthFailed
    )

# Mock garminconnect package if not present in test environment
if "garminconnect" not in sys.modules:
    gc_mock = MagicMock()

    class MockGarminConnectAuthenticationError(Exception):
        pass

    class MockGarminConnectConnectionError(Exception):
        pass

    gc_mock.GarminConnectAuthenticationError = MockGarminConnectAuthenticationError
    gc_mock.GarminConnectConnectionError = MockGarminConnectConnectionError
    sys.modules["garminconnect"] = gc_mock

import pytest
from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)

from custom_components.garmin_ha_ai.garmin_client import (
    GarminClient,
    GarminMfaRequired,
    _parse_body_battery,
    _parse_body_composition,
)
from homeassistant.exceptions import ConfigEntryAuthFailed


def test_login_with_tokens_success() -> None:
    """Test successful token resume."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "dG9rZW4="})
        mock_storage.async_save_tokens = AsyncMock()

        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.garth.dumps.return_value = "dG9rZW4="
            mock_garmin_cls.return_value = mock_garmin_inst

            success = await client_adapter.async_login_with_tokens()

            assert success is True
            assert client_adapter.client is mock_garmin_inst
            mock_garmin_inst.garth.loads.assert_called_once_with("dG9rZW4=")
            mock_garmin_inst.login.assert_called_once()
            mock_storage.async_save_tokens.assert_called_once_with({"tokenstore": "dG9rZW4="})

    asyncio.run(run())


def test_login_with_tokens_auth_failure() -> None:
    """Test token resume raising ConfigEntryAuthFailed on auth failure."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "invalid_token"})

        client_adapter = GarminClient(mock_hass, mock_storage)

        from garminconnect import GarminConnectAuthenticationError

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = GarminConnectAuthenticationError("Token expired")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(ConfigEntryAuthFailed):
                await client_adapter.async_login_with_tokens()

    asyncio.run(run())


def test_login_with_credentials_success() -> None:
    """Test successful credential login."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_save_tokens = AsyncMock()

        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.garth.dumps.return_value = "new_tokenstore"
            mock_garmin_cls.return_value = mock_garmin_inst

            tokens = await client_adapter.async_login_with_credentials(
                username="testuser@example.com", password="secret_password", mfa_code="123456"
            )

            assert tokens == {"tokenstore": "new_tokenstore"}
            mock_garmin_cls.assert_called_once_with(
                email="testuser@example.com", password="secret_password"
            )
            mock_garmin_inst.login.assert_called_once_with(mfa_code="123456")

    asyncio.run(run())


def test_login_with_credentials_auth_failure() -> None:
    """Test credential login failure raising ConfigEntryAuthFailed."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        from garminconnect import GarminConnectAuthenticationError

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = GarminConnectAuthenticationError("Invalid credentials")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(ConfigEntryAuthFailed):
                await client_adapter.async_login_with_credentials(
                    username="user@example.com", password="wrongpassword"
                )

    asyncio.run(run())


def test_async_get_client() -> None:
    """Test async_get_client returns client when authenticated."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "valid"})
        mock_storage.async_save_tokens = AsyncMock()

        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_cls.return_value = mock_garmin_inst

            client = await client_adapter.async_get_client()
            assert client is mock_garmin_inst

    asyncio.run(run())


def test_async_fetch_daily_metrics() -> None:
    """Test async_fetch_daily_metrics extracts and normalizes daily health stats."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)
        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        mock_garmin_inst = MagicMock()
        client_adapter.client = mock_garmin_inst

        mock_garmin_inst.get_user_summary.return_value = {
            "totalSteps": 10452,
            "totalDistanceMeters": 8230,
            "totalKilocalories": 2450,
            "restingHeartRate": 58,
            "averageStressLevel": 25,
            "bodyBatteryMinValue": 15,
            "bodyBatteryMaxValue": 95,
            "weight": 75500,
        }
        mock_garmin_inst.get_sleep_data.return_value = {
            "dailySleepDTO": {
                "sleepScores": {
                    "overall": {"value": 88}
                }
            }
        }
        mock_garmin_inst.get_hrv_data.return_value = {
            "hrvSummary": {"status": "BALANCED"}
        }
        mock_garmin_inst.get_activities_by_date.return_value = [
            {
                "activityId": 12345,
                "activityName": "Morning Run",
                "activityType": {"typeKey": "running"},
                "duration": 1800,
                "distance": 5000,
                "calories": 400,
            }
        ]

        metrics = await client_adapter.async_fetch_daily_metrics("2026-08-15")

        assert metrics.date == "2026-08-15"
        assert metrics.steps == 10452
        assert metrics.distance_km == 8.23
        assert metrics.total_calories == 2450
        assert metrics.resting_hr == 58
        assert metrics.avg_stress == 25
        assert metrics.sleep_score == 88
        assert metrics.hrv_status == "BALANCED"
        assert metrics.body_battery_min == 15
        assert metrics.body_battery_max == 95
        assert metrics.weight_kg == 75.5
        assert len(metrics.activities) == 1
        assert metrics.activities[0]["name"] == "Morning Run"

    asyncio.run(run())


def test_async_fetch_daily_metrics_partial_payload() -> None:
    """Test async_fetch_daily_metrics safely handles missing/null endpoint data."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)
        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        mock_garmin_inst = MagicMock()
        client_adapter.client = mock_garmin_inst

        # Empty payloads
        mock_garmin_inst.get_user_summary.return_value = {}
        mock_garmin_inst.get_sleep_data.return_value = {}
        mock_garmin_inst.get_hrv_data.return_value = {}
        mock_garmin_inst.get_activities_by_date.return_value = []

        metrics = await client_adapter.async_fetch_daily_metrics("2026-08-16")

        assert metrics.date == "2026-08-16"
        assert metrics.steps is None
        assert metrics.sleep_score is None
        assert metrics.hrv_status is None
        assert metrics.activities == []

    asyncio.run(run())


def test_async_fetch_daily_metrics_connection_error() -> None:
    """Test async_fetch_daily_metrics raises GarminConnectConnectionError on connection loss."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)
        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        mock_garmin_inst = MagicMock()
        client_adapter.client = mock_garmin_inst

        mock_garmin_inst.get_user_summary.side_effect = GarminConnectConnectionError("Unreachable")

        with pytest.raises(GarminConnectConnectionError):
            await client_adapter.async_fetch_daily_metrics("2026-08-16")

    asyncio.run(run())


def test_async_login_with_credentials_mfa_propagation() -> None:
    """Test async_login_with_credentials allows GarminMfaRequired to bubble up."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)
        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = GarminMfaRequired()
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(GarminMfaRequired):
                await client_adapter.async_login_with_credentials("user@example.com", "pass")

    asyncio.run(run())


def test_login_with_tokens_rate_limit() -> None:
    """Test token restore handles 429 rate limits with GarminRateLimitError instead of auth failure."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        mock_storage.async_load_tokens = AsyncMock(return_value={"tokenstore": "valid_token"})

        client_adapter = GarminClient(mock_hass, mock_storage)

        from custom_components.garmin_ha_ai.garmin_client import GarminRateLimitError
        from garminconnect import GarminConnectConnectionError

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = GarminConnectConnectionError("Mobile login returned 429 — IP rate limited by Garmin")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(GarminRateLimitError):
                await client_adapter.async_login_with_tokens()

    asyncio.run(run())


def test_parse_sleep_data() -> None:
    """Test _parse_sleep_data parses overall score correctly."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_sleep_data

    # Valid sleep score
    raw = {"dailySleepDTO": {"sleepScores": {"overall": {"value": 85}}}}
    assert _parse_sleep_data(raw) == 85

    # Missing or invalid payload
    assert _parse_sleep_data(None) is None
    assert _parse_sleep_data({}) is None
    assert _parse_sleep_data({"dailySleepDTO": {}}) is None


def test_parse_hrv_data() -> None:
    """Test _parse_hrv_data parses status correctly."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_hrv_data

    # Valid HRV status
    raw = {"hrvSummary": {"status": "BALANCED"}}
    assert _parse_hrv_data(raw) == "BALANCED"

    # Missing or invalid payload
    assert _parse_hrv_data(None) is None
    assert _parse_hrv_data({}) is None


def test_parse_activities() -> None:
    """Test _parse_activities extracts relevant activity fields."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_activities

    raw = [
        {
            "activityId": 12345,
            "activityName": "Morning Run",
            "activityType": {"typeKey": "running"},
            "duration": 1800,
            "calories": 350.0,
            "distance": 5000.0,
        },
        {
            "activityId": 12346,
            "activityName": "Gym Session",
            "activityType": {"typeKey": "strength_training"},
            "duration": 2700,
            "calories": 220.0,
        },
    ]

    parsed = _parse_activities(raw)
    assert len(parsed) == 2
    assert parsed[0]["activity_id"] == 12345
    assert parsed[0]["name"] == "Morning Run"
    assert parsed[0]["type"] == "running"
    assert parsed[0]["duration_sec"] == 1800
    assert parsed[0]["calories"] == 350.0
    assert parsed[0]["distance_m"] == 5000.0

    assert parsed[1]["type"] == "strength_training"
    assert parsed[1]["duration_sec"] == 2700
    assert parsed[1]["calories"] == 220.0

    # Empty payload
    assert _parse_activities(None) == []
    assert _parse_activities([]) == []


def test_parse_weight() -> None:
    """Test _parse_weight converts grams to kg and handles float/int."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_weight

    # Grams conversion (> 200)
    assert _parse_weight(72500) == 72.5
    # Kilograms direct (<= 200)
    assert _parse_weight(72.5) == 72.5
    # None or non-numeric
    assert _parse_weight(None) is None
    assert _parse_weight("invalid") is None


def test_parse_user_summary() -> None:
    """Test _parse_user_summary extracts metrics correctly."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_user_summary

    raw = {
        "totalSteps": 10500,
        "totalDistanceMeters": 7500,
        "totalKilocalories": 2300,
        "restingHeartRate": 54,
        "averageStressLevel": 28,
        "minHeartRate": 48,
        "maxHeartRate": 165,
        "bodyBatteryMinValue": 25,
        "bodyBatteryMaxValue": 95,
        "weight": 75000,
    }

    summary = _parse_user_summary(raw)
    assert summary["steps"] == 10500
    assert summary["distance_km"] == 7.5
    assert summary["total_calories"] == 2300
    assert summary["resting_hr"] == 54
    assert summary["avg_stress"] == 28
    assert summary["body_battery_min"] == 25
    assert summary["body_battery_max"] == 95
    assert summary["weight_kg"] == 75.0


def test_serialize_session_tokens() -> None:
    """Test _serialize_session_tokens correctly extracts garth/oauth tokens."""
    from custom_components.garmin_ha_ai.garmin_client import _serialize_session_tokens

    mock_client = MagicMock()
    mock_client.garth.dumps.return_value = "serialized_oauth_token"

    result = _serialize_session_tokens(mock_client)
    assert result == "serialized_oauth_token"


def test_async_login_with_credentials_mfa_tuple() -> None:
    """Test async_login_with_credentials handles ('needs_mfa', ...) tuple return."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)
        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.return_value = ("needs_mfa", "extra_info")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(GarminMfaRequired):
                await client_adapter.async_login_with_credentials("user@example.com", "pass")

    asyncio.run(run())


def test_async_login_with_credentials_mfa_string_exception() -> None:
    """Test async_login_with_credentials recognizes MFA in exception messages."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)
        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        with patch("custom_components.garmin_ha_ai.garmin_client.Garmin") as mock_garmin_cls:
            mock_garmin_inst = MagicMock()
            mock_garmin_inst.login.side_effect = Exception("2FA Verification code required")
            mock_garmin_cls.return_value = mock_garmin_inst

            with pytest.raises(GarminMfaRequired):
                await client_adapter.async_login_with_credentials("user@example.com", "pass")

    asyncio.run(run())


def test_parse_user_summary_edge_cases() -> None:
    """Test _parse_user_summary with string distances, empty payloads, and missing keys."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_user_summary

    # Empty payload or not dict
    assert _parse_user_summary({}) == {}
    assert _parse_user_summary(None) == {}
    assert _parse_user_summary({"unknown_key": 123}) == {}

    # String distance_m that can be converted
    valid_str_dist = {
        "totalSteps": 5000,
        "totalDistanceMeters": "4500",
        "restingHeartRate": 60,
    }
    summary = _parse_user_summary(valid_str_dist)
    assert summary["steps"] == 5000
    assert summary["distance_km"] == 4.5

    # Invalid non-convertible distance_m
    invalid_str_dist = {
        "totalSteps": 5000,
        "totalDistanceMeters": "invalid_dist",
        "restingHeartRate": 60,
    }
    summary2 = _parse_user_summary(invalid_str_dist)
    assert summary2["steps"] == 5000
    assert summary2["distance_km"] is None


def test_parse_activities_rich_metrics() -> None:
    """Test _parse_activities extracting heart rate zones, training effect, and HR stats."""
    from custom_components.garmin_ha_ai.garmin_client import _parse_activities

    raw = [
        {
            "activityId": 12345,
            "activityName": "Interval Track Workout",
            "activityType": {"typeKey": "running"},
            "duration": 2700,
            "distance": 8500,
            "calories": 620,
            "averageHR": 162.4,
            "maxHR": 184,
            "aerobicTrainingEffect": 4.1,
            "anaerobicTrainingEffect": 2.3,
            "hrTimeInZones": {"zone1": 120, "zone2": 300, "zone3": 900, "zone4": 1200, "zone5": 180},
        }
    ]

    acts = _parse_activities(raw)
    assert len(acts) == 1
    act = acts[0]
    assert act["activity_id"] == 12345
    assert act["name"] == "Interval Track Workout"
    assert act["type"] == "running"
    assert act["duration_sec"] == 2700
    assert act["duration_min"] == 45.0
    assert act["distance_m"] == 8500
    assert act["distance_km"] == 8.5
    assert act["calories"] == 620
    assert act["avg_hr"] == 162
    assert act["max_hr"] == 184
    assert act["aerobic_training_effect"] == 4.1
    assert act["anaerobic_training_effect"] == 2.3
    assert "zone4" in act["hr_zones"]


def test_parse_body_composition() -> None:
    """Test extracting weight from various body composition payloads."""
    # totalAverage dict with grams
    payload1 = {"totalAverage": {"weight": 74500}}
    assert _parse_body_composition(payload1) == 74.5

    # dateWeightList with grams
    payload2 = {"dateWeightList": [{"weight": 82000, "calendarDate": "2026-10-09"}]}
    assert _parse_body_composition(payload2) == 82.0

    # direct weight field in kg
    payload3 = {"weight": 71.2}
    assert _parse_body_composition(payload3) == 71.2

    # Empty or None
    assert _parse_body_composition(None) is None
    assert _parse_body_composition({}) is None


def test_parse_body_battery() -> None:
    """Test extracting min and max body battery from various payloads."""
    # bodyBatteryValuesArray array of [timestamp, value]
    payload1 = [
        {
            "date": "2026-10-09",
            "bodyBatteryValuesArray": [
                [1700000000, 85],
                [1700010000, 62],
                [1700020000, 95],
                [1700030000, 40],
            ],
        }
    ]
    b_min, b_max = _parse_body_battery(payload1)
    assert b_min == 40
    assert b_max == 95

    # explicit min and max fields
    payload2 = {"bodyBatteryMinValue": 25, "bodyBatteryMaxValue": 80}
    b_min2, b_max2 = _parse_body_battery(payload2)
    assert b_min2 == 25
    assert b_max2 == 80

    # Empty
    assert _parse_body_battery(None) == (None, None)
    assert _parse_body_battery([]) == (None, None)


def test_fetch_daily_metrics_sleep_and_body_battery_fallbacks() -> None:
    """Test sleep score and body battery fallback endpoints when primary summary is sparse."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        mock_gc = MagicMock()
        # Today user summary lacks body battery and sleep
        mock_gc.get_user_summary = MagicMock(return_value={
            "totalSteps": 8000,
            "totalDistanceMeters": 6000,
            "restingHeartRate": 52,
            # No weight, no bodyBatteryMinValue
        })
        # Today sleep data is empty (user woke up early)
        mock_gc.get_sleep_data = MagicMock(side_effect=lambda d: (
            {} if d == "2026-10-09" else {
                "dailySleepDTO": {"sleepScores": {"overall": {"value": 85}}}
            }
        ))
        # Dedicated body battery endpoint provides values
        mock_gc.get_body_battery = MagicMock(return_value=[{
            "bodyBatteryValuesArray": [[1, 30], [2, 92]]
        }])
        # Dedicated body composition endpoint provides weight
        mock_gc.get_body_composition = MagicMock(return_value={
            "totalAverage": {"weight": 75200}
        })
        mock_gc.get_hrv_data = MagicMock(return_value={"hrvSummary": {"status": "BALANCED"}})
        mock_gc.get_activities_by_date = MagicMock(return_value=[])

        client_adapter.client = mock_gc
        client_adapter.async_get_client = AsyncMock(return_value=mock_gc)

        metrics = await client_adapter.async_fetch_daily_metrics(
            target_date="2026-10-09", fallback_weight=74.0
        )

        assert metrics.steps == 8000
        # Sleep score recovered from previous day
        assert metrics.sleep_score == 85
        # Body battery recovered from get_body_battery endpoint
        assert metrics.body_battery_min == 30
        assert metrics.body_battery_max == 92
        # Weight recovered from get_body_composition endpoint (75200g -> 75.2kg)
        assert metrics.weight_kg == 75.2

    asyncio.run(run())


def test_fetch_daily_metrics_weight_historical_fallback() -> None:
    """Test weight falling back to historical weight when both summary and body composition are empty."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        mock_gc = MagicMock()
        mock_gc.get_user_summary = MagicMock(return_value={
            "totalSteps": 5000,
            "totalDistanceMeters": 4000,
            "restingHeartRate": 50,
        })
        mock_gc.get_sleep_data = MagicMock(return_value={})
        mock_gc.get_body_battery = MagicMock(return_value=[])
        mock_gc.get_body_composition = MagicMock(return_value={})
        mock_gc.get_hrv_data = MagicMock(return_value={})
        mock_gc.get_activities_by_date = MagicMock(return_value=[])

        client_adapter.client = mock_gc
        client_adapter.async_get_client = AsyncMock(return_value=mock_gc)

        metrics = await client_adapter.async_fetch_daily_metrics(
            target_date="2026-10-09", fallback_weight=73.5
        )

        # Weight uses fallback_weight
        assert metrics.weight_kg == 73.5

    asyncio.run(run())


def test_upload_workout_success() -> None:
    """Test async_upload_workout calls client upload_workout."""

    async def run() -> None:
        mock_hass = MagicMock()

        async def fake_executor(func, *args, **kwargs):
            return func(*args, **kwargs)

        mock_hass.async_add_executor_job = AsyncMock(side_effect=fake_executor)

        mock_storage = MagicMock()
        client_adapter = GarminClient(mock_hass, mock_storage)

        mock_gc = MagicMock()
        mock_gc.upload_workout = MagicMock(return_value={"workoutId": 998877})

        client_adapter.client = mock_gc
        client_adapter.async_get_client = AsyncMock(return_value=mock_gc)

        result = await client_adapter.async_upload_workout({"workoutName": "Test Workout"})
        assert result.get("workoutId") == 998877
        mock_gc.upload_workout.assert_called_once_with({"workoutName": "Test Workout"})

    asyncio.run(run())







