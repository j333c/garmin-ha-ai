# 7-Day Trend Analytics & Baseline Engine

The Garmin HA AI integration features a deterministic mathematical analytics engine (`analytics.py`) that computes rolling 7-day baselines, goal deltas, and activity heart rate intensities.

## Features

- **7-Day Statistical Means**: Calculates rolling average sleep score, resting heart rate, average stress score, daily step count, and total calorie burn.
- **Trend Deltas**: Computes exact numeric deltas comparing today's metrics against 7-day baseline averages and configured user goals (e.g., `+1200 steps vs avg`, `+5 pts vs sleep target`).
- **HRV Trend Classification**: Synthesizes daily HRV status transitions into qualitative recovery stages (`Stable & Balanced`, `Improving`, `Declining`, `Consistently Unbalanced`, `Low`).
- **Rich Activity Ingestion**: Captures aerobic and anaerobic training effect, average HR, maximum HR, distance, calories, and time-in-zones.
- **Deterministic Context Injection**: Pre-computes these mathematical facts and injects them directly into Block 2 of the AI coaching prompt, eliminating LLM arithmetic hallucination.
