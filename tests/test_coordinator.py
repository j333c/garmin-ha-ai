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
    mock_storage.async_save_and_prune_history = AsyncMock()

    def _create_task(coro):
        coro.close()
        return MagicMock()

    hass.async_create_task = MagicMock(side_effect=_create_task)

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    metrics = await coordinator._async_update_data()

    assert metrics is sample_metrics
    assert mock_client.async_fetch_daily_metrics.call_count == 2
    assert mock_storage.async_save_and_prune_history.call_count == 2
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


@pytest.mark.asyncio
async def test_coordinator_error_tracking_on_ai_failure(hass: HomeAssistant) -> None:
    """Test coordinator tracks latest_error on AI failures and clears it on success."""
    from custom_components.garmin_ha_ai.ai_engine.base import AIEngineError
    from homeassistant.exceptions import HomeAssistantError

    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test-key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(
        side_effect=AIEngineError("Gemini model is currently experiencing high demand (503 Service Unavailable).")
    )

    with patch(
        "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
        return_value=mock_provider,
    ):
        # Q&A failure sets latest_error
        with pytest.raises(HomeAssistantError, match="high demand"):
            await coordinator.async_ask_question("Will I recover?")
        assert coordinator.latest_error is not None
        assert "high demand" in coordinator.latest_error
        assert coordinator.last_error_time is not None

        # Successful call clears latest_error
        mock_provider.async_generate_response = AsyncMock(return_value="Yes, you will recover well.")
        await coordinator.async_ask_question("Will I recover?")
        assert coordinator.latest_error is None


@pytest.mark.asyncio
async def test_coordinator_async_generate_report_error_handling(hass: HomeAssistant) -> None:
    """Test async_generate_report captures AIEngineError and Exception without crashing."""
    from custom_components.garmin_ha_ai.ai_engine.base import AIEngineError

    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test-key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_client.async_fetch_daily_metrics = AsyncMock(
        return_value=GarminDailyMetrics(date="2026-08-16", steps=8000)
    )
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    mock_provider = AsyncMock()
    # 1. AIEngineError
    mock_provider.async_generate_response = AsyncMock(
        side_effect=AIEngineError("Quota exceeded")
    )

    with patch(
        "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
        return_value=mock_provider,
    ):
        report = await coordinator.async_generate_report()
        assert report is None
        assert coordinator.latest_error == "Quota exceeded"
        assert coordinator.last_error_time is not None

        # 2. General unexpected Exception
        mock_provider.async_generate_response = AsyncMock(
            side_effect=RuntimeError("Unexpected connection reset")
        )
        report2 = await coordinator.async_generate_report()
        assert report2 is None
        assert "Unexpected connection reset" in coordinator.latest_error


@pytest.mark.asyncio
async def test_coordinator_async_ask_question_uses_stored_input_fallback(hass: HomeAssistant) -> None:
    """Test async_ask_question falls back to self.question_input when question is None or empty."""
    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test-key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )
    coordinator.set_question_input("How was my training today?")

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(
        return_value="Your training was well-paced and within recovery zones."
    )

    with patch(
        "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
        return_value=mock_provider,
    ):
        # Call without question argument -> should use stored question_input
        ans = await coordinator.async_ask_question()
        assert "well-paced" in ans
        assert coordinator.latest_answer["question"] == "How was my training today?"


@pytest.mark.asyncio
async def test_coordinator_async_generate_report_force_refetches_metrics(hass: HomeAssistant) -> None:
    """Test async_generate_report with force=True refetches fresh daily metrics from Garmin."""
    mock_entry = MagicMock()
    mock_entry.data = {CONF_AI_PROVIDER: "gemini", CONF_AI_API_KEY: "test-key"}
    mock_entry.options = {}

    mock_client = MagicMock()
    cached_metrics = GarminDailyMetrics(date="2026-08-16", steps=5000)
    fresh_metrics = GarminDailyMetrics(date="2026-08-16", steps=12000)
    mock_client.async_fetch_daily_metrics = AsyncMock(return_value=fresh_metrics)

    mock_storage = MagicMock()
    mock_storage.async_load_history = AsyncMock(return_value={})

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )
    # Set cached data
    coordinator.data = cached_metrics

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(
        return_value="<summary>Report</summary>\nFull report"
    )

    with patch(
        "custom_components.garmin_ha_ai.coordinator.get_ai_provider",
        return_value=mock_provider,
    ), patch(
        "custom_components.garmin_ha_ai.coordinator.assemble_report_prompt"
    ) as mock_prompt_assembler:
        mock_prompt_assembler.return_value = "prompt text"
        report = await coordinator.async_generate_report(force=True)

        assert report is not None
        mock_client.async_fetch_daily_metrics.assert_called_once()
        # Prompt assembler should receive the fresh metrics (12000 steps)
        assert mock_prompt_assembler.call_args[1]["current_metrics"] == fresh_metrics


@pytest.mark.asyncio
async def test_coordinator_multi_day_window_and_weight_carryover(hass: HomeAssistant) -> None:
    """Test coordinator passes cached weight as fallback and reconciles yesterday and today."""
    mock_entry = MagicMock()
    mock_client = MagicMock()
    mock_storage = MagicMock()

    # Cached history has a previous weight entry
    mock_storage.async_load_history = AsyncMock(
        return_value={"2026-10-07": {"weight_kg": 76.5}}
    )
    mock_storage.async_save_and_prune_history = AsyncMock()

    yesterday_metrics = GarminDailyMetrics(date="2026-10-08", steps=9000, weight_kg=None)
    today_metrics = GarminDailyMetrics(date="2026-10-09", steps=1500, weight_kg=76.5)

    mock_client.async_fetch_daily_metrics = AsyncMock(
        side_effect=[yesterday_metrics, today_metrics]
    )

    def _create_task(coro):
        coro.close()
        return MagicMock()

    hass.async_create_task = MagicMock(side_effect=_create_task)

    coordinator = GarminDataUpdateCoordinator(
        hass, mock_entry, mock_client, mock_storage
    )

    result = await coordinator._async_update_data()

    assert result is today_metrics
    # Client should be called twice: once for yesterday and once for today
    assert mock_client.async_fetch_daily_metrics.call_count == 2
    # Verify fallback_weight was passed
    calls = mock_client.async_fetch_daily_metrics.call_args_list
    assert calls[0].kwargs.get("fallback_weight") == 76.5
    assert calls[1].kwargs.get("fallback_weight") == 76.5
    # Storage should be updated twice (yesterday + today)
    assert mock_storage.async_save_and_prune_history.call_count == 2





