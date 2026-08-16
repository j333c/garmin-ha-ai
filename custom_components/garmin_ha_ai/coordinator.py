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
)
from .garmin_client import GarminClient
from .models import AIHealthReport, GarminDailyMetrics
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
        self.latest_report: AIHealthReport | None = None
        self.latest_answer: dict[str, Any] | None = None
        self.last_update_time: str | None = None
        self._is_generating: bool = False

        update_interval = timedelta(hours=DEFAULT_POLLING_INTERVAL_HOURS)

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def async_dispatch_notification(self, report: AIHealthReport) -> None:
        """Dispatch generated AI health report to configured notification targets with fault tolerance."""
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
        """Generate AI Health Report with debouncing lock."""
        if self._is_generating:
            LOGGER.warning("AI report generation already in progress; skipping duplicate trigger")
            return None

        self._is_generating = True
        try:
            metrics = self.data
            if not metrics:
                LOGGER.debug("No cached metrics available; fetching daily metrics from Garmin")
                metrics = await self.client.async_fetch_daily_metrics()

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

            prompt = assemble_report_prompt(
                current_metrics=metrics,
                history=history_data,
                user_goals=goals,
                coaching_directives=directives,
            )

            provider = get_ai_provider(
                provider_type=provider_type,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )
            raw_response = await provider.async_generate_response(prompt)
            report = parse_ai_health_report(
                raw_text=raw_response,
                provider_used=provider_type,
                model_used=getattr(provider, "model", model or "default"),
            )

            self.latest_report = report
            self.last_update_time = dt_util.now().isoformat()
            self.async_update_listeners()
            LOGGER.info("Successfully generated AI health report using provider %s", provider_type)

            await self.async_dispatch_notification(report)
            return report
        except AIEngineError as err:
            LOGGER.error("AI Engine error during report generation: %s", err)
            return None
        except Exception as err:
            LOGGER.exception("Unexpected error during AI report generation: %s", err)
            return None
        finally:
            self._is_generating = False

    async def async_set_latest_answer(self, question: str, answer: str) -> None:
        """Update the latest Q&A response and notify listeners."""
        self.latest_answer = {
            "question": question,
            "answer": answer,
            "timestamp": dt_util.now().isoformat(),
        }
        self.async_update_listeners()

    async def _async_update_data(self) -> GarminDailyMetrics:
        """Fetch daily health and fitness data from Garmin Connect."""
        try:
            metrics = await self.client.async_fetch_daily_metrics()
            await self.storage.async_save_daily_metrics(metrics.to_dict())

            options = {**self.entry.data, **self.entry.options}
            retention_days = int(options.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS))
            await self.storage.async_prune_history(retention_days)

            LOGGER.debug(
                "Successfully polled Garmin metrics for date %s: %s steps",
                metrics.date,
                metrics.steps,
            )
            self.last_update_time = dt_util.now().isoformat()
            # Trigger background AI report generation automatically after sync
            self.hass.async_create_task(self.async_generate_report())
            return metrics
        except ConfigEntryAuthFailed:
            LOGGER.warning("Authentication failed during Garmin background polling")
            raise
        except (GarminConnectConnectionError, Exception) as err:
            LOGGER.warning("Error fetching Garmin data: %s", err)
            raise UpdateFailed(f"Error fetching Garmin data: {err}") from err

