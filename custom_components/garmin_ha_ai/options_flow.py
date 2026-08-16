"""Options flow for Garmin HA AI integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_NOTIFICATION_TARGETS,
    CONF_POLLING_SCHEDULE,
    CONF_RETENTION_DAYS,
    DEFAULT_POLLING_TIME,
    DEFAULT_RETENTION_DAYS,
    LOGGER,
    MAX_RETENTION_DAYS,
    MIN_RETENTION_DAYS,
)
from .storage import GarminStorage


class GarminHaAiOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Garmin HA AI."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        super().__init__()
        if config_entry is not None:
            self.config_entry = config_entry
            self.handler = config_entry.entry_id


    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            retention_days = user_input.get(
                CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS
            )
            storage = GarminStorage(self.hass)
            try:
                await storage.async_prune_history(retention_days)
            except Exception as err:
                LOGGER.warning("Error pruning history during options flow: %s", err)

            return self.async_create_entry(title="", data=user_input)

        current_options = self.config_entry.options
        current_data = self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_RETENTION_DAYS,
                    default=current_options.get(
                        CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_RETENTION_DAYS, max=MAX_RETENTION_DAYS),
                ),
                vol.Optional(
                    CONF_FITNESS_GOALS,
                    default=current_options.get(
                        CONF_FITNESS_GOALS, current_data.get(CONF_FITNESS_GOALS, "")
                    ),
                ): str,
                vol.Optional(
                    CONF_COACHING_DIRECTIVES,
                    default=current_options.get(CONF_COACHING_DIRECTIVES, ""),
                ): str,
                vol.Optional(
                    CONF_NOTIFICATION_TARGETS,
                    default=current_options.get(CONF_NOTIFICATION_TARGETS, ""),
                ): str,
                vol.Optional(
                    CONF_POLLING_SCHEDULE,
                    default=current_options.get(
                        CONF_POLLING_SCHEDULE, DEFAULT_POLLING_TIME
                    ),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
