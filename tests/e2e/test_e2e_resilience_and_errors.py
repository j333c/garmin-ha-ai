"""End-to-End Resilience, Reauth, and Error Handling Tests."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from custom_components.garmin_ha_ai import async_setup, async_setup_entry
from custom_components.garmin_ha_ai.const import (
    CONF_AI_API_KEY,
    CONF_AI_MODEL,
    CONF_AI_PROVIDER,
    CONF_GARMIN_PASSWORD,
    CONF_GARMIN_USERNAME,
    CONF_MFA_CODE,
    CONF_NOTIFICATION_TARGETS,
    DEFAULT_AI_MODEL_GEMINI,
    DOMAIN,
    PROVIDER_GEMINI,
)
from custom_components.garmin_ha_ai.coordinator import GarminDataUpdateCoordinator
from custom_components.garmin_ha_ai.models import AIHealthReport, GarminDailyMetrics


@pytest.mark.asyncio
async def test_e2e_reauth_lifecycle_on_session_expiration(hass: HomeAssistant) -> None:
    """Validate E2E reauth workflow when Garmin token expires during regular operation."""
    await async_setup(hass, {})

    entry = MagicMock()
    entry.entry_id = "reauth_entry_id"
    entry.data = {
        CONF_GARMIN_USERNAME: "runner@garmin.com",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "test-api-key",
        CONF_AI_MODEL: DEFAULT_AI_MODEL_GEMINI,
    }
    entry.options = {}
    entry.add_update_listener = MagicMock()
    entry.async_on_unload = MagicMock()

    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.flow = MagicMock()
    hass.config_entries.flow.async_init = AsyncMock(return_value={"type": "form", "step_id": "reauth_confirm"})

    from garminconnect import GarminConnectAuthenticationError

    # 1. Setup succeeds initially
    mock_metrics = GarminDailyMetrics(date="2026-08-16", steps=8000)
    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_fetch_daily_metrics",
        new_callable=AsyncMock,
        return_value=mock_metrics,
    ), patch("custom_components.garmin_ha_ai.storage.GarminStorage.async_save_daily_metrics", new_callable=AsyncMock):
        assert await async_setup_entry(hass, entry) is True

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # 2. Next scheduled polling attempt raises GarminConnectAuthenticationError
    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_fetch_daily_metrics",
        side_effect=GarminConnectAuthenticationError("Session expired"),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    # 3. User triggers Reauth flow in UI with new password and MFA
    from custom_components.garmin_ha_ai.config_flow import GarminHaAiConfigFlow

    reauth_flow = GarminHaAiConfigFlow()
    reauth_flow.hass = hass
    reauth_flow.context = {
        "source": "reauth",
        "entry_id": entry.entry_id,
        "unique_id": "runner@garmin.com",
    }

    reauth_flow._reauth_entry = entry

    from garminconnect import GarminConnectMfaRequired

    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_login_with_credentials",
        side_effect=GarminConnectMfaRequired("MFA challenge"),
    ):
        reauth_step1 = await reauth_flow.async_step_reauth_confirm(
            {CONF_GARMIN_PASSWORD: "new-super-secret-password"}
        )
        assert reauth_step1["type"] == "form"
        assert reauth_step1["step_id"] == "mfa"

    with patch(
        "custom_components.garmin_ha_ai.garmin_client.GarminClient.async_login_with_credentials",
        new_callable=AsyncMock,
        return_value={"tokenstore": "renewed-token-xyz"},
    ):
        reauth_step2 = await reauth_flow.async_step_mfa({CONF_MFA_CODE: "778899"})
        assert reauth_step2["type"] == "abort"
        assert reauth_step2["reason"] == "reauth_successful"


@pytest.mark.asyncio
async def test_e2e_garmin_network_outage_resilience(hass: HomeAssistant) -> None:
    """Validate coordinator raises UpdateFailed on network failure without losing cached data."""
    from homeassistant.helpers.update_coordinator import UpdateFailed
    from garminconnect import GarminConnectConnectionError

    entry = MagicMock()
    entry.entry_id = "network_test_entry"
    entry.data = {
        CONF_GARMIN_USERNAME: "user@example.com",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "test-key",
    }
    entry.options = {}

    storage = MagicMock()
    storage.async_save_daily_metrics = AsyncMock()
    client = MagicMock()
    client.async_fetch_daily_metrics = AsyncMock(
        side_effect=GarminConnectConnectionError("Garmin servers unreachable")
    )

    coordinator = GarminDataUpdateCoordinator(hass, entry, client, storage)

    # Initial data is None
    with pytest.raises(UpdateFailed) as exc:
        await coordinator._async_update_data()

    assert "Error fetching Garmin data" in str(exc.value)


@pytest.mark.asyncio
async def test_e2e_ai_provider_quota_exhaustion_resilience(hass: HomeAssistant) -> None:
    """Validate report generation handles 429 quota exhaustion gracefully."""
    from google.genai.errors import APIError

    entry = MagicMock()
    entry.entry_id = "ai_error_entry"
    entry.data = {
        CONF_GARMIN_USERNAME: "user@example.com",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "test-key",
        CONF_AI_MODEL: DEFAULT_AI_MODEL_GEMINI,
    }
    entry.options = {}

    storage = MagicMock()
    storage.async_load_history = AsyncMock(return_value=[])
    client = MagicMock()

    coordinator = GarminDataUpdateCoordinator(hass, entry, client, storage)
    coordinator.data = GarminDailyMetrics(date="2026-08-16", steps=9500)

    with patch(
        "custom_components.garmin_ha_ai.ai_engine.gemini.GeminiProvider.async_generate_response",
        side_effect=APIError(code=429, message="Resource exhausted"),
    ):
        # Must catch and log error, not raise unhandled exception
        await coordinator.async_generate_report()
        assert coordinator.latest_report is None


@pytest.mark.asyncio
async def test_e2e_notification_missing_service_tolerance(hass: HomeAssistant) -> None:
    """Validate multi-target notification dispatch falls back safely if target service fails."""
    from homeassistant.exceptions import ServiceNotFound

    entry = MagicMock()
    entry.entry_id = "notify_test_entry"
    entry.data = {}
    entry.options = {
        CONF_NOTIFICATION_TARGETS: "notify.invalid_device,persistent_notification"
    }

    storage = MagicMock()
    client = MagicMock()
    coordinator = GarminDataUpdateCoordinator(hass, entry, client, storage)

    dispatched = []

    def mock_invalid(call):
        from homeassistant.exceptions import ServiceNotFound
        raise ServiceNotFound("notify", "invalid_device")

    def mock_persistent(call):
        dispatched.append("persistent_notification")

    hass.services.async_register("notify", "invalid_device", mock_invalid)
    hass.services.async_register("persistent_notification", "create", mock_persistent)

    sample_report = AIHealthReport(
        timestamp="2026-08-16T06:00:00Z",
        short_summary="Great recovery!",
        full_report="# Full Report",
        provider_used="gemini",
        model_used="gemini-2.0-flash",
    )

    # Should not raise exception even when invalid_device raises ServiceNotFound
    await coordinator.async_dispatch_notification(sample_report)

    assert "persistent_notification" in dispatched
