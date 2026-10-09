# Dashboard Usability & Lovelace Cards Guide

## Overview

The `garmin-ha-ai` Lovelace frontend suite provides glanceable, touch-friendly, and responsive cards designed for Home Assistant desktop and mobile companion apps. This guide covers usability best practices, metric visibility, and card customization.

---

## Metric Visibility & Auto-Discovery

The cards dynamically discover entities belonging to your Garmin integration entry:

| Metric | Entity ID Pattern | Visual Representation | Status Thresholds |
| :--- | :--- | :--- | :--- |
| **Weight** | `sensor.*weight*` | Compact Metric Pill with kg display | Tracked against goals |
| **Sleep Score** | `sensor.*sleep*` | Circular Progress Gauge & Metric Pill | Optimal: >=80 (Emerald) <br> Moderate: 60-79 (Amber) <br> Poor: <60 (Coral) |
| **Body Battery** | `sensor.*body_battery*` | Circular Progress Gauge & Pill | Optimal: >=75 <br> Moderate: 40-74 <br> Low: <40 |
| **HRV Status** | `sensor.*hrv*` | Circular Status Gauge | Balanced (Emerald), Low/Poor (Coral) |
| **Steps** | `sensor.*steps*` | Metric Pill with daily step total | Dynamic progress toward goal |
| **Heart Rate** | `sensor.*resting_hr*` | Metric Pill with current resting HR | Resting HR baseline indicator |

### Graceful Pending Sync States

In earlier versions, unpolled or morning-pending metrics would show a stark `--` or error state. The updated usability architecture features:
* **Pending Indicator:** When morning data is still synchronizing from Garmin servers, entities display a subtle pulse indicator (`⏳ Syncing...`) rather than blank or zero values.
* **Fallback History Carryover:** If today's scale measurement hasn't occurred yet, the weight pill seamlessly displays your last known recorded weight with a subtle `(latest)` tag.

---

## Card Overview

### 1. `custom:garmin-ha-ai-card` (Packaged All-in-One Card)

The premier dashboard card combining biometrics, AI coaching briefing, and an interactive Q&A conversational drawer into a single unified component.

#### Lovelace YAML Configuration

```yaml
type: custom:garmin-ha-ai-card
title: "Garmin AI Coach"
weight_entity: sensor.garmin_weight
battery_entity: sensor.garmin_body_battery
sleep_entity: sensor.garmin_sleep_score
hrv_entity: sensor.garmin_hrv_status
report_entity: sensor.garmin_ai_health_report_short
full_report_entity: sensor.garmin_ai_health_report_long
qa_answer_entity: sensor.garmin_ai_last_answer
show_gauges: true
show_weight: true
show_qa_drawer: true
```

#### Usability Features:
* **Single-Tap Report Expansion:** Toggle seamlessly between the concise 2-sentence executive summary and full markdown coaching recommendations.
* **Slide-Out Q&A Drawer:** Tap the chat bubble or "Ask Coach" button to slide open a lightweight chat panel without navigating away from your primary dashboard.
* **One-Click Refresh:** Tap the top-right refresh icon to trigger a manual Garmin cloud sync and regenerate AI advice immediately.

---

### 2. `custom:garmin-ha-ai-overview-card` (Quick Glance Biometrics Bar)

A compact, horizontally scrollable metric bar designed specifically for mobile views and dashboard headers.

#### Lovelace YAML Configuration

```yaml
type: custom:garmin-ha-ai-overview-card
title: "Today's Biometrics"
show_steps: true
show_hr: true
show_sleep: true
show_stress: true
show_battery: true
show_weight: true
```

#### Usability Layout:
```
┌────────────────────────────────────────────────────────────────────────┐
│  👟 Steps    ❤️ RHR    😴 Sleep    🔋 Battery    ⚖️ Weight   ⚡ Stress │
│   9,420      48 bpm     88%          92%         74.2 kg       16      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Mobile Usability & Ergonomics

1. **Thumb-Zone Navigation:** Interactive inputs (Ask Coach submit, view toggles) are positioned in the lower two-thirds of cards for effortless one-handed smartphone use.
2. **Dynamic Color Adaptation:** All gauge strokes and text colors bind directly to Home Assistant theme variables (`--primary-text-color`, `--card-background-color`, `--ha-card-border-radius`), ensuring high-contrast legibility in both Dark and Light themes.
3. **Touch Targets:** All clickable icons and buttons adhere to a minimum 44x44px touch target floor to prevent mis-taps.
