"""DataUpdateCoordinator for Garmin HA AI integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_POLLING_INTERVAL_HOURS, DOMAIN, LOGGER
from .garmin_client import GarminClient
from .models import GarminDailyMetrics
from .storage import GarminStorage


class GarminDataUpdateCoordinator(DataUpdateCoordinator[GarminDailyMetrics]):
    """Class to manage fetching Garmin metrics data on a scheduled interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: GarminClient,
        storage: GarminStorage,
    ) -> None:
        """Initialize Garmin DataUpdateCoordinator."""
        self.entry = entry
        self.client = client
        self.storage = storage

        update_interval = timedelta(hours=DEFAULT_POLLING_INTERVAL_HOURS)

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> GarminDailyMetrics:
        """Fetch daily health and fitness data from Garmin Connect."""
        try:
            metrics = await self.client.async_fetch_daily_metrics()
            await self.storage.async_save_daily_metrics(metrics.to_dict())
            LOGGER.debug(
                "Successfully polled Garmin metrics for date %s: %s steps",
                metrics.date,
                metrics.steps,
            )
            return metrics
        except ConfigEntryAuthFailed:
            LOGGER.warning("Authentication failed during Garmin background polling")
            raise
        except (GarminConnectConnectionError, Exception) as err:
            LOGGER.warning("Error fetching Garmin data: %s", err)
            raise UpdateFailed(f"Error fetching Garmin data: {err}") from err
