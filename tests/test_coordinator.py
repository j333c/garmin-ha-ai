"""Tests for Garmin HA AI DataUpdateCoordinator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.garmin_ha_ai.coordinator import GarminDataUpdateCoordinator
from custom_components.garmin_ha_ai.models import GarminDailyMetrics
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

        metrics = await coordinator._async_update_data()

        assert metrics is sample_metrics
        mock_client.async_fetch_daily_metrics.assert_called_once()
        mock_storage.async_save_daily_metrics.assert_called_once_with(sample_metrics.to_dict())

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
