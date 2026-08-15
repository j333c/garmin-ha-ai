"""Garmin client authentication adapter for Garmin HA AI integration."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import LOGGER
from .models import GarminDailyMetrics
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

    async def async_fetch_daily_metrics(
        self, target_date: date | str | None = None
    ) -> GarminDailyMetrics:
        """Fetch and normalize daily health statistics for a target date."""
        if isinstance(target_date, date):
            date_str = target_date.isoformat()
        elif isinstance(target_date, str):
            date_str = target_date
        else:
            date_str = date.today().isoformat()

        client = await self.async_get_client()

        def _fetch_sync() -> GarminDailyMetrics:
            summary_data: dict[str, Any] = {}
            try:
                summary_data = client.get_user_summary(date_str) or {}
            except Exception as err:
                LOGGER.warning("Could not fetch user summary for %s: %s", date_str, err)

            sleep_score: int | None = None
            try:
                sleep_data = client.get_sleep_data(date_str) or {}
                daily_sleep = sleep_data.get("dailySleepDTO", {})
                scores = daily_sleep.get("sleepScores", {})
                overall = scores.get("overall", {})
                if isinstance(overall, dict):
                    sleep_score = overall.get("value")
            except Exception as err:
                LOGGER.debug("Could not fetch sleep data for %s: %s", date_str, err)

            hrv_status: str | None = None
            try:
                hrv_data = client.get_hrv_data(date_str) or {}
                summary = hrv_data.get("hrvSummary", {})
                if isinstance(summary, dict):
                    hrv_status = summary.get("status")
            except Exception as err:
                LOGGER.debug("Could not fetch HRV data for %s: %s", date_str, err)

            activities: list[dict[str, Any]] = []
            try:
                raw_activities = client.get_activities_by_date(date_str, date_str) or []
                for act in raw_activities:
                    act_type = (
                        act.get("activityType", {}).get("typeKey")
                        if isinstance(act.get("activityType"), dict)
                        else None
                    )
                    activities.append({
                        "activity_id": act.get("activityId"),
                        "name": act.get("activityName"),
                        "type": act_type,
                        "duration_sec": act.get("duration"),
                        "distance_m": act.get("distance"),
                        "calories": act.get("calories"),
                    })
            except Exception as err:
                LOGGER.debug("Could not fetch activities for %s: %s", date_str, err)

            steps = summary_data.get("totalSteps")
            distance_m = summary_data.get("totalDistanceMeters")
            distance_km = round(distance_m / 1000.0, 2) if distance_m is not None else None
            total_calories = summary_data.get("totalKilocalories") or summary_data.get(
                "activeKilocalories"
            )
            resting_hr = summary_data.get("restingHeartRate")
            avg_stress = summary_data.get("averageStressLevel")
            body_battery_min = summary_data.get("bodyBatteryMinValue")
            body_battery_max = summary_data.get("bodyBatteryMaxValue")

            weight_g = summary_data.get("weight")
            weight_kg = (
                round(weight_g / 1000.0, 2)
                if weight_g is not None and weight_g > 200
                else (weight_g if weight_g else None)
            )

            return GarminDailyMetrics(
                date=date_str,
                steps=steps,
                distance_km=distance_km,
                total_calories=total_calories,
                resting_hr=resting_hr,
                avg_stress=avg_stress,
                sleep_score=sleep_score,
                hrv_status=hrv_status,
                body_battery_min=body_battery_min,
                body_battery_max=body_battery_max,
                weight_kg=weight_kg,
                activities=activities,
            )

        return await self.hass.async_add_executor_job(_fetch_sync)
