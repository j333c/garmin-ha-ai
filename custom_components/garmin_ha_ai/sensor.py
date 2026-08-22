"""Sensor platform for Garmin HA AI integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    REPORT_VIEW_LONG,
    REPORT_VIEW_QA,
    REPORT_VIEW_SHORT,
)
from .coordinator import GarminDataUpdateCoordinator
from .helpers import get_device_info, truncate_entity_state
from .models import GarminDailyMetrics


# Definition of standard daily health metrics exposed as numeric Home Assistant sensor entities.
# Each SensorEntityDescription specifies the unique key, friendly name, unit of measurement,
# state class (for long-term statistics in HA), and MDI icon.
SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="steps",
        name="Garmin Steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:walk",
    ),
    SensorEntityDescription(
        key="resting_hr",
        name="Garmin Resting Heart Rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:heart-pulse",
    ),
    SensorEntityDescription(
        key="sleep_score",
        name="Garmin Sleep Score",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sleep",
    ),
    SensorEntityDescription(
        key="avg_stress",
        name="Garmin Stress Level",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:emoticon-neutral-outline",
    ),
    SensorEntityDescription(
        key="weight_kg",
        name="Garmin Weight",
        native_unit_of_measurement="kg",
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:scale-bathroom",
    ),
    SensorEntityDescription(
        key="body_battery_min",
        name="Garmin Body Battery",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Garmin HA AI sensor entities from a config entry.

    Instantiates all standard Garmin metric sensors along with the AI-driven
    report sensors and registers them with Home Assistant's entity platform.
    """
    # Retrieve the shared coordinator instance attached to this config entry
    coordinator: GarminDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # 1. Create standard numeric metric sensors (steps, HR, sleep, stress, weight, body battery)
    entities: list[SensorEntity] = [
        GarminSensorEntity(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]

    # 2. Add AI-specific narrative and metadata sensors
    entities.append(GarminAIHealthReportShortSensor(coordinator, entry))
    entities.append(GarminAIHealthReportLongSensor(coordinator, entry))
    entities.append(GarminAILastAnswerSensor(coordinator, entry))
    entities.append(GarminAILastUpdateSensor(coordinator, entry))
    entities.append(GarminAISelectedReportSensor(coordinator, entry))

    async_add_entities(entities)


class GarminSensorEntity(CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity):
    """Representation of a Garmin metric sensor entity.

    Subclasses CoordinatorEntity to automatically update its state whenever the
    DataUpdateCoordinator completes a polling cycle or on-demand fetch.
    """

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        description: SensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize Garmin metric sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> Any:
        """Return native value of the sensor from coordinator data."""
        if not self.coordinator.data:
            return None

        metrics: GarminDailyMetrics = self.coordinator.data
        return getattr(metrics, self.entity_description.key, None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes providing enriched context for specific metrics."""
        if not self.coordinator.data:
            return {}

        metrics: GarminDailyMetrics = self.coordinator.data

        # For Body Battery, include both minimum recharge and peak values
        if self.entity_description.key == "body_battery_min":
            return {
                "body_battery_min": metrics.body_battery_min,
                "body_battery_max": metrics.body_battery_max,
            }

        # For Steps, provide accompanying distance, calories, and logged activity counts
        if self.entity_description.key == "steps":
            return {
                "distance_km": metrics.distance_km,
                "total_calories": metrics.total_calories,
                "activities_count": len(metrics.activities) if metrics.activities else 0,
            }

        return {}


class GarminAIHealthReportShortSensor(
    CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity
):
    """Short summary AI Health Report sensor entity with 255-character state protection.

    Exposes the 1-2 sentence executive summary generated by the AI Coach.
    Uses truncate_entity_state to ensure strict compliance with Home Assistant state limit.
    """

    _attr_icon = "mdi:brain"

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize short AI health report sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ai_health_report_short"
        self._attr_name = "Garmin AI Health Report Short"
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return truncated short report summary guaranteed to fit within 250 characters."""
        report = self.coordinator.latest_report
        if not report:
            return "No report generated yet"

        return truncate_entity_state(
            report.short_summary,
            max_len=250,
            placeholder="No summary available",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes containing report generation metadata."""
        report = self.coordinator.latest_report
        if not report:
            return {}

        return {
            "timestamp": report.timestamp,
            "provider_used": report.provider_used,
            "model_used": report.model_used,
        }


class GarminAIHealthReportLongSensor(
    CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity
):
    """Full AI Health Report sensor carrying full Markdown in extra attributes.

    Because Home Assistant state strings cannot exceed 255 characters, the native
    state displays a concise status string (e.g. 'Report generated (YYYY-MM-DD)'),
    while the complete multi-section Markdown report is placed in extra_state_attributes.
    """

    _attr_icon = "mdi:file-document-outline"

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize long AI health report sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ai_health_report_long"
        self._attr_name = "Garmin AI Health Report Long"
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return brief status line as native state."""
        report = self.coordinator.latest_report
        if not report:
            return "No report generated yet"

        date_str = report.timestamp[:10] if report.timestamp else "Available"
        return f"Report generated ({date_str})"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full Markdown report and error tracking in extra state attributes."""
        attrs: dict[str, Any] = {}

        # Include error tracking metadata if the last report generation encountered an error
        latest_error = getattr(self.coordinator, "latest_error", None)
        if isinstance(latest_error, str) and latest_error:
            attrs["last_error"] = latest_error
            err_time = getattr(self.coordinator, "last_error_time", None)
            if isinstance(err_time, datetime):
                attrs["last_error_time"] = err_time.isoformat()
            elif isinstance(err_time, str) and err_time:
                attrs["last_error_time"] = err_time

        report = self.coordinator.latest_report
        if not report:
            return attrs

        attrs.update(
            {
                "full_report": report.full_report,
                "short_summary": report.short_summary,
                "timestamp": report.timestamp,
                "provider_used": report.provider_used,
                "model_used": report.model_used,
            }
        )
        return attrs


class GarminAILastAnswerSensor(
    CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity
):
    """Last AI Q&A answer sensor entity carrying full answer Markdown in extra attributes.

    Allows user to see the latest answer provided by the AI Coach. Short summary
    is stored in the state, with full markdown answer in extra attributes.
    """

    _attr_icon = "mdi:comment-question-outline"

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize last AI answer sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ai_last_answer"
        self._attr_name = "Garmin AI Last Answer"
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return truncated short answer summary guaranteed to fit within 250 characters."""
        latest = self.coordinator.latest_answer
        if not latest or not latest.get("answer"):
            return "No question asked yet"

        return truncate_entity_state(
            str(latest["answer"]),
            max_len=250,
            placeholder="No answer available",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes including full Markdown answer and original question."""
        attrs: dict[str, Any] = {}

        # Include error tracking metadata if the last Q&A request failed
        latest_error = getattr(self.coordinator, "latest_error", None)
        if isinstance(latest_error, str) and latest_error:
            attrs["last_error"] = latest_error
            err_time = getattr(self.coordinator, "last_error_time", None)
            if isinstance(err_time, datetime):
                attrs["last_error_time"] = err_time.isoformat()
            elif isinstance(err_time, str) and err_time:
                attrs["last_error_time"] = err_time

        latest = self.coordinator.latest_answer
        if not latest:
            return attrs

        attrs.update(
            {
                "full_answer": latest.get("answer", ""),
                "question": latest.get("question", ""),
                "timestamp": latest.get("timestamp", ""),
            }
        )
        return attrs


class GarminAILastUpdateSensor(
    CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity
):
    """Timestamp sensor indicating the last successful sync and update.

    Employs SensorDeviceClass.TIMESTAMP for automatic human-readable relative time formatting in Lovelace.
    """

    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize last update sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ai_last_update"
        self._attr_name = "Garmin AI Last Update"
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> datetime | None:
        """Return the timestamp of the last successful update as a datetime object."""
        val = getattr(self.coordinator, "last_update_time", None)
        if isinstance(val, str):
            # Parse string timestamps if set as string
            try:
                parsed = dt_util.parse_datetime(val)
                if isinstance(parsed, datetime):
                    return parsed
            except Exception:
                pass
            try:
                return datetime.fromisoformat(val)
            except Exception:
                return None
        return val


class GarminAISelectedReportSensor(
    CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity
):
    """Dynamic sensor providing report or answer text according to currently selected display mode.

    The user can switch between 'Short Summary', 'Long Report', and 'Latest Q&A Answer' via
    the select entity, and this sensor immediately reflects that content for dashboard cards.
    """

    _attr_icon = "mdi:text-box-search-outline"

    def __init__(
        self,
        coordinator: GarminDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize dynamic selected report sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_ai_selected_report"
        self._attr_name = "Garmin AI Selected Report"
        self._attr_device_info = get_device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the current display mode name as native state."""
        return self.coordinator.report_display_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return dynamically rendered content matching the selected mode in extra state attributes."""
        mode = self.coordinator.report_display_mode
        report = self.coordinator.latest_report
        answer = self.coordinator.latest_answer

        report_text = ""
        timestamp = None

        # Render corresponding text based on active display mode
        if mode == REPORT_VIEW_SHORT:
            if report and report.short_summary:
                report_text = report.short_summary
                timestamp = report.timestamp
            else:
                report_text = "No report generated yet."
        elif mode == REPORT_VIEW_LONG:
            if report and report.full_report:
                report_text = report.full_report
                timestamp = report.timestamp
            else:
                report_text = "No report generated yet."
        elif mode == REPORT_VIEW_QA:
            if answer and answer.get("answer"):
                q = answer.get("question", "")
                a = answer.get("answer", "")
                report_text = f"**Question:** {q}\n\n**Answer:** {a}"
                timestamp = answer.get("timestamp")
            else:
                report_text = "No question asked yet."
        else:
            report_text = report.short_summary if report else "No report generated yet."

        return {
            "report_text": report_text,
            "display_mode": mode,
            "timestamp": timestamp,
        }




