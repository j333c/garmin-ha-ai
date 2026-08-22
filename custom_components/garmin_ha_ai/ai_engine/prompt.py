"""5-Block Prompt Context Assembler for AI Engine."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from ..helpers import truncate_entity_state
from ..models import AIHealthReport, GarminDailyMetrics

_LOGGER = logging.getLogger(__name__)

# Maximum character threshold for 7-day historical context to prevent token budget blowup
DEFAULT_MAX_HISTORY_CHARS = 3000

# Default fallbacks if user has not configured custom coaching goals or personas
DEFAULT_USER_GOALS = "Maintain overall health, optimize daily energy, and support balanced recovery."
DEFAULT_COACHING_DIRECTIVES = (
    "Provide evidence-based, actionable, and encouraging health coaching recommendations. "
    "Focus on sleep quality, stress management, and appropriate workout intensity."
)


def sanitize_prompt_input(text: str | None) -> str:
    """Sanitize user-provided prompt strings to prevent delimiter and tag injection.

    Neutralizes markdown heading sequences matching our block delimiters (e.g. '### BLOCK 1')
    and strips <summary> tags to ensure clean parsing of the LLM's output structure.
    """
    if not text:
        return ""
    # Neutralize block delimiter headers that mimic prompt structure
    cleaned = re.sub(
        r"(?i)###\s*(block\s*\d+|user\s*question|historical|instructions|persona|user\s*goals)",
        r"[USER_INPUT: \1]",
        text,
    )
    # Strip output formatting tag spoofing
    cleaned = re.sub(r"(?i)</?summary>", "", cleaned)
    return cleaned.strip()


def _format_metric_val(val: Any, unit: str = "", pending_note: str = "") -> str:
    """Format metric value, returning N/A with optional pending note if None."""
    if val is None:
        return f"N/A ({pending_note})" if pending_note else "N/A"
    return f"{val}{unit}"


def format_daily_metrics_block(metrics: GarminDailyMetrics | None) -> str:
    """Format Block 1: Current Day Metrics.

    Formats today's health indicators and workout list into a bulleted list for LLM context.
    """
    if not metrics:
        return "No metrics recorded for today."

    lines = [
        f"- Date: {metrics.date}",
        f"- Steps: {_format_metric_val(metrics.steps)}",
        f"- Distance: {_format_metric_val(metrics.distance_km, ' km')}",
        f"- Total Calories: {_format_metric_val(metrics.total_calories, ' kcal')}",
        f"- Resting Heart Rate: {_format_metric_val(metrics.resting_hr, ' bpm')}",
        f"- Average Stress Level: {_format_metric_val(metrics.avg_stress)}",
        f"- Sleep Score: {_format_metric_val(metrics.sleep_score, pending_note='Pending sync or watch not worn')}",
        f"- HRV Status: {_format_metric_val(metrics.hrv_status, pending_note='Pending sync or not calculated')}",
        f"- Body Battery (Min/Max): {_format_metric_val(metrics.body_battery_min)} / {_format_metric_val(metrics.body_battery_max)}",
        f"- Weight: {_format_metric_val(metrics.weight_kg, ' kg')}",
    ]

    # Format logged workouts / activities
    if metrics.activities:
        lines.append("- Logged Activities:")
        for act in metrics.activities:
            act_type = act.get("activity_type") or act.get("type") or act.get("name") or "Activity"
            if act.get("duration_min") is not None:
                act_dur = act.get("duration_min")
            elif act.get("duration_sec") is not None:
                act_dur = round(float(act["duration_sec"]) / 60, 1)
            else:
                act_dur = "N/A"
            act_cal = act.get("calories", "N/A")
            lines.append(f"  * {act_type}: {act_dur} min, {act_cal} kcal")
    else:
        lines.append("- Logged Activities: None")

    return "\n".join(lines)


def truncate_history_context(
    history: list[GarminDailyMetrics | dict[str, Any]] | dict[str, Any] | None,
    max_chars: int = DEFAULT_MAX_HISTORY_CHARS,
) -> tuple[str, bool]:
    """Format history list into text and truncate older entries if total length exceeds max_chars.

    Prioritizes the most recent days by traversing newest-to-oldest until max_chars is reached,
    then formats back into chronological order.

    Returns:
        tuple of (formatted_history_text, was_truncated).
    """
    if not history:
        return "No previous 7-day history recorded yet.", False

    # Normalize dict or list representations into a list of daily metric records
    if isinstance(history, dict):
        history_list = [history[k] for k in sorted(history.keys())]
    elif isinstance(history, list):
        history_list = history
    else:
        history_list = []

    if not history_list:
        return "No previous 7-day history recorded yet.", False

    formatted_days: list[str] = []
    total_len = 0
    was_truncated = False

    # Take up to the 7 most recent days
    recent_history = history_list[-7:] if len(history_list) > 7 else history_list
    # Process from newest to oldest for safe backward truncation
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

        # Check if adding this day exceeds our token-budget character bound
        if total_len + len(day_text) + 1 > max_chars:
            was_truncated = True
            _LOGGER.warning(
                "History context exceeded %d chars threshold; truncating older entries",
                max_chars,
            )
            break

        formatted_days.append(day_text)
        total_len += len(day_text) + 1

    # Re-reverse back to chronological order for natural reading
    chronological = list(reversed(formatted_days))
    return "\n".join(chronological), was_truncated


def parse_ai_health_report(
    raw_text: str,
    provider_used: str,
    model_used: str,
    timestamp: str | None = None,
) -> AIHealthReport:
    """Parse raw AI response text into structured AIHealthReport.

    Extracts short summary from <summary> tags, falling back to first line if tags are omitted.
    Ensures short summary is safely clamped within 250 characters.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    match = re.search(r"<summary>(.*?)</summary>", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        short_summary = match.group(1).strip()
    else:
        # Fallback to first non-empty line or sentence if tags were omitted
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        short_summary = lines[0] if lines else "Health report generated."

    # Enforce strict 250-character limit via shared truncate_entity_state helper
    clean_short_summary = truncate_entity_state(short_summary, max_len=250)

    return AIHealthReport(
        timestamp=ts,
        short_summary=clean_short_summary,
        full_report=raw_text.strip(),
        provider_used=provider_used,
        model_used=model_used,
    )


def assemble_report_prompt(
    current_metrics: GarminDailyMetrics | None,
    history: list[GarminDailyMetrics | dict[str, Any]] | None = None,
    user_goals: str | None = None,
    coaching_directives: str | None = None,
    max_history_chars: int = DEFAULT_MAX_HISTORY_CHARS,
) -> str:
    """Assemble 5-block prompt context payload for daily AI report generation.

    Block 1: Current Day Metrics (Steps, HR, Sleep, Stress, HRV, Body Battery, Activities)
    Block 2: Historical Trends (7-day rolling context)
    Block 3: User Goals & Profile (Customizable)
    Block 4: Persona Directives & Tone (Customizable)
    Block 5: Structural Output Formatting Rules (Summary tags and markdown headings)
    """
    # Block 1: Current Day Metrics
    block1_content = format_daily_metrics_block(current_metrics)

    # Block 2: Historical Trends
    history_list = history or []
    block2_content, _ = truncate_history_context(history_list, max_chars=max_history_chars)

    # Block 3: User Goals & Profile (Sanitized)
    sanitized_goals = sanitize_prompt_input(user_goals)
    block3_content = sanitized_goals or DEFAULT_USER_GOALS

    # Block 4: Persona Directives & Tone (Sanitized)
    sanitized_directives = sanitize_prompt_input(coaching_directives)
    block4_content = sanitized_directives or DEFAULT_COACHING_DIRECTIVES

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
        "   - ## Actionable Recommendations for Tomorrow\n"
        "4. If any metrics are marked 'Pending sync', state that synchronization may be in progress rather than assuming zero activity or missing sleep."
    )

    # Assemble into full structured context string
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
    """Assemble prompt payload for interactive Q&A session.

    Grounds user questions in rolling metrics history, personal fitness goals, and coaching directives.
    """
    history_list = history or []
    block_history_content, _ = truncate_history_context(
        history_list, max_chars=max_history_chars
    )

    sanitized_question = sanitize_prompt_input(question)
    sanitized_goals = sanitize_prompt_input(user_goals)
    sanitized_directives = sanitize_prompt_input(coaching_directives)

    block_goals = sanitized_goals or DEFAULT_USER_GOALS
    block_directives = sanitized_directives or DEFAULT_COACHING_DIRECTIVES

    prompt = (
        f"### USER QUESTION\n"
        f"{sanitized_question}\n\n"
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


