"""Tests for Garmin HA AI config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.garmin_ha_ai.config_flow import GarminHaAiConfigFlow
from custom_components.garmin_ha_ai.const import (
    CONF_AI_API_KEY,
    CONF_AI_PROVIDER,
    CONF_GARMIN_PASSWORD,
    CONF_GARMIN_USERNAME,
    CONF_MFA_CODE,
    PROVIDER_GEMINI,
)


@pytest.mark.asyncio
async def test_user_step_form_init(hass: HomeAssistant) -> None:
    """Test user step shows initial setup form."""
    flow = GarminHaAiConfigFlow()
    flow.hass = hass
    result = await flow.async_step_user(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_user_step_success(hass: HomeAssistant) -> None:
    """Test user step successfully creates entry without MFA."""
    flow = GarminHaAiConfigFlow()
    flow.hass = hass
    flow.context = {}
    user_input = {
        CONF_GARMIN_USERNAME: "testuser@example.com",
        CONF_GARMIN_PASSWORD: "securepassword",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "gemini_api_key_12345",
    }

    with patch(
        "custom_components.garmin_ha_ai.config_flow.GarminClient.async_login_with_credentials",
        new_callable=AsyncMock,
    ) as mock_login:
        mock_login.return_value = {"tokenstore": "xyz"}
        result = await flow.async_step_user(user_input=user_input)

        assert result["type"] == "create_entry"
        assert result["title"] == "Garmin (testuser@example.com)"
        assert result["data"][CONF_GARMIN_USERNAME] == "testuser@example.com"
        assert CONF_GARMIN_PASSWORD not in result["data"]


@pytest.mark.asyncio
async def test_user_step_mfa_required(hass: HomeAssistant) -> None:
    """Test user step redirects to MFA step when MFA is required."""
    flow = GarminHaAiConfigFlow()
    flow.hass = hass
    flow.context = {}
    user_input = {
        CONF_GARMIN_USERNAME: "mfauser@example.com",
        CONF_GARMIN_PASSWORD: "securepassword",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "gemini_api_key_12345",
    }

    from garminconnect import GarminConnectMfaRequired

    with patch(
        "custom_components.garmin_ha_ai.config_flow.GarminClient.async_login_with_credentials",
        new_callable=AsyncMock,
    ) as mock_login:
        mock_login.side_effect = GarminConnectMfaRequired()
        result = await flow.async_step_user(user_input=user_input)

        assert result["type"] == "form"
        assert result["step_id"] == "mfa"


@pytest.mark.asyncio
async def test_mfa_step_success(hass: HomeAssistant) -> None:
    """Test MFA step successfully verifies passcode and creates entry."""
    flow = GarminHaAiConfigFlow()
    flow.hass = hass
    flow.context = {}
    flow._user_data = {
        CONF_GARMIN_USERNAME: "mfauser@example.com",
        CONF_GARMIN_PASSWORD: "securepassword",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "gemini_api_key_12345",
    }

    with patch(
        "custom_components.garmin_ha_ai.config_flow.GarminClient.async_login_with_credentials",
        new_callable=AsyncMock,
    ) as mock_login:
        mock_login.return_value = {"tokenstore": "mfa_token"}

        result = await flow.async_step_mfa(user_input={CONF_MFA_CODE: "654321"})

        assert result["type"] == "create_entry"
        assert result["title"] == "Garmin (mfauser@example.com)"
        mock_login.assert_called_once_with(
            "mfauser@example.com", "securepassword", mfa_code="654321"
        )


@pytest.mark.asyncio
async def test_user_step_invalid_auth(hass: HomeAssistant) -> None:
    """Test user step shows invalid_auth error on bad credentials."""
    flow = GarminHaAiConfigFlow()
    flow.hass = hass
    flow.context = {}
    user_input = {
        CONF_GARMIN_USERNAME: "testuser@example.com",
        CONF_GARMIN_PASSWORD: "wrongpassword",
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "key",
    }

    with patch(
        "custom_components.garmin_ha_ai.config_flow.GarminClient.async_login_with_credentials",
        new_callable=AsyncMock,
    ) as mock_login:
        mock_login.side_effect = ConfigEntryAuthFailed("Invalid credentials")

        result = await flow.async_step_user(user_input=user_input)
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}
