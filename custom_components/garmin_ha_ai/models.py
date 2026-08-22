"""Data models for Garmin HA AI integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GarminActivity:
    """Class representing an activity recorded on Garmin Connect."""

    activity_id: int | str | None = None
    name: str | None = None
    type: str | None = None
    duration_sec: float | int | None = None
    duration_min: float | None = None
    distance_m: float | None = None
    distance_km: float | None = None
    calories: int | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    aerobic_training_effect: float | None = None
    anaerobic_training_effect: float | None = None
    hr_zones: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert activity to dictionary representation."""
        return asdict(self)


@dataclass
class GarminDailyMetrics:
    """Class representing normalized daily fitness and health metrics from Garmin Connect."""

    date: str
    steps: int | None = None
    distance_km: float | None = None
    total_calories: int | None = None
    resting_hr: int | None = None
    avg_stress: int | None = None
    sleep_score: int | None = None
    hrv_status: str | None = None
    body_battery_min: int | None = None
    body_battery_max: int | None = None
    weight_kg: float | None = None
    activities: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics dataclass to dictionary representation."""
        return asdict(self)


@dataclass
class AIHealthReport:
    """Class representing generated AI health reports and summaries."""

    timestamp: str
    short_summary: str
    full_report: str
    provider_used: str
    model_used: str

    def to_dict(self) -> dict[str, Any]:
        """Convert health report dataclass to dictionary representation."""
        return asdict(self)
