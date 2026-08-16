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

from .ai_engine import (
    AIEngineError,
    assemble_qa_prompt,
    get_ai_provider,
)
from .const import (
    CONF_AI_API_KEY,
    CONF_AI_BASE_URL,
    CONF_AI_MODEL,
    CONF_AI_PROVIDER,
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    DEFAULT_AI_PROVIDER,
    DOMAIN,
    LOGGER,
    SERVICE_ASK_QUESTION,
    SERVICE_GENERATE_REPORT,
)
from .storage import GarminStorage

SERVICE_ASK_QUESTION_SCHEMA = vol.Schema(
    {
        vol.Required("question"): cv.string,
        vol.Optional("days_history", default=7): cv.positive_int,
        vol.Optional("response_entity"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up custom services for Garmin HA AI integration."""

    async def handle_generate_report(call: ServiceCall) -> None:
        """Handle generate_report service call."""
        domain_data = hass.data.get(DOMAIN, {})
        for entry_id, entry_data in domain_data.items():
            if isinstance(entry_data, dict) and "coordinator" in entry_data:
                coordinator = entry_data["coordinator"]
                await coordinator.async_generate_report(force=True)

    async def handle_ask_question(call: ServiceCall) -> ServiceResponse:
        """Handle ask_question service call with direct response support."""
        question: str = call.data["question"]
        days_history: int = call.data.get("days_history", 7)

        domain_data = hass.data.get(DOMAIN, {})
        if not domain_data:
            raise HomeAssistantError("Garmin HA AI integration is not set up.")

        # Obtain active entry data
        entry_data = None
        for data in domain_data.values():
            if isinstance(data, dict) and "storage" in data and "coordinator" in data:
                entry_data = data
                break

        if not entry_data:
            raise HomeAssistantError("No active Garmin HA AI entry found.")

        storage: GarminStorage = entry_data["storage"]
        coordinator = entry_data["coordinator"]
        entry = coordinator.entry

        options = {**entry.data, **entry.options}
        provider_type = options.get(CONF_AI_PROVIDER, DEFAULT_AI_PROVIDER)
        api_key = options.get(CONF_AI_API_KEY, "")
        model = options.get(CONF_AI_MODEL)
        base_url = options.get(CONF_AI_BASE_URL)
        goals = options.get(CONF_FITNESS_GOALS)
        directives = options.get(CONF_COACHING_DIRECTIVES)

        if not api_key:
            raise HomeAssistantError("AI API key is not configured.")

        # Load local metric history from storage
        history_dict = await storage.async_load_history()
        history_list = []
        if isinstance(history_dict, dict) and history_dict:
            sorted_dates = sorted(history_dict.keys())
            # Clamp days_history (range 1..90)
            clamped_days = max(1, min(days_history, 90))
            available_days = min(clamped_days, len(sorted_dates))
            recent_dates = sorted_dates[-available_days:] if available_days > 0 else []
            history_list = [history_dict[d] for d in recent_dates]

        prompt = assemble_qa_prompt(
            question=question,
            history=history_list,
            user_goals=goals,
            coaching_directives=directives,
        )

        response_entity = call.data.get("response_entity")

        try:
            provider = get_ai_provider(
                provider_type=provider_type,
                api_key=api_key,
                model=model,
                base_url=base_url,
                hass=hass,
            )
            answer_text = await provider.async_generate_response(prompt)
            await coordinator.async_set_latest_answer(question, answer_text)

            if response_entity:
                short_val = answer_text[:247] + "..." if len(answer_text) > 250 else answer_text
                hass.states.async_set(
                    response_entity,
                    short_val,
                    {
                        "full_answer": answer_text,
                        "question": question,
                        "context_days": len(history_list),
                    },
                )
        except AIEngineError as err:
            LOGGER.error("AI Engine error during Q&A call: %s", err)
            raise HomeAssistantError(f"AI Engine error: {err}") from err
        except Exception as err:
            LOGGER.exception("Unexpected error during Q&A execution: %s", err)
            raise HomeAssistantError(f"Q&A execution failed: {err}") from err

        return {
            "answer": answer_text,
            "question": question,
            "context_days": len(history_list),
        }

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_REPORT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GENERATE_REPORT,
            handle_generate_report,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ASK_QUESTION):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ASK_QUESTION,
            handle_ask_question,
            schema=SERVICE_ASK_QUESTION_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )
