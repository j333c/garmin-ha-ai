"""Tests for Garmin HA AI DataUpdateCoordinator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.garmin_ha_ai.const import CONF_AI_API_KEY, CONF_AI_PROVIDER
from custom_components.garmin_ha_ai.coordinator import GarminDataUpdateCoordinator
from custom_components.garmin_ha_ai.models import AIHealthReport, GarminDailyMetrics
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed


def test_coordinator_update_success() -> None:
    """Test coordinator successfully fetches metrics and saves to storage."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_client = MagicMock()
        mock_storage = MagicMock()

        sample_metrics = GarminDailyMetrics(date="2026-08-15", steps=10000)
        mock_client.async_fetch_daily_metrics = AsyncMock(return_value=sample_metrics)
        mock_storage.async_save_daily_metrics = AsyncMock()

        coordinator = GarminDataUpdateCoordinator(
            mock_hass, mock_entry, mock_client, mock_storage
        )

        mock_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())

        metrics = await coordinator._async_update_data()

        assert metrics is sample_metrics
        mock_client.async_fetch_daily_metrics.assert_called_once()
        mock_storage.async_save_daily_metrics.assert_called_once_with(sample_metrics.to_dict())
        mock_hass.async_create_task.assert_called_once()

    asyncio.run(run())


def test_coordinator_connection_error() -> None:
    """Test coordinator handles network/connection errors by raising UpdateFailed."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_client = MagicMock()
        mock_storage = MagicMock()

        from garminconnect import GarminConnectConnectionError

        mock_client.async_fetch_daily_metrics = AsyncMock(
            side_effect=GarminConnectConnectionError("Server unreachable")
        )

        coordinator = GarminDataUpdateCoordinator(
            mock_hass, mock_entry, mock_client, mock_storage
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_coordinator_auth_failure() -> None:
    """Test coordinator propagates ConfigEntryAuthFailed on auth failure."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_client = MagicMock()
        mock_storage = MagicMock()

        mock_client.async_fetch_daily_metrics = AsyncMock(
            side_effect=ConfigEntryAuthFailed("Token expired")
        )

        coordinator = GarminDataUpdateCoordinator(
            mock_hass, mock_entry, mock_client, mock_storage
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    asyncio.run(run())


def test_coordinator_async_generate_report_success() -> None:
    """Test async_generate_report success flow."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test_key"}
        mock_entry.options = {}

        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load_history = AsyncMock(return_value=[])

        sample_metrics = GarminDailyMetrics(date="2026-08-15", steps=10000)

        coordinator = GarminDataUpdateCoordinator(
            mock_hass, mock_entry, mock_client, mock_storage
        )
        coordinator.data = sample_metrics
        coordinator.async_update_listeners = MagicMock()

        mock_report = AIHealthReport(
            timestamp="2026-08-15T06:00:00Z",
            short_summary="Great job today!",
            full_report="# Full Report",
            provider_used="gemini",
            model_used="gemini-2.0-flash",
        )

        mock_provider = MagicMock()
        mock_provider.async_generate_report = AsyncMock(return_value=mock_report)

        with patch(
            "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
            return_value=mock_provider,
        ):
            report = await coordinator.async_generate_report()

            assert report is mock_report
            assert coordinator.latest_report is mock_report
            coordinator.async_update_listeners.assert_called_once()
            assert coordinator._is_generating is False

    asyncio.run(run())


def test_coordinator_debouncing_lock() -> None:
    """Test async_generate_report debouncing lock rejects duplicate in-flight requests."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_client = MagicMock()
        mock_storage = MagicMock()

        coordinator = GarminDataUpdateCoordinator(
            mock_hass, mock_entry, mock_client, mock_storage
        )
        coordinator._is_generating = True

        report = await coordinator.async_generate_report()
        assert report is None
        assert coordinator._is_generating is True

    asyncio.run(run())


def test_coordinator_missing_api_key() -> None:
    """Test async_generate_report returns None when API key is missing."""

    async def run() -> None:
        mock_hass = MagicMock()
        mock_entry = MagicMock()
        mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: ""}
        mock_entry.options = {}

        mock_client = MagicMock()
        mock_storage = MagicMock()
        mock_storage.async_load_history = AsyncMock(return_value=[])

        coordinator = GarminDataUpdateCoordinator(
            mock_hass, mock_entry, mock_client, mock_storage
        )
        coordinator.data = GarminDailyMetrics(date="2026-08-15", steps=10000)

        report = await coordinator.async_generate_report()
        assert report is None
        assert coordinator._is_generating is False

    asyncio.run(run())

