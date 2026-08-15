"""5-Block Prompt Context Assembler for AI Engine."""
from __future__ import annotations

import logging
from typing import Any

from ..models import GarminDailyMetrics

_LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_HISTORY_CHARS = 3000

DEFAULT_USER_GOALS = "Maintain overall health, optimize daily energy, and support balanced recovery."
DEFAULT_COACHING_DIRECTIVES = (
    "Provide evidence-based, actionable, and encouraging health coaching recommendations. "
    "Focus on sleep quality, stress management, and appropriate workout intensity."
)


def _format_metric_val(val: Any, unit: str = "") -> str:
    """Format metric value, returning N/A if None."""
    if val is None:
        return "N/A"
    return f"{val}{unit}"


def format_daily_metrics_block(metrics: GarminDailyMetrics | None) -> str:
    """Format Block 1: Current Day Metrics."""
    if not metrics:
        return "No metrics recorded for today."

    lines = [
        f"- Date: {metrics.date}",
        f"- Steps: {_format_metric_val(metrics.steps)}",
        f"- Distance: {_format_metric_val(metrics.distance_km, ' km')}",
        f"- Total Calories: {_format_metric_val(metrics.total_calories, ' kcal')}",
        f"- Resting Heart Rate: {_format_metric_val(metrics.resting_hr, ' bpm')}",
        f"- Average Stress Level: {_format_metric_val(metrics.avg_stress)}",
        f"- Sleep Score: {_format_metric_val(metrics.sleep_score)}",
        f"- HRV Status: {_format_metric_val(metrics.hrv_status)}",
        f"- Body Battery (Min/Max): {_format_metric_val(metrics.body_battery_min)} / {_format_metric_val(metrics.body_battery_max)}",
        f"- Weight: {_format_metric_val(metrics.weight_kg, ' kg')}",
    ]

    if metrics.activities:
        lines.append("- Logged Activities:")
        for act in metrics.activities:
            act_type = act.get("activity_type", "Activity")
            act_dur = act.get("duration_min", "N/A")
            act_cal = act.get("calories", "N/A")
            lines.append(f"  * {act_type}: {act_dur} min, {act_cal} kcal")
    else:
        lines.append("- Logged Activities: None")

    return "\n".join(lines)


def truncate_history_context(
    history: list[GarminDailyMetrics | dict[str, Any]],
    max_chars: int = DEFAULT_MAX_HISTORY_CHARS,
) -> tuple[str, bool]:
    """Format history list into text and truncate older entries if total length exceeds max_chars.

    Returns a tuple of (formatted_history_text, was_truncated).
    """
    if not history:
        return "No previous 7-day history recorded yet.", False

    formatted_days: list[str] = []
    total_len = 0
    was_truncated = False

    # Take up to recent 7 days
    recent_history = history[-7:] if len(history) > 7 else history
    # Process from newest to oldest for safety truncation
    reversed_history = list(reversed(recent_history))

    for item in reversed_history:
        if isinstance(item, GarminDailyMetrics):
            data = item.to_dict()
        elif isinstance(item, dict):
            data = item
        else:
            continue

        date_str = data.get("date", "Unknown Date")
        steps = _format_metric_val(data.get("steps"))
        sleep = _format_metric_val(data.get("sleep_score"))
        hrv = _format_metric_val(data.get("hrv_status"))
        stress = _format_metric_val(data.get("avg_stress"))
        rhr = _format_metric_val(data.get("resting_hr"))

        day_text = (
            f"[{date_str}] Steps: {steps} | Sleep Score: {sleep} | "
            f"HRV: {hrv} | Stress: {stress} | Resting HR: {rhr}"
        )

        if total_len + len(day_text) + 1 > max_chars:
            was_truncated = True
            _LOGGER.warning(
                "History context exceeded %d chars threshold; truncating older entries",
                max_chars,
            )
            break

        formatted_days.append(day_text)
        total_len += len(day_text) + 1

    # Re-reverse back to chronological order
    chronological = list(reversed(formatted_days))
    return "\n".join(chronological), was_truncated


def assemble_report_prompt(
    current_metrics: GarminDailyMetrics | None,
    history: list[GarminDailyMetrics | dict[str, Any]] | None = None,
    user_goals: str | None = None,
    coaching_directives: str | None = None,
    max_history_chars: int = DEFAULT_MAX_HISTORY_CHARS,
) -> str:
    """Assemble 5-block prompt context payload for AI report generation."""
    # Block 1: Current Day Metrics
    block1_content = format_daily_metrics_block(current_metrics)

    # Block 2: Historical Trends
    history_list = history or []
    block2_content, _ = truncate_history_context(history_list, max_chars=max_history_chars)

    # Block 3: User Goals & Profile
    block3_content = (user_goals or "").strip() or DEFAULT_USER_GOALS

    # Block 4: Persona Directives & Tone
    block4_content = (coaching_directives or "").strip() or DEFAULT_COACHING_DIRECTIVES

    # Block 5: Structural Output Formatting Rules
    block5_content = (
        "IMPORTANT OUTPUT FORMATTING RULES:\n"
        "1. You MUST start your response with a concise 1-2 sentence summary enclosed in <summary>...</summary> tags.\n"
        "   - The summary text inside <summary> MUST NOT exceed 200 characters.\n"
        "   - Example: <summary>Great recovery today with an 85 sleep score! Focus on light cardio and hydration.</summary>\n"
        "2. Following the <summary> block, provide the complete, detailed Daily Health Briefing in Markdown format.\n"
        "3. Structure the detailed briefing with clear section headers:\n"
        "   - ## Summary & Recovery Status\n"
        "   - ## Sleep & Stress Analysis\n"
        "   - ## Activity & Performance\n"
        "   - ## Actionable Recommendations for Tomorrow"
    )

    prompt = (
        "### BLOCK 1: CURRENT DAY METRICS\n"
        f"{block1_content}\n\n"
        "### BLOCK 2: HISTORICAL TRENDS (7-DAY CONTEXT)\n"
        f"{block2_content}\n\n"
        "### BLOCK 3: USER GOALS & PROFILE\n"
        f"{block3_content}\n\n"
        "### BLOCK 4: PERSONA & COACHING DIRECTIVES\n"
        f"{block4_content}\n\n"
        "### BLOCK 5: STRUCTURAL OUTPUT FORMATTING RULES\n"
        f"{block5_content}"
    )

    return prompt


def assemble_qa_prompt(
    question: str,
    history: list[GarminDailyMetrics | dict[str, Any]] | None = None,
    user_goals: str | None = None,
    coaching_directives: str | None = None,
    max_history_chars: int = DEFAULT_MAX_HISTORY_CHARS,
) -> str:
    """Assemble prompt payload for interactive Q&A session."""
    history_list = history or []
    block_history_content, _ = truncate_history_context(
        history_list, max_chars=max_history_chars
    )

    block_goals = (user_goals or "").strip() or DEFAULT_USER_GOALS
    block_directives = (coaching_directives or "").strip() or DEFAULT_COACHING_DIRECTIVES

    prompt = (
        f"### USER QUESTION\n"
        f"{question.strip()}\n\n"
        "### HISTORICAL METRICS CONTEXT\n"
        f"{block_history_content}\n\n"
        "### USER GOALS & PROFILE\n"
        f"{block_goals}\n\n"
        "### PERSONA & COACHING DIRECTIVES\n"
        f"{block_directives}\n\n"
        "### INSTRUCTIONS FOR RESPONSE:\n"
        "1. Provide a clear, evidence-based, concise answer directly addressing the user's question.\n"
        "2. Ground your recommendations using the provided historical health metrics and user goals.\n"
        "3. Keep the tone encouraging, supportive, and actionable."
    )

    return prompt

