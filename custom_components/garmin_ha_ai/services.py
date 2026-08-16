"""Service definitions for Garmin HA AI integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    LOGGER,
    SERVICE_ASK_QUESTION,
    SERVICE_GENERATE_REPORT,
)
from .storage import GarminStorage

SERVICE_GENERATE_REPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_ASK_QUESTION_SCHEMA = vol.Schema(
    {
        vol.Required("question"): cv.string,
        vol.Optional("days_history", default=7): cv.positive_int,
        vol.Optional("response_entity"): cv.string,
        vol.Optional("entry_id"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up custom services for Garmin HA AI integration."""

    async def handle_generate_report(call: ServiceCall) -> None:
        """Handle generate_report service call."""
        domain_data = hass.data.get(DOMAIN, {})
        target_entry_id = call.data.get("entry_id")

        if target_entry_id:
            entry_data = domain_data.get(target_entry_id)
            if not entry_data or "coordinator" not in entry_data:
                raise HomeAssistantError(f"Garmin HA AI entry '{target_entry_id}' not found.")
            await entry_data["coordinator"].async_generate_report(force=True)
            return

        for entry_id, entry_data in domain_data.items():
            if isinstance(entry_data, dict) and "coordinator" in entry_data:
                coordinator = entry_data["coordinator"]
                await coordinator.async_generate_report(force=True)

    async def handle_ask_question(call: ServiceCall) -> ServiceResponse:
        """Handle ask_question service call with direct response support."""
        question: str = call.data["question"]
        days_history: int = call.data.get("days_history", 7)
        target_entry_id = call.data.get("entry_id")

        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise HomeAssistantError("Garmin HA AI integration is not set up.")

        entry_data = None
        if target_entry_id:
            entry_data = domain_data.get(target_entry_id)
            if not entry_data or "storage" not in entry_data or "coordinator" not in entry_data:
                raise HomeAssistantError(f"Garmin HA AI entry '{target_entry_id}' not found.")
        else:
            # Obtain first active entry data
            for data in domain_data.values():
                if isinstance(data, dict) and "storage" in data and "coordinator" in data:
                    entry_data = data
                    break

        if not entry_data:
            raise HomeAssistantError("No active Garmin HA AI entry found.")

        storage: GarminStorage = entry_data["storage"]
        coordinator = entry_data["coordinator"]

        # Calculate context_days for response payload
        history_dict = await storage.async_load_history()
        context_days = 0
        if isinstance(history_dict, dict) and history_dict:
            clamped_days = max(1, min(days_history, 90))
            context_days = min(clamped_days, len(history_dict))

        answer_text = await coordinator.async_ask_question(
            question=question, days_history=days_history
        )

        response_entity = call.data.get("response_entity")
        if response_entity:
            short_val = answer_text[:247] + "..." if len(answer_text) > 250 else answer_text
            hass.states.async_set(
                response_entity,
                short_val,
                {
                    "full_answer": answer_text,
                    "question": question,
                    "context_days": context_days,
                },
            )

        return {
            "answer": answer_text,
            "question": question,
            "context_days": context_days,
        }

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_REPORT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GENERATE_REPORT,
            handle_generate_report,
            schema=SERVICE_GENERATE_REPORT_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ASK_QUESTION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            handle_ask_question,
            schema=SERVICE_ASK_QUESTION_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
