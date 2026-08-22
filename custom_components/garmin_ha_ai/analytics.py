"""Analytics engine for computing 7-day statistical baselines and trend deltas."""
from __future__ import annotations

import logging
from typing import Any

from .models import GarminDailyMetrics

LOGGER = logging.getLogger(__name__)

# Default user goal values if not specified in configuration
DEFAULT_STEP_GOAL = 10000
DEFAULT_SLEEP_TARGET = 80


def _safe_float(val: Any) -> float | None:
    """Safely convert value to float or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val: Any) -> int | None:
    """Safely convert value to int or return None."""
    if val is None:
        return None
    try:
        return int(round(float(val)))
    except (ValueError, TypeError):
        return None


def calculate_baseline_analytics(
    current_metrics: GarminDailyMetrics | dict[str, Any] | None,
    history: list[GarminDailyMetrics | dict[str, Any]] | dict[str, Any] | None = None,
    step_goal: int | None = None,
    sleep_target: int | None = None,
) -> dict[str, Any]:
    """Calculate 7-day rolling statistics, baseline averages, and trend deltas.

    Returns a structured dictionary containing:
    - 7-day averages (mean_steps, mean_sleep_score, mean_resting_hr, mean_avg_stress, mean_calories)
    - Deltas against current day (e.g. step_delta_vs_avg, sleep_delta_vs_avg, rhr_delta_vs_avg)
    - Goal variance (e.g. step_delta_vs_goal, sleep_delta_vs_target)
    - HRV trend classification ('improving', 'stable', 'declining', 'unbalanced', 'unknown')
    - Total weekly workout count and total activity duration
    """
    effective_step_goal = step_goal or DEFAULT_STEP_GOAL
    effective_sleep_target = sleep_target or DEFAULT_SLEEP_TARGET

    # Normalize current metrics
    curr_dict: dict[str, Any] = {}
    if isinstance(current_metrics, GarminDailyMetrics):
        curr_dict = current_metrics.to_dict()
    elif isinstance(current_metrics, dict):
        curr_dict = current_metrics

    # Normalize history to a list of dicts
    history_list: list[dict[str, Any]] = []
    if isinstance(history, dict):
        for k in sorted(history.keys()):
            item = history[k]
            if isinstance(item, GarminDailyMetrics):
                history_list.append(item.to_dict())
            elif isinstance(item, dict):
                history_list.append(item)
    elif isinstance(history, list):
        for item in history:
            if isinstance(item, GarminDailyMetrics):
                history_list.append(item.to_dict())
            elif isinstance(item, dict):
                history_list.append(item)

    # Consider up to the last 7 recorded days for baseline calculations
    recent_7_days = history_list[-7:] if len(history_list) > 7 else list(history_list)

    # Collect valid numeric samples across historical days
    sleep_scores: list[int] = []
    resting_hrs: list[int] = []
    stress_levels: list[int] = []
    daily_steps: list[int] = []
    total_cals: list[int] = []
    hrv_statuses: list[str] = []
    total_activity_count = 0
    total_activity_duration_min = 0.0

    for day in recent_7_days:
        s = _safe_int(day.get("sleep_score"))
        if s is not None and s > 0:
            sleep_scores.append(s)

        rhr = _safe_int(day.get("resting_hr"))
        if rhr is not None and rhr > 0:
            resting_hrs.append(rhr)

        stress = _safe_int(day.get("avg_stress"))
        if stress is not None and stress >= 0:
            stress_levels.append(stress)

        st = _safe_int(day.get("steps"))
        if st is not None and st >= 0:
            daily_steps.append(st)

        cal = _safe_int(day.get("total_calories"))
        if cal is not None and cal > 0:
            total_cals.append(cal)

        hrv = day.get("hrv_status")
        if isinstance(hrv, str) and hrv.strip():
            hrv_statuses.append(hrv.strip().upper())

        acts = day.get("activities", [])
        if isinstance(acts, list):
            total_activity_count += len(acts)
            for act in acts:
                if isinstance(act, dict):
                    dur_min = act.get("duration_min")
                    if dur_min is not None:
                        total_activity_duration_min += float(dur_min)
                    elif act.get("duration_sec") is not None:
                        total_activity_duration_min += float(act["duration_sec"]) / 60.0

    # Compute baseline means
    mean_sleep = round(sum(sleep_scores) / len(sleep_scores), 1) if sleep_scores else None
    mean_rhr = round(sum(resting_hrs) / len(resting_hrs), 1) if resting_hrs else None
    mean_stress = round(sum(stress_levels) / len(stress_levels), 1) if stress_levels else None
    mean_steps = round(sum(daily_steps) / len(daily_steps)) if daily_steps else None
    mean_cals = round(sum(total_cals) / len(total_cals)) if total_cals else None

    # Current day metrics
    curr_steps = _safe_int(curr_dict.get("steps"))
    curr_sleep = _safe_int(curr_dict.get("sleep_score"))
    curr_rhr = _safe_int(curr_dict.get("resting_hr"))
    curr_stress = _safe_int(curr_dict.get("avg_stress"))
    curr_hrv = str(curr_dict.get("hrv_status") or "").strip().upper() or None

    # Current vs 7-day Baseline Deltas
    step_delta_vs_avg = (curr_steps - mean_steps) if (curr_steps is not None and mean_steps is not None) else None
    sleep_delta_vs_avg = (curr_sleep - mean_sleep) if (curr_sleep is not None and mean_sleep is not None) else None
    rhr_delta_vs_avg = (curr_rhr - mean_rhr) if (curr_rhr is not None and mean_rhr is not None) else None
    stress_delta_vs_avg = (curr_stress - mean_stress) if (curr_stress is not None and mean_stress is not None) else None

    # Goal Deltas
    step_delta_vs_goal = (curr_steps - effective_step_goal) if curr_steps is not None else None
    sleep_delta_vs_target = (curr_sleep - effective_sleep_target) if curr_sleep is not None else None

    # HRV Trend Classification
    hrv_trend = _classify_hrv_trend(curr_hrv, hrv_statuses)

    return {
        "days_analyzed": len(recent_7_days),
        "mean_sleep_score": mean_sleep,
        "mean_resting_hr": mean_rhr,
        "mean_avg_stress": mean_stress,
        "mean_steps": mean_steps,
        "mean_total_calories": mean_cals,
        "step_delta_vs_avg": step_delta_vs_avg,
        "sleep_delta_vs_avg": round(sleep_delta_vs_avg, 1) if sleep_delta_vs_avg is not None else None,
        "rhr_delta_vs_avg": round(rhr_delta_vs_avg, 1) if rhr_delta_vs_avg is not None else None,
        "stress_delta_vs_avg": round(stress_delta_vs_avg, 1) if stress_delta_vs_avg is not None else None,
        "step_delta_vs_goal": step_delta_vs_goal,
        "sleep_delta_vs_target": sleep_delta_vs_target,
        "hrv_trend": hrv_trend,
        "total_weekly_activities": total_activity_count,
        "total_weekly_duration_min": round(total_activity_duration_min, 1),
    }


def _classify_hrv_trend(current_hrv: str | None, history_hrv: list[str]) -> str:
    """Classify 7-day HRV trend pattern into intuitive states."""
    if not current_hrv and not history_hrv:
        return "Unknown (No HRV data recorded)"

    all_statuses = list(history_hrv)
    if current_hrv and (not all_statuses or all_statuses[-1] != current_hrv):
        all_statuses.append(current_hrv)

    if not all_statuses:
        return "Unknown"

    latest = all_statuses[-1]
    if latest in ("BALANCED", "OPTIMAL", "GOOD"):
        if any(h in ("UNBALANCED", "LOW", "POOR") for h in all_statuses[:-1]):
            return "Improving (Recovering from unbalanced/low period to balanced)"
        return "Stable & Balanced (Consistent baseline recovery)"

    if latest in ("UNBALANCED", "POOR"):
        if any(h in ("BALANCED", "OPTIMAL") for h in all_statuses[:-1]):
            return "Declining (Shifted from balanced to unbalanced recovery)"
        return "Consistently Unbalanced (Accumulated strain or incomplete recovery)"

    if latest == "LOW":
        return "Low (Subdued autonomic recovery)"

    return f"Status: {latest}"


def format_baseline_analytics_block(analytics: dict[str, Any]) -> str:
    """Format calculated analytics into concise, factual bullet lines for LLM context."""
    if not analytics or analytics.get("days_analyzed", 0) == 0:
        return "No sufficient 7-day history available to compute statistical baselines."

    days = analytics.get("days_analyzed", 0)
    mean_sleep = analytics.get("mean_sleep_score")
    sleep_delta = analytics.get("sleep_delta_vs_avg")
    mean_rhr = analytics.get("mean_resting_hr")
    rhr_delta = analytics.get("rhr_delta_vs_avg")
    mean_stress = analytics.get("mean_avg_stress")
    stress_delta = analytics.get("stress_delta_vs_avg")
    mean_steps = analytics.get("mean_steps")
    step_delta = analytics.get("step_delta_vs_avg")
    step_goal_delta = analytics.get("step_delta_vs_goal")
    hrv_trend = analytics.get("hrv_trend", "Unknown")
    acts_count = analytics.get("total_weekly_activities", 0)
    acts_dur = analytics.get("total_weekly_duration_min", 0.0)

    def _sign_fmt(val: int | float | None, unit: str = "") -> str:
        if val is None:
            return "N/A"
        prefix = "+" if val > 0 else ""
        return f"{prefix}{val}{unit}"

    lines = [
        f"- Statistical Rolling Window: Past {days} days recorded",
        f"- Sleep Score Baseline: 7-day Avg = {mean_sleep if mean_sleep is not None else 'N/A'} (Today vs Avg: {_sign_fmt(sleep_delta, ' pts')})",
        f"- Resting Heart Rate Baseline: 7-day Avg = {mean_rhr if mean_rhr is not None else 'N/A'} bpm (Today vs Avg: {_sign_fmt(rhr_delta, ' bpm')})",
        f"- Stress Baseline: 7-day Avg = {mean_stress if mean_stress is not None else 'N/A'} (Today vs Avg: {_sign_fmt(stress_delta, ' pts')})",
        f"- Steps Baseline: 7-day Avg = {mean_steps if mean_steps is not None else 'N/A'} (Today vs Avg: {_sign_fmt(step_delta, ' steps')}, Today vs Goal: {_sign_fmt(step_goal_delta, ' steps')})",
        f"- HRV Trend Classification: {hrv_trend}",
        f"- 7-Day Training Volume: {acts_count} activities ({acts_dur} min total logged workout time)",
    ]

    return "\n".join(lines)
