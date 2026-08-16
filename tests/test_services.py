"""Tests for Garmin HA AI custom services."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.garmin_ha_ai.const import (
    DOMAIN,
    SERVICE_ASK_QUESTION,
    SERVICE_GENERATE_REPORT,
)
from custom_components.garmin_ha_ai.services import async_setup_services


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
def mock_coordinator():
    """Mock GarminDataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.async_ask_question = AsyncMock(
        return_value="You should run 5km today at an easy pace."
    )
    coordinator.async_generate_report = AsyncMock()
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
        "context_days": 3,
    }
    mock_coordinator.async_ask_question.assert_called_once_with(
        question="Should I run today?", days_history=7
    )


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

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        {"question": "How's my progression?", "days_history": 100},
        blocking=True,
        return_response=True,
    )

    assert response["answer"] == "You should run 5km today at an easy pace."
    assert response["context_days"] == 3
    mock_coordinator.async_ask_question.assert_called_once_with(
        question="How's my progression?", days_history=100
    )


@pytest.mark.asyncio
async def test_ask_question_coordinator_error_propagation(
    hass: HomeAssistant, mock_storage, mock_coordinator
):
    """Test that ask_question propagates HomeAssistantError from coordinator."""
    await async_setup_services(hass)

    mock_coordinator.async_ask_question = AsyncMock(
        side_effect=HomeAssistantError("AI API key is not configured.")
    )

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

    mock_coordinator.async_ask_question = AsyncMock(
        return_value="No historical data found, but stay active!"
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": empty_storage,
        "coordinator": mock_coordinator,
    }

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        {"question": "How are my stats?"},
        blocking=True,
        return_response=True,
    )

    assert response["answer"] == "No historical data found, but stay active!"
    assert response["context_days"] == 0


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


@pytest.mark.asyncio
async def test_ask_question_with_response_entity(
    hass: HomeAssistant, mock_storage, mock_coordinator
):
    """Test ask_question service sets state on target response_entity."""
    await async_setup_services(hass)

    mock_coordinator.async_ask_question = AsyncMock(
        return_value="Target entity answer."
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": mock_storage,
        "coordinator": mock_coordinator,
    }

    await hass.services.async_call(
        DOMAIN,
        SERVICE_ASK_QUESTION,
        {
            "question": "Status?",
            "response_entity": "sensor.custom_response_target",
        },
        blocking=True,
        return_response=True,
    )

    hass.states.async_set.assert_called_once_with(
        "sensor.custom_response_target",
        "Target entity answer.",
        {
            "full_answer": "Target entity answer.",
            "question": "Status?",
            "context_days": 3,
        },
    )


@pytest.mark.asyncio
async def test_generate_report_service_call(
    hass: HomeAssistant, mock_storage, mock_coordinator
):
    """Test generate_report service triggers coordinator.async_generate_report(force=True)."""
    await async_setup_services(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = {
        "storage": mock_storage,
        "coordinator": mock_coordinator,
    }

    await hass.services.async_call(
        DOMAIN,
        SERVICE_GENERATE_REPORT,
        {},
        blocking=True,
    )

    mock_coordinator.async_generate_report.assert_called_once_with(force=True)
