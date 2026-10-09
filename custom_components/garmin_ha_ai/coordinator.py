"""DataUpdateCoordinator for Garmin HA AI integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from garminconnect import (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceNotFound,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
import homeassistant.util.dt as dt_util

from .ai_engine import (
    AIEngineError,
    assemble_qa_prompt,
    assemble_report_prompt,
    get_ai_provider,
    parse_ai_health_report,
)
from .const import (
    CONF_AI_API_KEY,
    CONF_AI_BASE_URL,
    CONF_AI_LANGUAGE,
    CONF_AI_MODEL,
    CONF_AI_PROVIDER,
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_NOTIFICATION_TARGETS,
    CONF_POLLING_INTERVAL,
    CONF_POLLING_MODE,
    CONF_POLLING_SCHEDULE,
    CONF_RETENTION_DAYS,
    DEFAULT_AI_LANGUAGE,
    DEFAULT_AI_PROVIDER,
    DEFAULT_POLLING_INTERVAL_HOURS,
    DEFAULT_POLLING_MODE,
    DEFAULT_RETENTION_DAYS,
    DOMAIN,
    LOGGER,
    POLLING_MODE_INTERVAL,
    REPORT_VIEW_OPTIONS,
    REPORT_VIEW_SHORT,
)
from .exceptions import (
    AIEngineError as CentralizedAIEngineError,
    GarminAIError,
    GarminAuthError,
    GarminRateLimitError,
)
from .garmin_client import (
    GarminClient,
    GarminConnectTooManyRequestsError,
)
from .models import AIHealthReport, GarminDailyMetrics
from .storage import GarminStorage


def calculate_coordinator_interval(entry: ConfigEntry) -> timedelta:
    """Calculate polling interval based on configured polling mode."""
    options = {**entry.data, **entry.options}
    mode = options.get(CONF_POLLING_MODE, DEFAULT_POLLING_MODE)
    if mode == POLLING_MODE_INTERVAL:
        try:
            val = options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL_HOURS)
            interval_hours = int(val) if val is not None else DEFAULT_POLLING_INTERVAL_HOURS
        except (ValueError, TypeError):
            interval_hours = DEFAULT_POLLING_INTERVAL_HOURS
        return timedelta(hours=max(1, interval_hours))
    return timedelta(hours=DEFAULT_POLLING_INTERVAL_HOURS)


class GarminDataUpdateCoordinator(DataUpdateCoordinator[GarminDailyMetrics]):
    """Class to manage fetching Garmin metrics data on a scheduled interval.

    Orchestrates:
    1. Polling Garmin Connect daily metrics and storing them in local rolling history.
    2. Generating AI Health Briefings asynchronously using the configured AI provider.
    3. Dispatching notifications to configured mobile app or persistent notification targets.
    4. Processing interactive Q&A queries from Lovelace dashboard cards.
    """

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

        # State storage for AI report and interactive Q&A
        self.latest_report: AIHealthReport | None = None
        self.latest_answer: dict[str, Any] | None = None
        self.latest_error: str | None = None
        self.last_update_time: datetime | None = None
        self.last_error_time: datetime | None = None
        self._is_generating: bool = False
        self.question_input: str = ""
        self.report_display_mode: str = REPORT_VIEW_SHORT
        self._unsub_schedule = None

        # Schedule polling interval dynamically based on options
        update_interval = calculate_coordinator_interval(entry)

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

        options = {**entry.data, **entry.options}
        if options.get(CONF_POLLING_MODE, DEFAULT_POLLING_MODE) != POLLING_MODE_INTERVAL:
            self._setup_daily_schedule()

    def _setup_daily_schedule(self) -> None:
        """Register daily fixed time trigger if configured."""
        try:
            from homeassistant.helpers.event import async_track_time_change
        except Exception:
            return

        options = {**self.entry.data, **self.entry.options}
        sched = str(options.get(CONF_POLLING_SCHEDULE, "06:00:00") or "06:00:00")
        try:
            parts = [int(p) for p in sched.split(":") if p.strip()]
            hour = parts[0] if len(parts) > 0 else 6
            minute = parts[1] if len(parts) > 1 else 0
            second = parts[2] if len(parts) > 2 else 0
        except (ValueError, TypeError, IndexError):
            hour, minute, second = 6, 0, 0

        async def _scheduled_update(_now: datetime) -> None:
            LOGGER.debug("Triggering daily scheduled sync at %02d:%02d:%02d", hour, minute, second)
            await self.async_request_refresh()

        try:
            self._unsub_schedule = async_track_time_change(
                self.hass, _scheduled_update, hour=hour, minute=minute, second=second
            )
        except Exception as err:
            LOGGER.debug("Could not register time change tracker: %s", err)

    async def async_shutdown(self) -> None:
        """Clean up background listeners."""
        if self._unsub_schedule:
            self._unsub_schedule()
            self._unsub_schedule = None
        await super().async_shutdown()

    async def async_dispatch_notification(self, report: AIHealthReport) -> None:
        """Dispatch generated AI health report to configured notification targets with fault tolerance.

        Supports comma-separated targets such as:
        - 'persistent_notification' -> creates a Home Assistant persistent notification
        - 'notify.mobile_app_phone' -> sends actionable notification to Home Assistant companion app
        """
        options = {**self.entry.data, **self.entry.options}
        target_str = str(options.get(CONF_NOTIFICATION_TARGETS, "") or "").strip()

        if not target_str:
            LOGGER.debug("No notification target configured; skipping notification dispatch")
            return

        targets = [t.strip() for t in target_str.split(",") if t.strip()]
        title = "Garmin AI Daily Report"
        short_msg = report.short_summary or "New Garmin AI Health Report available."
        full_msg = report.full_report or short_msg

        for target in targets:
            try:
                # 1. Home Assistant persistent notification
                if target == "persistent_notification":
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": title,
                            "message": full_msg,
                            "notification_id": "garmin_ai_daily_report",
                        },
                    )
                    LOGGER.info("Successfully dispatched persistent notification report")
                # 2. Companion app or notify service (notify.xyz)
                elif target.startswith("notify.") and len(target.split(".", 1)[1].strip()) > 0:
                    domain, service = target.split(".", 1)
                    await self.hass.services.async_call(
                        domain,
                        service,
                        {
                            "title": title,
                            "message": short_msg,
                            "data": {"long_message": full_msg},
                        },
                    )
                    LOGGER.info("Successfully dispatched notification to %s", target)
                else:
                    LOGGER.warning("Unsupported notification target format '%s'; skipping dispatch", target)
            except (ServiceNotFound, HomeAssistantError, Exception) as err:
                LOGGER.warning("Failed to dispatch notification to target '%s': %s", target, err)

    async def async_generate_report(self, force: bool = False) -> AIHealthReport | None:
        """Generate AI Health Report with debouncing lock to prevent duplicate LLM calls."""
        if self._is_generating:
            LOGGER.warning("AI report generation already in progress; skipping duplicate trigger")
            return None

        self._is_generating = True
        try:
            metrics = self.data
            if not metrics or force:
                LOGGER.debug("Fetching fresh daily metrics from Garmin (force=%s)", force)
                metrics = await self.client.async_fetch_daily_metrics()

            # Load 7-day rolling history snapshot from local storage
            history_data = await self.storage.async_load_history()

            options = {**self.entry.data, **self.entry.options}
            provider_type = options.get(CONF_AI_PROVIDER, DEFAULT_AI_PROVIDER)
            api_key = options.get(CONF_AI_API_KEY, "")
            model = options.get(CONF_AI_MODEL)
            base_url = options.get(CONF_AI_BASE_URL)
            goals = options.get(CONF_FITNESS_GOALS)
            directives = options.get(CONF_COACHING_DIRECTIVES)
            language = options.get(CONF_AI_LANGUAGE, DEFAULT_AI_LANGUAGE)

            if not api_key:
                LOGGER.warning("AI provider API key is not configured; skipping report generation")
                return None

            # Assemble 5-block prompt payload
            prompt = assemble_report_prompt(
                current_metrics=metrics,
                history=history_data,
                user_goals=goals,
                coaching_directives=directives,
                language=language,
                hass=self.hass,
            )

            # Instantiate pluggable AI provider driver
            provider = get_ai_provider(
                provider_type=provider_type,
                api_key=api_key,
                model=model,
                base_url=base_url,
                hass=self.hass,
            )
            raw_response = await provider.async_generate_response(prompt)
            report = parse_ai_health_report(
                raw_text=raw_response,
                provider_used=provider_type,
                model_used=getattr(provider, "model", model or "default"),
            )

            # Update coordinator state and notify sensor entities
            self.latest_report = report
            self.latest_error = None
            self.last_update_time = dt_util.now()
            self.async_update_listeners()
            LOGGER.info("Successfully generated AI health report using provider %s", provider_type)

            # Dispatch notification to configured channels
            await self.async_dispatch_notification(report)
            return report
        except AIEngineError as err:
            # Capture error details for UI inspection without crashing the coordinator
            self.latest_error = str(err)
            self.last_error_time = dt_util.now()
            self.async_update_listeners()
            LOGGER.error("AI Engine error during report generation: %s", err)
            return None
        except Exception as err:
            self.latest_error = str(err)
            self.last_error_time = dt_util.now()
            self.async_update_listeners()
            LOGGER.exception("Unexpected error during AI report generation: %s", err)
            return None
        finally:
            self._is_generating = False

    def set_question_input(self, value: str) -> None:
        """Set the question input string buffer and notify UI listeners."""
        self.question_input = value
        self.async_update_listeners()

    async def async_set_question_input(self, value: str) -> None:
        """Set the question input string asynchronously."""
        self.set_question_input(value)

    def set_report_display_mode(self, mode: str) -> None:
        """Set the report display mode string."""
        if mode in REPORT_VIEW_OPTIONS:
            self.report_display_mode = mode
            self.async_update_listeners()

    async def async_set_report_display_mode(self, mode: str) -> None:
        """Set the report display mode string asynchronously."""
        self.set_report_display_mode(mode)

    async def async_ask_question(
        self, question: str | None = None, days_history: int = 7
    ) -> str:
        """Ask a question to AI provider using rolling metrics history."""
        target_question = (question or self.question_input or "").strip()
        if not target_question:
            raise HomeAssistantError("Question cannot be empty.")

        options = {**self.entry.data, **self.entry.options}
        provider_type = options.get(CONF_AI_PROVIDER, DEFAULT_AI_PROVIDER)
        api_key = options.get(CONF_AI_API_KEY, "")
        model = options.get(CONF_AI_MODEL)
        base_url = options.get(CONF_AI_BASE_URL)
        goals = options.get(CONF_FITNESS_GOALS)
        directives = options.get(CONF_COACHING_DIRECTIVES)

        if not api_key:
            raise HomeAssistantError("AI API key is not configured.")

        # Load historical metrics context and slice requested days
        history_dict = await self.storage.async_load_history()
        history_list = []
        if isinstance(history_dict, dict) and history_dict:
            sorted_dates = sorted(history_dict.keys())
            clamped_days = max(1, min(days_history, 90))
            available_days = min(clamped_days, len(sorted_dates))
            recent_dates = sorted_dates[-available_days:] if available_days > 0 else []
            history_list = [history_dict[d] for d in recent_dates]

        # Assemble interactive Q&A prompt
        language = options.get(CONF_AI_LANGUAGE, DEFAULT_AI_LANGUAGE)
        prompt = assemble_qa_prompt(
            question=target_question,
            history=history_list,
            user_goals=goals,
            coaching_directives=directives,
            language=language,
            hass=self.hass,
        )

        try:
            provider = get_ai_provider(
                provider_type=provider_type,
                api_key=api_key,
                model=model,
                base_url=base_url,
                hass=self.hass,
            )
            answer_text = await provider.async_generate_response(prompt)
            self.latest_error = None
            await self.async_set_latest_answer(target_question, answer_text)
            return answer_text
        except AIEngineError as err:
            self.latest_error = str(err)
            self.last_error_time = dt_util.now()
            self.async_update_listeners()
            LOGGER.error("AI Engine error during Q&A call: %s", err)
            raise HomeAssistantError(f"AI Engine error: {err}") from err
        except Exception as err:
            self.latest_error = str(err)
            self.last_error_time = dt_util.now()
            self.async_update_listeners()
            LOGGER.exception("Unexpected error during Q&A execution: %s", err)
            raise HomeAssistantError(f"Q&A execution failed: {err}") from err

    async def async_set_latest_answer(self, question: str, answer: str) -> None:
        """Update the latest Q&A response and notify listeners."""
        self.latest_answer = {
            "question": question,
            "answer": answer,
            "timestamp": dt_util.now().isoformat(),
        }
        self.async_update_listeners()

    async def _async_update_data(self) -> GarminDailyMetrics:
        """Fetch daily health and fitness data from Garmin Connect.

        Executes a 24-hour multi-day sliding window reconciliation:
        1. Inspects local history for latest recorded weight.
        2. Polls yesterday's finalized metrics and reconciles into local history.
        3. Polls today's metrics (with historical weight fallback if unweighed).
        4. Saves today's snapshot, updates coordinator data, and generates AI report.
        """
        try:
            today_date = dt_util.now().date()
            yesterday_date = today_date - timedelta(days=1)
            today_str = today_date.isoformat()
            yesterday_str = yesterday_date.isoformat()

            options = {**self.entry.data, **self.entry.options}
            retention_days = int(options.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS))

            # 1. Inspect local history to find most recently recorded weight
            latest_cached_weight: float | None = None
            try:
                history = await self.storage.async_load_history()
                if isinstance(history, dict) and history:
                    for d in sorted(history.keys(), reverse=True):
                        w = history[d].get("weight_kg")
                        if w is not None:
                            try:
                                latest_cached_weight = float(w)
                                break
                            except (ValueError, TypeError):
                                pass
            except Exception as err:
                LOGGER.debug("Could not inspect cached history for weight: %s", err)

            # 2. Reconcile yesterday's metrics to capture finalized workouts and sleep
            try:
                yesterday_metrics = await self.client.async_fetch_daily_metrics(
                    target_date=yesterday_str,
                    fallback_weight=latest_cached_weight,
                )
                await self.storage.async_save_and_prune_history(
                    yesterday_metrics.to_dict(), retention_days
                )
                if yesterday_metrics.weight_kg is not None:
                    latest_cached_weight = yesterday_metrics.weight_kg
                LOGGER.debug(
                    "Reconciled yesterday's Garmin metrics (%s): %s steps, %s activities",
                    yesterday_str,
                    yesterday_metrics.steps,
                    len(yesterday_metrics.activities) if yesterday_metrics.activities else 0,
                )
            except (ConfigEntryAuthFailed, GarminConnectAuthenticationError):
                raise
            except Exception as err:
                LOGGER.debug("Could not reconcile yesterday's metrics (%s): %s", yesterday_str, err)

            # 3. Fetch today's metrics from Garmin Connect Cloud
            metrics = await self.client.async_fetch_daily_metrics(
                target_date=today_str,
                fallback_weight=latest_cached_weight,
            )

            # 4. Persist today's metrics snapshot and prune old entries atomically
            await self.storage.async_save_and_prune_history(metrics.to_dict(), retention_days)

            LOGGER.debug(
                "Successfully polled Garmin metrics for date %s: %s steps",
                metrics.date,
                metrics.steps,
            )
            self.last_update_time = dt_util.now()

            # 5. Trigger background AI report generation automatically after sync
            self.hass.async_create_task(self.async_generate_report())
            return metrics
        except (ConfigEntryAuthFailed, GarminConnectAuthenticationError) as err:
            LOGGER.warning("Authentication failed during Garmin background polling: %s", err)
            raise ConfigEntryAuthFailed(f"Garmin authentication failed: {err}") from err
        except (GarminRateLimitError, GarminConnectTooManyRequestsError) as err:
            LOGGER.warning("Garmin Connect API rate limited (HTTP 429); retaining existing metrics: %s", err)
            # Retain cached data on rate limit instead of setting entities unavailable
            if self.data is not None:
                return self.data
            raise UpdateFailed(f"Garmin Connect rate limit (HTTP 429): {err}") from err
        except (GarminConnectConnectionError, Exception) as err:
            LOGGER.warning("Error fetching Garmin data: %s", err)
            raise UpdateFailed(f"Error fetching Garmin data: {err}") from err


