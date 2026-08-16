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

from custom_components.garmin_ha_ai.garmin_client import GarminClient, GarminMfaRequired
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


