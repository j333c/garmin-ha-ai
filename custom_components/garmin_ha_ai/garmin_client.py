"""Garmin client authentication adapter for Garmin HA AI integration."""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

try:
    from garminconnect import (
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
except ImportError:
    # Graceful fallback in environments where python-garminconnect is mocked or partially installed
    from garminconnect import (  # type: ignore[no-redef]
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
    )

    class GarminConnectTooManyRequestsError(GarminConnectConnectionError):  # type: ignore[no-redef]
        """Fallback exception for Garmin rate limiting."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.util.dt as dt_util

from .const import LOGGER
from .models import GarminDailyMetrics
from .storage import GarminStorage


class GarminMfaRequired(Exception):
    """Exception raised when Garmin Connect requires MFA verification."""


GarminConnectMfaRequired = GarminMfaRequired


class GarminRateLimitError(GarminConnectConnectionError):
    """Exception raised when Garmin Connect rate-limits requests (HTTP 429)."""


def _parse_weight(weight_raw: Any) -> float | None:
    """Normalize weight value from Garmin Connect API.

    Garmin Connect API returns weight in grams (e.g. 72500 for 72.5 kg) in user summary,
    or in kilograms in certain endpoints. If the value exceeds 200, assume grams and divide by 1000.
    """
    if weight_raw is None:
        return None
    try:
        val = float(weight_raw)
        if val <= 0:
            return None
        # Convert grams to kilograms if value > 200
        return round(val / 1000.0, 2) if val > 200 else round(val, 2)
    except (ValueError, TypeError):
        return None


def _parse_sleep_data(sleep_data: dict[str, Any] | None) -> int | None:
    """Extract overall sleep score integer from Garmin sleep payload.

    Navigates dailySleepDTO -> sleepScores -> overall -> value.
    """
    if not sleep_data or not isinstance(sleep_data, dict):
        return None

    try:
        daily_sleep = sleep_data.get("dailySleepDTO", {})
        if isinstance(daily_sleep, dict):
            scores = daily_sleep.get("sleepScores", {})
            if isinstance(scores, dict):
                overall = scores.get("overall", {})
                if isinstance(overall, dict):
                    val = overall.get("value")
                    return int(val) if val is not None else None
    except (ValueError, TypeError):
        pass
    return None


def _parse_hrv_data(hrv_data: dict[str, Any] | None) -> str | None:
    """Extract HRV status string from Garmin HRV payload.

    Navigates hrvSummary -> status (e.g., 'BALANCED', 'UNBALANCED', 'LOW', 'POOR').
    """
    if not hrv_data or not isinstance(hrv_data, dict):
        return None

    try:
        summary = hrv_data.get("hrvSummary", {})
        if isinstance(summary, dict):
            status = summary.get("status")
            return str(status) if status else None
    except Exception:
        pass
    return None


def _parse_activities(raw_activities: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalize activity list extracted from Garmin Connect.

    Extracts activity ID, display name, activity type key, duration, distance, and calories.
    """
    if not raw_activities or not isinstance(raw_activities, list):
        return []

    activities: list[dict[str, Any]] = []
    for act in raw_activities:
        if not isinstance(act, dict):
            continue

        act_type = None
        if isinstance(act.get("activityType"), dict):
            act_type = act["activityType"].get("typeKey")

        activities.append({
            "activity_id": act.get("activityId"),
            "name": act.get("activityName"),
            "type": act_type,
            "duration_sec": act.get("duration"),
            "distance_m": act.get("distance"),
            "calories": act.get("calories"),
        })
    return activities


def _parse_user_summary(summary_data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract and normalize core daily metric figures from Garmin user summary payload.

    Converts distance meters to kilometers and normalizes calories and heart rate.
    """
    if not summary_data or not isinstance(summary_data, dict):
        return {}

    steps = summary_data.get("totalSteps")
    distance_m = summary_data.get("totalDistanceMeters")
    distance_km = round(distance_m / 1000.0, 2) if distance_m is not None else None
    total_calories = summary_data.get("totalKilocalories") or summary_data.get("activeKilocalories")
    resting_hr = summary_data.get("restingHeartRate")
    avg_stress = summary_data.get("averageStressLevel")
    body_battery_min = summary_data.get("bodyBatteryMinValue")
    body_battery_max = summary_data.get("bodyBatteryMaxValue")
    weight_kg = _parse_weight(summary_data.get("weight"))

    return {
        "steps": steps,
        "distance_km": distance_km,
        "total_calories": total_calories,
        "resting_hr": resting_hr,
        "avg_stress": avg_stress,
        "body_battery_min": body_battery_min,
        "body_battery_max": body_battery_max,
        "weight_kg": weight_kg,
    }


def _serialize_session_tokens(client: Garmin | None) -> str:
    """Extract serialized token state string across different python-garminconnect versions."""
    if not client:
        return ""

    # Modern python-garminconnect uses garth under the hood
    if hasattr(client, "garth") and hasattr(client.garth, "dumps") and callable(client.garth.dumps):
        return client.garth.dumps()

    # Legacy garminconnect dump methods
    if hasattr(client, "dumps") and callable(client.dumps):
        return client.dumps()
    if hasattr(client, "client") and hasattr(client.client, "dumps") and callable(client.client.dumps):
        return client.client.dumps()

    # Fallback to manual dictionary serialization of client tokens
    if hasattr(client, "client"):
        c = client.client
        token_dict = {
            "di_token": getattr(c, "di_token", None),
            "di_refresh_token": getattr(c, "di_refresh_token", None),
            "di_client_id": getattr(c, "di_client_id", None),
            "jwt_web": getattr(c, "jwt_web", None),
            "csrf_token": getattr(c, "csrf_token", None),
        }
        return json.dumps(token_dict)
    return ""


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
            token_data = tokens["tokenstore"]
            # Restore tokens via garth if supported
            if hasattr(client, "garth") and hasattr(client.garth, "loads"):
                client.garth.loads(token_data)
                client.login()
            else:
                try:
                    client.login(tokenstore=token_data)
                except TypeError:
                    if hasattr(client, "client") and hasattr(client.client, "loads"):
                        client.client.loads(token_data)
                        client.login()
                    else:
                        client.login()
            return client

        try:
            # Execute blocking authentication call in HA executor thread
            self.client = await self.hass.async_add_executor_job(_restore_session)
            LOGGER.debug("Garmin session successfully restored from tokens")
            await self._async_save_current_tokens()
            return True
        except (GarminConnectTooManyRequestsError, GarminRateLimitError) as err:
            LOGGER.warning("Garmin Connect rate limit (HTTP 429) during token restore: %s", err)
            raise GarminRateLimitError(f"Garmin rate limit reached: {err}") from err
        except GarminConnectConnectionError as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                LOGGER.warning("Garmin Connect rate limit (HTTP 429): %s", err)
                raise GarminRateLimitError(f"Garmin rate limit reached: {err}") from err
            LOGGER.warning("Network error restoring Garmin session: %s", err)
            raise
        except (GarminConnectAuthenticationError, KeyError) as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                LOGGER.warning("Garmin Connect rate limit (HTTP 429) during auth: %s", err)
                raise GarminRateLimitError(f"Garmin rate limit reached: {err}") from err
            LOGGER.warning("Garmin OAuth token authentication failed: %s", err)
            raise ConfigEntryAuthFailed("Garmin OAuth tokens expired or revoked") from err
        except Exception as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                LOGGER.warning("Garmin Connect rate limit (HTTP 429): %s", err)
                raise GarminRateLimitError(f"Garmin rate limit reached: {err}") from err
            LOGGER.error("Unexpected error restoring Garmin session: %s", err)
            raise ConfigEntryAuthFailed("Unexpected error during Garmin token authentication") from err

    async def async_login_with_credentials(
        self, username: str, password: str, mfa_code: str | None = None
    ) -> dict[str, Any]:
        """Authenticate with Garmin Connect using email/password and optional MFA code.

        Returns token dictionary on success.
        Raises GarminMfaRequired if MFA is requested.
        Raises ConfigEntryAuthFailed on invalid credentials.
        """
        def _credential_login() -> Garmin:
            client = Garmin(email=username, password=password)
            if mfa_code:
                # If MFA code provided, pass it directly to login
                try:
                    client.login(mfa_code=mfa_code)
                except TypeError:
                    client.login()
                return client

            # Intercept MFA prompt callback from python-garminconnect
            def mfa_callback():
                raise GarminMfaRequired("Garmin MFA required")

            try:
                client.prompt_mfa = mfa_callback
            except Exception:
                pass

            try:
                res = client.login()
            except GarminMfaRequired:
                raise
            except Exception as err:
                err_msg = str(err).lower()
                if "mfa" in err_msg or "2fa" in err_msg or "verification code" in err_msg:
                    raise GarminMfaRequired("Garmin MFA required") from err
                raise

            if isinstance(res, tuple) and len(res) > 0 and res[0] == "needs_mfa":
                raise GarminMfaRequired("Garmin MFA required")

            return client

        try:
            # Execute blocking login call off the main event loop
            self.client = await self.hass.async_add_executor_job(_credential_login)
            LOGGER.info("Successfully authenticated with Garmin Connect")
            return await self._async_save_current_tokens()
        except (GarminMfaRequired, GarminRateLimitError, GarminConnectTooManyRequestsError, GarminConnectConnectionError):
            raise
        except GarminConnectAuthenticationError as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                LOGGER.warning("Garmin Connect rate limit (HTTP 429) during login: %s", err)
                raise GarminRateLimitError(f"Garmin rate limit reached: {err}") from err
            LOGGER.warning("Garmin authentication failed")
            raise ConfigEntryAuthFailed("Invalid Garmin credentials") from err
        except Exception as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
                LOGGER.warning("Garmin Connect rate limit (HTTP 429) during login: %s", err)
                raise GarminRateLimitError(f"Garmin rate limit reached: {err}") from err
            LOGGER.error("Error during Garmin credential authentication: %s", err)
            raise ConfigEntryAuthFailed("Garmin authentication failed") from err

    async def _async_save_current_tokens(self) -> dict[str, Any]:
        """Extract current session tokens and persist to GarminStorage."""
        if not self.client:
            return {}

        try:
            token_str = await self.hass.async_add_executor_job(_serialize_session_tokens, self.client)
            if token_str:
                token_data = {"tokenstore": token_str}
                await self.storage.async_save_tokens(token_data)
                return token_data
        except Exception as err:
            LOGGER.warning("Could not serialize Garmin session tokens: %s", err)
        return {}

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
            try:
                date_str = dt_util.now().date().isoformat()
            except Exception:
                date_str = date.today().isoformat()

        client = await self.async_get_client()

        def _fetch_sync() -> GarminDailyMetrics:
            # 1. Fetch user daily summary
            summary_data: dict[str, Any] = {}
            try:
                summary_data = client.get_user_summary(date_str) or {}
            except (GarminConnectAuthenticationError, GarminConnectConnectionError):
                raise
            except Exception as err:
                LOGGER.warning("Could not fetch user summary for %s: %s", date_str, err)

            # 2. Fetch sleep data
            sleep_score: int | None = None
            try:
                sleep_raw = client.get_sleep_data(date_str) or {}
                sleep_score = _parse_sleep_data(sleep_raw)
            except GarminConnectAuthenticationError:
                raise
            except Exception as err:
                LOGGER.debug("Could not fetch sleep data for %s: %s", date_str, err)

            # 3. Fetch HRV data
            hrv_status: str | None = None
            try:
                hrv_raw = client.get_hrv_data(date_str) or {}
                hrv_status = _parse_hrv_data(hrv_raw)
            except GarminConnectAuthenticationError:
                raise
            except Exception as err:
                LOGGER.debug("Could not fetch HRV data for %s: %s", date_str, err)

            # 4. Fetch activities
            activities: list[dict[str, Any]] = []
            try:
                raw_activities = client.get_activities_by_date(date_str, date_str) or []
                activities = _parse_activities(raw_activities)
            except GarminConnectAuthenticationError:
                raise
            except Exception as err:
                LOGGER.debug("Could not fetch activities for %s: %s", date_str, err)

            # 5. Extract core metrics
            summary_metrics = _parse_user_summary(summary_data)

            # 6. Assemble normalized GarminDailyMetrics dataclass
            return GarminDailyMetrics(
                date=date_str,
                steps=summary_metrics.get("steps"),
                distance_km=summary_metrics.get("distance_km"),
                total_calories=summary_metrics.get("total_calories"),
                resting_hr=summary_metrics.get("resting_hr"),
                avg_stress=summary_metrics.get("avg_stress"),
                sleep_score=sleep_score,
                hrv_status=hrv_status,
                body_battery_min=summary_metrics.get("body_battery_min"),
                body_battery_max=summary_metrics.get("body_battery_max"),
                weight_kg=summary_metrics.get("weight_kg"),
                activities=activities,
            )

        try:
            return await self.hass.async_add_executor_job(_fetch_sync)
        except GarminConnectAuthenticationError as err:
            LOGGER.warning("Garmin Connect authentication failed during metric fetch: %s", err)
            raise ConfigEntryAuthFailed("Garmin OAuth session expired") from err


