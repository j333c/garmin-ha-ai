"""Tests for Garmin HA AI options flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant

from custom_components.garmin_ha_ai.config_flow import GarminHaAiConfigFlow
from custom_components.garmin_ha_ai.const import (
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_NOTIFICATION_TARGETS,
    CONF_POLLING_SCHEDULE,
    CONF_RETENTION_DAYS,
    DEFAULT_POLLING_TIME,
    DEFAULT_RETENTION_DAYS,
    DOMAIN,
)
from custom_components.garmin_ha_ai.options_flow import GarminHaAiOptionsFlowHandler
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_options_flow_init_form(hass: HomeAssistant) -> None:
    """Test options flow displays initial form pre-populated with defaults."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "gemini", "ai_api_key": "key"},
        options={},
    )
    entry.add_to_hass(hass)

    flow = GarminHaAiOptionsFlowHandler(entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_save_valid(hass: HomeAssistant) -> None:
    """Test options flow saves valid options and prunes history."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "gemini", "ai_api_key": "key"},
        options={},
    )
    entry.add_to_hass(hass)

    flow = GarminHaAiOptionsFlowHandler(entry)
    flow.hass = hass

    user_input = {
        CONF_RETENTION_DAYS: 14,
        CONF_FITNESS_GOALS: "Run 5k in under 25 mins",
        CONF_COACHING_DIRECTIVES: "Encouraging tone",
        CONF_NOTIFICATION_TARGETS: "persistent_notification",
        CONF_POLLING_SCHEDULE: "07:00:00",
    }

    with patch(
        "custom_components.garmin_ha_ai.options_flow.GarminStorage.async_prune_history",
        new_callable=AsyncMock,
    ) as mock_prune:
        result = await flow.async_step_init(user_input=user_input)

        assert result["type"] == "create_entry"
        assert result["data"][CONF_RETENTION_DAYS] == 14
        assert result["data"][CONF_FITNESS_GOALS] == "Run 5k in under 25 mins"
        assert result["data"][CONF_COACHING_DIRECTIVES] == "Encouraging tone"
        assert result["data"][CONF_NOTIFICATION_TARGETS] == "persistent_notification"
        assert result["data"][CONF_POLLING_SCHEDULE] == "07:00:00"
        mock_prune.assert_called_once_with(14)


@pytest.mark.asyncio
async def test_options_flow_out_of_bounds_retention(hass: HomeAssistant) -> None:
    """Test options flow rejects retention_days out of bounds (< 7 or > 90)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "gemini", "ai_api_key": "key"},
    )
    entry.add_to_hass(hass)

    flow = GarminHaAiOptionsFlowHandler(entry)
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)
    schema = result["data_schema"]

    with pytest.raises(vol.Invalid):
        schema({CONF_RETENTION_DAYS: 5})

    with pytest.raises(vol.Invalid):
        schema({CONF_RETENTION_DAYS: 100})

    valid_payload = schema({CONF_RETENTION_DAYS: 30})
    assert valid_payload[CONF_RETENTION_DAYS] == 30


@pytest.mark.asyncio
async def test_config_flow_get_options_flow(hass: HomeAssistant) -> None:
    """Test async_get_options_flow returns OptionsFlowHandler instance."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "gemini", "ai_api_key": "key"},
    )
    entry.add_to_hass(hass)

    options_flow = GarminHaAiConfigFlow.async_get_options_flow(entry)
    options_flow.hass = hass
    assert isinstance(options_flow, GarminHaAiOptionsFlowHandler)
    assert options_flow.config_entry == entry


@pytest.mark.asyncio
async def test_options_update_listener(hass: HomeAssistant) -> None:
    """Test options update reloads entry and prunes storage history."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "gemini", "ai_api_key": "key"},
        options={CONF_RETENTION_DAYS: 21},
    )
    entry.add_to_hass(hass)

    from custom_components.garmin_ha_ai import async_reload_entry

    with patch(
        "custom_components.garmin_ha_ai.storage.GarminStorage.async_prune_history",
        new_callable=AsyncMock,
    ) as mock_prune, patch.object(
        hass.config_entries, "async_reload", new_callable=AsyncMock
    ) as mock_reload:
        await async_reload_entry(hass, entry)
        mock_prune.assert_called_once_with(21)
        mock_reload.assert_called_once_with(entry.entry_id)


@pytest.mark.asyncio
async def test_options_flow_model_discovery_and_time_selector(hass: HomeAssistant) -> None:
    """Test options flow fetches available models and uses TimeSelector."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "gemini", "ai_api_key": "valid_gemini_key"},
        options={},
    )
    entry.add_to_hass(hass)

    flow = GarminHaAiOptionsFlowHandler(entry)
    flow.hass = hass

    with patch(
        "custom_components.garmin_ha_ai.options_flow.async_list_gemini_models",
        new_callable=AsyncMock,
        return_value=["gemini-2.5-flash", "gemini-2.5-pro"],
    ) as mock_list:
        result = await flow.async_step_init(user_input=None)
        assert result["type"] == "form"
        mock_list.assert_called_once_with("valid_gemini_key", hass=hass)


@pytest.mark.asyncio
async def test_options_flow_openai_model_discovery(hass: HomeAssistant) -> None:
    """Test options flow dynamically fetches models when AI provider is openai."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garmin Test",
        data={"username": "testuser", "ai_provider": "openai", "ai_api_key": "openai_api_key"},
        options={"ai_base_url": "http://localhost:11434/v1"},
    )
    entry.add_to_hass(hass)

    flow = GarminHaAiOptionsFlowHandler(entry)
    flow.hass = hass

    with patch(
        "custom_components.garmin_ha_ai.options_flow.async_list_openai_models",
        new_callable=AsyncMock,
        return_value=["llama3.3:70b", "mistral:latest"],
    ) as mock_list:
        result = await flow.async_step_init(user_input=None)
        assert result["type"] == "form"
        mock_list.assert_called_once_with(
            "openai_api_key", base_url="http://localhost:11434/v1", hass=hass
        )


