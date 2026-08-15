"""Garmin client authentication adapter for Garmin HA AI integration."""
from __future__ import annotations

import logging
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import LOGGER
from .storage import GarminStorage


class GarminClient:
    """Authentication adapter wrapping python-garminconnect with token persistence."""

    def __init__(self, hass: HomeAssistant, storage: GarminStorage) -> None:
        """Initialize GarminClient wrapper."""
        self.hass = hass
        self.storage = storage
        self.client: Garmin | None = None

    async def async_login_with_tokens(self) -> bool:
        """Attempt to resume session using stored OAuth tokens.

        Returns True if successful, False if no stored tokens.
        Raises ConfigEntryAuthFailed if token restoration/login fails due to auth errors.
        """
        tokens = await self.storage.async_load_tokens()
        if not tokens or "tokenstore" not in tokens:
            LOGGER.debug("No stored Garmin OAuth tokens found")
            return False

        def _restore_session() -> Garmin:
            client = Garmin()
            client.garth.loads(tokens["tokenstore"])
            client.login()
            return client

        try:
            self.client = await self.hass.async_add_executor_job(_restore_session)
            LOGGER.debug("Garmin session successfully restored from tokens")
            await self._async_save_current_tokens()
            return True
        except (GarminConnectAuthenticationError, KeyError) as err:
            LOGGER.warning("Garmin OAuth token authentication failed: %s", err)
            raise ConfigEntryAuthFailed("Garmin OAuth tokens expired or revoked") from err
        except GarminConnectConnectionError as err:
            LOGGER.warning("Network error restoring Garmin session: %s", err)
            raise
        except Exception as err:
            LOGGER.error("Unexpected error restoring Garmin session: %s", err)
            raise ConfigEntryAuthFailed("Unexpected error during Garmin token authentication") from err

    async def async_login_with_credentials(
        self, username: str, password: str, mfa_code: str | None = None
    ) -> dict[str, Any]:
        """Authenticate with Garmin Connect using email/password and optional MFA code.

        Returns token dictionary on success.
        Raises ConfigEntryAuthFailed on invalid credentials.
        """
        def _credential_login() -> Garmin:
            client = Garmin(email=username, password=password)
            if mfa_code:
                client.login(mfa_code=mfa_code)
            else:
                client.login()
            return client

        try:
            self.client = await self.hass.async_add_executor_job(_credential_login)
            LOGGER.info("Successfully authenticated with Garmin Connect")
            return await self._async_save_current_tokens()
        except GarminConnectAuthenticationError as err:
            LOGGER.warning("Garmin authentication failed")
            raise ConfigEntryAuthFailed("Invalid Garmin credentials") from err
        except Exception as err:
            LOGGER.error("Error during Garmin credential authentication: %s", err)
            raise ConfigEntryAuthFailed("Garmin authentication failed") from err

    async def _async_save_current_tokens(self) -> dict[str, Any]:
        """Extract current tokens from garth and save to GarminStorage."""
        if not self.client or not hasattr(self.client, "garth"):
            return {}

        def _dump_tokens() -> str:
            return self.client.garth.dumps()

        token_str = await self.hass.async_add_executor_job(_dump_tokens)
        token_data = {"tokenstore": token_str}
        await self.storage.async_save_tokens(token_data)
        return token_data

    async def async_get_client(self) -> Garmin:
        """Ensure an authenticated Garmin client instance is available.

        If not authenticated, attempts token login or raises ConfigEntryAuthFailed.
        """
        if self.client:
            return self.client

        success = await self.async_login_with_tokens()
        if not success or not self.client:
            raise ConfigEntryAuthFailed("No valid Garmin session available")
        return self.client
