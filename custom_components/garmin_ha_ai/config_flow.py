"""Config flow for Garmin HA AI integration."""
from __future__ import annotations

import logging
from typing import Any

from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectMfaRequired,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    CONF_AI_API_KEY,
    CONF_AI_PROVIDER,
    CONF_FITNESS_GOALS,
    CONF_GARMIN_PASSWORD,
    CONF_GARMIN_USERNAME,
    CONF_MFA_CODE,
    DEFAULT_AI_PROVIDER,
    DOMAIN,
    LOGGER,
    PROVIDER_GEMINI,
    PROVIDER_OPENAI,
)
from .garmin_client import GarminClient
from .storage import GarminStorage


class GarminHaAiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Garmin HA AI."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        super().__init__()
        self._user_data: dict[str, Any] = {}
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_GARMIN_USERNAME].strip()
            password = user_input[CONF_GARMIN_PASSWORD]

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            self._user_data = dict(user_input)
            self._user_data[CONF_GARMIN_USERNAME] = username

            storage = GarminStorage(self.hass)
            client = GarminClient(self.hass, storage)

            try:
                await client.async_login_with_credentials(username, password)
                # Successful login without MFA
                return self._create_garmin_entry()
            except GarminConnectMfaRequired:
                LOGGER.info("Garmin MFA required for user: %s", username)
                return await self.async_step_mfa()
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except GarminConnectConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception in config flow: %s", err)
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_GARMIN_USERNAME): str,
                vol.Required(CONF_GARMIN_PASSWORD): str,
                vol.Required(
                    CONF_AI_PROVIDER, default=DEFAULT_AI_PROVIDER
                ): vol.In([PROVIDER_GEMINI, PROVIDER_OPENAI]),
                vol.Required(CONF_AI_API_KEY): str,
                vol.Optional(CONF_FITNESS_GOALS, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle MFA passcode verification step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mfa_code = user_input[CONF_MFA_CODE].strip()
            username = self._user_data[CONF_GARMIN_USERNAME]
            password = self._user_data[CONF_GARMIN_PASSWORD]

            storage = GarminStorage(self.hass)
            client = GarminClient(self.hass, storage)

            try:
                await client.async_login_with_credentials(
                    username, password, mfa_code=mfa_code
                )
                return self._create_garmin_entry()
            except (ConfigEntryAuthFailed, GarminConnectAuthenticationError):
                errors["base"] = "invalid_mfa"
            except GarminConnectConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception during MFA step: %s", err)
                errors["base"] = "unknown"

        schema = vol.Schema({vol.Required(CONF_MFA_CODE): str})

        return self.async_show_form(
            step_id="mfa", data_schema=schema, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication trigger."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm re-authentication with updated credentials."""
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry:
            username = self._reauth_entry.data[CONF_GARMIN_USERNAME]
            password = user_input[CONF_GARMIN_PASSWORD]

            storage = GarminStorage(self.hass)
            client = GarminClient(self.hass, storage)

            try:
                await client.async_login_with_credentials(username, password)
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                )
                return self.async_abort(reason="reauth_successful")
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

        schema = vol.Schema({vol.Required(CONF_GARMIN_PASSWORD): str})

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors
        )

    def _create_garmin_entry(self) -> FlowResult:
        """Create config entry without storing plaintext password in config entry data."""
        username = self._user_data[CONF_GARMIN_USERNAME]
        entry_data = {
            CONF_GARMIN_USERNAME: username,
            CONF_AI_PROVIDER: self._user_data[CONF_AI_PROVIDER],
            CONF_AI_API_KEY: self._user_data[CONF_AI_API_KEY],
            CONF_FITNESS_GOALS: self._user_data.get(CONF_FITNESS_GOALS, ""),
        }
        return self.async_create_entry(
            title=f"Garmin ({username})", data=entry_data
        )
