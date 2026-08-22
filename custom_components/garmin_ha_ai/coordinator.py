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
    CONF_AI_MODEL,
    CONF_AI_PROVIDER,
    CONF_COACHING_DIRECTIVES,
    CONF_FITNESS_GOALS,
    CONF_NOTIFICATION_TARGETS,
    CONF_RETENTION_DAYS,
    DEFAULT_AI_PROVIDER,
    DEFAULT_POLLING_INTERVAL_HOURS,
    DEFAULT_RETENTION_DAYS,
    DOMAIN,
    LOGGER,
    REPORT_VIEW_OPTIONS,
    REPORT_VIEW_SHORT,
)
from .garmin_client import (
    GarminClient,
    GarminConnectTooManyRequestsError,
    GarminRateLimitError,
)
from .models import AIHealthReport, GarminDailyMetrics
from .storage import GarminStorage


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

        # Schedule daily polling intervals
        update_interval = timedelta(hours=DEFAULT_POLLING_INTERVAL_HOURS)

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

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
            if not metrics:
                LOGGER.debug("No cached metrics available; fetching daily metrics from Garmin")
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

            if not api_key:
                LOGGER.warning("AI provider API key is not configured; skipping report generation")
                return None

            # Assemble 5-block prompt payload
            prompt = assemble_report_prompt(
                current_metrics=metrics,
                history=history_data,
                user_goals=goals,
                coaching_directives=directives,
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
        prompt = assemble_qa_prompt(
            question=target_question,
            history=history_list,
            user_goals=goals,
            coaching_directives=directives,
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

        Called automatically by Home Assistant on scheduled interval.
        Saves snapshot to rolling history, prunes old entries, and kicks off AI report generation.
        """
        try:
            # 1. Fetch metrics from Garmin Connect Cloud
            metrics = await self.client.async_fetch_daily_metrics()

            # 2. Persist metrics snapshot into local storage
            await self.storage.async_save_daily_metrics(metrics.to_dict())

            # 3. Prune history older than configured retention period
            options = {**self.entry.data, **self.entry.options}
            retention_days = int(options.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS))
            await self.storage.async_prune_history(retention_days)

            LOGGER.debug(
                "Successfully polled Garmin metrics for date %s: %s steps",
                metrics.date,
                metrics.steps,
            )
            self.last_update_time = dt_util.now()

            # 4. Trigger background AI report generation automatically after sync
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


