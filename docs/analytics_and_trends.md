# 7-Day Trend Analytics & Baseline Engine

The Garmin HA AI integration features a deterministic mathematical analytics engine (`analytics.py`) that computes rolling 7-day baselines, goal deltas, HRV recovery classifications, and workout heart rate zone distributions.

---

## 🎯 Purpose & Why Deterministic Computation Matters

Language models are notoriously prone to arithmetic and trend calculation errors when given raw, unformatted daily logs. Rather than relying on the LLM to calculate moving averages or percentage variances, `analytics.py` executes strict deterministic mathematics in Python and injects pre-calculated baseline facts directly into the prompt context (**Block 2: Pre-Computed Baselines & Trends**).

---

## 📊 Core Analytics Capabilities

### 1. Rolling 7-Day Statistical Baselines
The engine scans the local rolling storage (`garmin_ha_ai_history.json`) for the most recent 7 days of recorded data and computes exact statistical means:
* **7-Day Average Sleep Score** (e.g., `78.4 / 100`)
* **7-Day Average Resting Heart Rate** (e.g., `52 bpm`)
* **7-Day Average Daily Stress Level** (e.g., `28 / 100`)
* **7-Day Average Step Count** (e.g., `11,450 steps/day`)
* **7-Day Average Total Calorie Burn** (e.g., `2,450 kcal/day`)

### 2. Real-Time Baseline & Goal Deltas
Every daily briefing compares today's current metrics against both your 7-day baseline and your configured personal targets:
* **Step Variance**: Today's steps vs. 7-day average (e.g. `+1,250 steps (+10.9%) vs 7-day avg`).
* **Sleep Quality Variance**: Today's sleep score vs. 7-day average and target.
* **Resting Heart Rate Deviation**: Indicates elevated strain, illness, or fatigue when RHR exceeds baseline by > 3-5 bpm.
* **Stress Load Deviation**: Quantifies recovery balance.

### 3. HRV Recovery Classification
The engine evaluates multi-day transitions in Heart Rate Variability (HRV) and assigns standardized qualitative recovery states:
* **`Stable & Balanced`**: HRV is consistently within your baseline range; optimal for high-intensity training.
* **`Improving`**: Upward trend in HRV following rest or reduced training load.
* **`Declining`**: Downward trend indicating accumulating systemic fatigue, poor sleep, or stress.
* **`Consistently Unbalanced`**: Multi-day deviations outside baseline; recommend active recovery or rest.
* **`Low / Poor`**: Significant depression in HRV; strong signal to prioritize rest, hydration, and sleep.

### 4. Rich Activity Ingestion & HR Zone Extraction
When activities are recorded on your Garmin watch, the analytics engine extracts and summarizes:
* **Aerobic & Anaerobic Training Effect** (e.g., `Aerobic: 3.4 (Impactful), Anaerobic: 1.2 (Minor)`).
* **Heart Rate Zones**: Time spent in Zones 1 through 5 (Warm Up, Easy, Aerobic, Threshold, Maximum).
* **Workload Metrics**: Average HR, Max HR, total active duration, distance, and calories.

---

## 🧠 Prompt Grounding Architecture

The analytics output is structured into human-readable and LLM-friendly blocks within `prompt.py`:

```text
[7-DAY BASELINE & TRENDS]
- Rolling 7-Day Averages: Sleep: 81/100, RHR: 51 bpm, Stress: 24/100, Steps: 12,100, Calories: 2,650 kcal
- HRV Trend Status: Stable & Balanced (Optimal recovery)
- Today vs 7-Day Baseline: Steps (+1,400), Sleep (-4 pts), RHR (+2 bpm)
- Recent Activities: 45 min Run (Aerobic TE: 3.2, Avg HR: 148 bpm, Zone 3: 28 min, Zone 4: 12 min)
```

This guarantees that the AI Health Coach provides mathematically accurate advice and personalized training adaptations grounded in true physiological data.
