"""Tests for Garmin HA AI DataUpdateCoordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ServiceNotFound
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.garmin_ha_ai.const import (
    CONF_AI_API_KEY,
    CONF_AI_PROVIDER,
    CONF_NOTIFICATION_TARGETS,
)
from custom_components.garmin_ha_ai.coordinator import GarminDataUpdateCoordinator
from custom_components.garmin_ha_ai.models import AIHealthReport, GarminDailyMetrics


@pytest.mark.asyncio
async def test_coordinator_update_success(hass: HomeAssistant) -> None:
    """Test coordinator successfully fetches metrics and saves to storage."""
    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    sample_metrics = GarminDailyMetrics(date="2026-08-15", steps=10000)
    mock_client.async_fetch_daily_metrics = AsyncMock(return_value=sample_metrics)
    mock_storage.async_save_daily_metrics = AsyncMock()

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    metrics = await coordinator._async_update_data()

    assert metrics is sample_metrics
    mock_client.async_fetch_daily_metrics.assert_called()
    mock_storage.async_save_daily_metrics.assert_called_once_with(sample_metrics.to_dict())


@pytest.mark.asyncio
async def test_coordinator_connection_error(hass: HomeAssistant) -> None:
    """Test coordinator handles network/connection errors by raising UpdateFailed."""
    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    from garminconnect import GarminConnectConnectionError

    mock_client.async_fetch_daily_metrics = AsyncMock(
        side_effect=GarminConnectConnectionError("Server unreachable")
    )

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_auth_failure(hass: HomeAssistant) -> None:
    """Test coordinator propagates ConfigEntryAuthFailed on auth failure."""
    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    mock_client.async_fetch_daily_metrics = AsyncMock(
        side_effect=ConfigEntryAuthFailed("Token expired")
    )

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_async_generate_report_success(hass: HomeAssistant) -> None:
    """Test async_generate_report success flow."""
    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test_key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    sample_metrics = GarminDailyMetrics(date="2026-08-15", steps=10000)

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
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


@pytest.mark.asyncio
async def test_coordinator_debouncing_lock(hass: HomeAssistant) -> None:
    """Test async_generate_report debouncing lock rejects duplicate in-flight requests."""
    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )
    coordinator._is_generating = True

    report = await coordinator.async_generate_report()
    assert report is None
    assert coordinator._is_generating is True


@pytest.mark.asyncio
async def test_coordinator_missing_api_key(hass: HomeAssistant) -> None:
    """Test async_generate_report returns None when API key is missing."""
    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: ""}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )
    coordinator.data = GarminDailyMetrics(date="2026-08-15", steps=10000)

    report = await coordinator.async_generate_report()
    assert report is None
    assert coordinator._is_generating is False


@pytest.mark.asyncio
async def test_coordinator_dispatch_notification_targets(hass: HomeAssistant) -> None:
    """Test notification dispatch for persistent_notification, notify.<service>, empty target, and ServiceNotFound error."""
    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    sample_report = AIHealthReport(
        timestamp="2026-08-15T06:00:00Z",
        short_summary="Great activity level today!",
        full_report="# Full Daily AI Report\n\nDetailed breakdown.",
        provider_used="gemini",
        model_used="gemini-2.0-flash",
    )

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as mock_async_call:
        # 1. Empty target (disabled)
        mock_entry.data = {CONF_NOTIFICATION_TARGETS: ""}
        mock_entry.options = {}
        await coordinator.async_dispatch_notification(sample_report)
        mock_async_call.assert_not_called()

        # 2. persistent_notification
        mock_entry.options = {CONF_NOTIFICATION_TARGETS: "persistent_notification"}
        await coordinator.async_dispatch_notification(sample_report)
        mock_async_call.assert_called_once_with(
            "persistent_notification",
            "create",
            {
                "title": "Garmin AI Daily Report",
                "message": "# Full Daily AI Report\n\nDetailed breakdown.",
                "notification_id": "garmin_ai_daily_report",
            },
        )

        # 3. notify.mobile_app_phone
        mock_async_call.reset_mock()
        mock_entry.options = {CONF_NOTIFICATION_TARGETS: "notify.mobile_app_phone"}
        await coordinator.async_dispatch_notification(sample_report)
        mock_async_call.assert_called_once_with(
            "notify",
            "mobile_app_phone",
            {
                "title": "Garmin AI Daily Report",
                "message": "Great activity level today!",
                "data": {"long_message": "# Full Daily AI Report\n\nDetailed breakdown."},
            },
        )

        # 4. Fault tolerance on ServiceNotFound
        mock_async_call.side_effect = ServiceNotFound("notify", "invalid_target")
        await coordinator.async_dispatch_notification(sample_report)
        # Should complete gracefully without throwing
