"""Tests for Garmin HA AI custom services."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.garmin_ha_ai.const import (
    CONF_AI_API_KEY,
    CONF_AI_PROVIDER,
    DOMAIN,
    PROVIDER_GEMINI,
    SERVICE_ASK_QUESTION,
)
from custom_components.garmin_ha_ai.services import async_setup_services


@pytest.fixture
def mock_config_entry():
    """Mock config entry for setup."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_AI_PROVIDER: PROVIDER_GEMINI,
        CONF_AI_API_KEY: "test_key",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_storage():
    """Mock GarminStorage."""
    storage = MagicMock()
    storage.async_load_history = AsyncMock(
        return_value={
            "2026-08-10": {"date": "2026-08-10", "total_steps": 8000},
            "2026-08-11": {"date": "2026-08-11", "total_steps": 10000},
            "2026-08-12": {"date": "2026-08-12", "total_steps": 12000},
        }
    )
    return storage


@pytest.fixture
def mock_coordinator(mock_config_entry):
    """Mock GarminDataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.entry = mock_config_entry
    return coordinator


@pytest.mark.asyncio
async def test_ask_question_service_registration(hass: HomeAssistant):
    """Test that garmin_ha_ai.ask_question service is registered."""
    await async_setup_services(hass)
    assert hass.services.has_service(DOMAIN, SERVICE_ASK_QUESTION)


@pytest.mark.asyncio
async def test_ask_question_success(
    hass: HomeAssistant, mock_storage, mock_coordinator
):
    """Test successful execution of ask_question service returning direct response."""
    await async_setup_services(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": mock_storage,
        "coordinator": mock_coordinator,
    }

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(
        return_value="You should run 5km today at an easy pace."
    )

    with patch(
        "custom_components.garmin_ha_ai.services.get_ai_provider",
        return_value=mock_provider,
    ):
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            {"question": "Should I run today?", "days_history": 7},
            blocking=True,
            return_response=True,
        )

    assert response == {
        "question": "Should I run today?",
        "answer": "You should run 5km today at an easy pace.",
    }
    mock_provider.async_generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_ask_question_history_clamping(
    hass: HomeAssistant, mock_storage, mock_coordinator
):
    """Test history clamping when days_history exceeds available stored days."""
    await async_setup_services(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": mock_storage,
        "coordinator": mock_coordinator,
    }

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(
        return_value="Based on your 3 days of metrics..."
    )

    with patch(
        "custom_components.garmin_ha_ai.services.get_ai_provider",
        return_value=mock_provider,
    ), patch(
        "custom_components.garmin_ha_ai.services.assemble_qa_prompt",
        wraps=lambda **kwargs: "mocked prompt",
    ) as mock_prompt_func:
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            {"question": "How's my progression?", "days_history": 100},
            blocking=True,
            return_response=True,
        )

    assert response["answer"] == "Based on your 3 days of metrics..."
    # Verify only the 3 available historical entries were passed into assemble_qa_prompt
    history_passed = mock_prompt_func.call_args.kwargs["history"]
    assert len(history_passed) == 3


@pytest.mark.asyncio
async def test_ask_question_missing_api_key(
    hass: HomeAssistant, mock_storage, mock_coordinator, mock_config_entry
):
    """Test that ask_question raises HomeAssistantError when API key is missing."""
    await async_setup_services(hass)

    mock_config_entry.data[CONF_AI_API_KEY] = ""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": mock_storage,
        "coordinator": mock_coordinator,
    }

    with pytest.raises(HomeAssistantError, match="AI API key is not configured"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            {"question": "What's my status?"},
            blocking=True,
            return_response=True,
        )


@pytest.mark.asyncio
async def test_ask_question_empty_history_fallback(
    hass: HomeAssistant, mock_coordinator
):
    """Test ask_question behavior when no history is stored."""
    await async_setup_services(hass)

    empty_storage = MagicMock()
    empty_storage.async_load_history = AsyncMock(return_value={})

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": empty_storage,
        "coordinator": mock_coordinator,
    }

    mock_provider = AsyncMock()
    mock_provider.async_generate_response = AsyncMock(
        return_value="No historical data found, but stay active!"
    )

    with patch(
        "custom_components.garmin_ha_ai.services.get_ai_provider",
        return_value=mock_provider,
    ):
        response = await hass.services.async_call(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            {"question": "How are my stats?"},
            blocking=True,
            return_response=True,
        )

    assert response["answer"] == "No historical data found, but stay active!"


@pytest.mark.asyncio
async def test_ask_question_not_setup_error(hass: HomeAssistant):
    """Test ask_question error when integration is not set up in hass.data."""
    await async_setup_services(hass)

    with pytest.raises(HomeAssistantError, match="integration is not set up"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            {"question": "Hello?"},
            blocking=True,
            return_response=True,
        )
