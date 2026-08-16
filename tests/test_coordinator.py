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
    mock_storage.async_prune_history = AsyncMock()

    def _create_task(coro):
        coro.close()
        return MagicMock()

    hass.async_create_task = MagicMock(side_effect=_create_task)

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    metrics = await coordinator._async_update_data()

    assert metrics is sample_metrics
    mock_client.async_fetch_daily_metrics.assert_called()
    mock_storage.async_save_daily_metrics.assert_called_once_with(sample_metrics.to_dict())
    mock_storage.async_prune_history.assert_called_once()
    hass.async_create_task.assert_called_once()


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
    mock_provider.model = "gemini-2.0-flash"
    mock_provider.async_generate_response = AsyncMock(
        return_value="<summary>Great recovery today with 85 sleep score.</summary>\n\n## Daily Report\nLooking strong!"
    )

    with patch(
        "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
        return_value=mock_provider,
    ):
        report = await coordinator.async_generate_report()

        assert report is not None
        assert report.short_summary == "Great recovery today with 85 sleep score."
        assert "## Daily Report" in report.full_report
        assert coordinator.latest_report == report
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

    with patch.object(
        coordinator.hass.services, "async_call", new_callable=AsyncMock
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


@pytest.mark.asyncio
async def test_coordinator_rate_limit_fallback(hass: HomeAssistant) -> None:
    """Test coordinator catches Garmin rate limits (429) and retains existing cached metrics."""
    from custom_components.garmin_ha_ai.garmin_client import GarminRateLimitError

    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    cached_metrics = GarminDailyMetrics(date="2026-08-15", steps=8500)
    coordinator.data = cached_metrics

    mock_client.async_fetch_daily_metrics = AsyncMock(
        side_effect=GarminRateLimitError("Garmin rate limit 429")
    )

    metrics = await coordinator._async_update_data()
    assert metrics is cached_metrics
    assert coordinator.data.steps == 8500


@pytest.mark.asyncio
async def test_coordinator_question_and_report_view_state(hass: HomeAssistant) -> None:
    """Test setting question input and report display mode on coordinator."""
    from custom_components.garmin_ha_ai.const import REPORT_VIEW_LONG, REPORT_VIEW_SHORT

    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    coordinator.async_update_listeners = MagicMock()

    # Question input
    coordinator.set_question_input("What workouts should I do?")
    assert coordinator.question_input == "What workouts should I do?"
    coordinator.async_update_listeners.assert_called_once()

    await coordinator.async_set_question_input("Updated question?")
    assert coordinator.question_input == "Updated question?"

    # Report display mode
    coordinator.set_report_display_mode(REPORT_VIEW_LONG)
    assert coordinator.report_display_mode == REPORT_VIEW_LONG

    # Invalid mode is ignored
    coordinator.set_report_display_mode("InvalidMode")
    assert coordinator.report_display_mode == REPORT_VIEW_LONG

    await coordinator.async_set_report_display_mode(REPORT_VIEW_SHORT)
    assert coordinator.report_display_mode == REPORT_VIEW_SHORT


@pytest.mark.asyncio
async def test_coordinator_async_ask_question_success(hass: HomeAssistant) -> None:
    """Test coordinator async_ask_question invokes AI provider and stores latest answer."""
    from homeassistant.exceptions import HomeAssistantError

    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test-key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(
        return_value={"2026-08-15": {"steps": 10000}}
    )

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(return_value="Take a rest day.")

    with patch(
        "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
        return_value=mock_provider,
    ):
        answer = await coordinator.async_ask_question("Should I run?")

    assert answer == "Take a rest day."
    assert coordinator.latest_answer["question"] == "Should I run?"
    assert coordinator.latest_answer["answer"] == "Take a rest day."


@pytest.mark.asyncio
async def test_coordinator_async_ask_question_errors(hass: HomeAssistant) -> None:
    """Test coordinator async_ask_question validation errors."""
    from homeassistant.exceptions import HomeAssistantError

    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test-key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_storage = MagicMock()

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    # Empty question
    with pytest.raises(HomeAssistantError, match="Question cannot be empty"):
        await coordinator.async_ask_question("")

    # Missing API key
    mock_entry.data[CONF_AI_API_KEY] = ""
    with pytest.raises(HomeAssistantError, match="AI API key is not configured"):
        await coordinator.async_ask_question("Any tips?")


