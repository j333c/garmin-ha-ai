"""Sensor platform for Garmin HA AI integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GarminDataUpdateCoordinator
from .models import GarminDailyMetrics

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="steps",
        name="Garmin Steps",
        native_unit_of_measurement="steps",
        icon="mdi:walk",
    ),
    SensorEntityDescription(
        key="resting_hr",
        name="Garmin Resting Heart Rate",
        native_unit_of_measurement="bpm",
        icon="mdi:heart-pulse",
    ),
    SensorEntityDescription(
        key="sleep_score",
        name="Garmin Sleep Score",
        native_unit_of_measurement="%",
        icon="mdi:sleep",
    ),
    SensorEntityDescription(
        key="avg_stress",
        name="Garmin Stress Level",
        icon="mdi:emoticon-neutral-outline",
    ),
    SensorEntityDescription(
        key="weight_kg",
        name="Garmin Weight",
        native_unit_of_measurement="kg",
        icon="mdi:scale-bathroom",
    ),
    SensorEntityDescription(
        key="body_battery_min",
        name="Garmin Body Battery",
        native_unit_of_measurement="%",
        icon="mdi:battery-charging",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Garmin HA AI sensor entities from a config entry."""
    coordinator: GarminDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = [
        GarminSensorEntity(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(GarminAIHealthReportShortSensor(coordinator, entry))
    entities.append(GarminAIHealthReportLongSensor(coordinator, entry))

    async_add_entities(entities)


class GarminSensorEntity(CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity):
    """Representation of a Garmin metric sensor entity."""

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

    @property
    def native_value(self) -> Any:
        """Return native value of the sensor from coordinator data."""
        if not self.coordinator.data:
            return None

        metrics: GarminDailyMetrics = self.coordinator.data
        return getattr(metrics, self.entity_description.key, None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}

        metrics: GarminDailyMetrics = self.coordinator.data

        if self.entity_description.key == "body_battery_min":
            return {
                "body_battery_min": metrics.body_battery_min,
                "body_battery_max": metrics.body_battery_max,
            }

        if self.entity_description.key == "steps":
            return {
                "distance_km": metrics.distance_km,
                "total_calories": metrics.total_calories,
                "activities_count": len(metrics.activities),
            }

        return {}


class GarminAIHealthReportShortSensor(
    CoordinatorEntity[GarminDataUpdateCoordinator], SensorEntity
):
    """Short summary AI Health Report sensor entity with 255-character state protection."""

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

    @property
    def native_value(self) -> str | None:
        """Return truncated short report summary guaranteed to fit within 250 characters."""
        report = self.coordinator.latest_report
        if not report:
            return "No report generated yet"

        summary = (report.short_summary or "").strip()
        if not summary:
            summary = "No summary available"

        # Hard truncation at 250 characters (AD-5: strictly < 255 chars)
        if len(summary) > 250:
            summary = summary[:247] + "..."

        return summary

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
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
    """Full AI Health Report sensor carrying full Markdown in extra attributes."""

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
        """Return full Markdown report in extra state attributes."""
        report = self.coordinator.latest_report
        if not report:
            return {}

        return {
            "full_report": report.full_report,
            "short_summary": report.short_summary,
            "timestamp": report.timestamp,
            "provider_used": report.provider_used,
            "model_used": report.model_used,
        }

