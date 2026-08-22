# Multi-Account & Multi-Member Profile Support

The **Garmin HA AI** integration natively supports multiple Garmin Connect accounts within a single Home Assistant instance, ensuring complete privacy, storage isolation, and personalized coaching for every household member.

---

## 🔒 Isolation Architecture

### 1. Storage Partitioning
* **Token Isolation**: OAuth credentials and session tokens are saved in isolated storage partitions:  
  `.storage/garmin_ha_ai_tokens_{entry_id}.json`
* **Historical Data Partitioning**: Daily metric histories are stored in dedicated JSON stores:  
  `.storage/garmin_ha_ai_history_{entry_id}.json`
* **Seamless Migration**: Upgrading from single-account installations automatically migrates legacy unpartitioned storage to entry-scoped storage without any loss of historical data.

### 2. Dedicated Device Scope
* Each configured Garmin account generates its own distinct Home Assistant Device (e.g., `Garmin AI (jens@example.com)`).
* All entities (sensors, buttons, texts, selects) are registered under their specific device with unique, collision-proof entity IDs.

### 3. Independent Personas, Goals & Schedules
Each household member customizes their own:
* **Fitness Goals** (e.g. Marathon training vs. Strength & Mobility).
* **Coaching Directives & Tone** (e.g. Tough love vs. Encouraging & recovery-first).
* **Sync Schedules & Polling Modes** (e.g. Jens syncs at 06:00, Sarah syncs at 07:30).
* **Notification Targets** (e.g. `notify.mobile_app_jens` vs. `notify.mobile_app_sarah`).
* **AI Providers & Models** (e.g. Gemini 2.5 Flash vs. Local Ollama `llama3.3:70b`).

---

## 🛠️ Step-by-Step Multi-Account Setup

1. Add your first account via **Settings → Devices & Services → + Add Integration → Garmin HA AI**.
2. To add a second account for a partner or family member:
   * Click **+ Add Integration** again.
   * Search for **Garmin HA AI**.
   * Enter the second person's Garmin credentials and AI preferences.
3. Home Assistant will create two distinct config entries and separate device profiles.

---

## 🎨 Multi-User Lovelace Dashboard Setup

When multiple accounts exist, create dedicated dashboard views for each member using explicit entity IDs in `custom:garmin-ha-ai-card`:

```yaml
# Dashboard View for Member 1 (Jens)
type: custom:garmin-ha-ai-card
title: 🏃 Jens's AI Health Coach
sleep_score_entity: sensor.garmin_sleep_score
body_battery_entity: sensor.garmin_body_battery
stress_entity: sensor.garmin_stress_level
hrv_entity: sensor.garmin_hrv_status
resting_hr_entity: sensor.garmin_resting_heart_rate
steps_entity: sensor.garmin_steps
short_report_entity: sensor.garmin_ai_health_report_short
long_report_entity: sensor.garmin_ai_health_report_long
last_answer_entity: sensor.garmin_ai_last_answer
question_entity: text.garmin_ai_question
ask_button_entity: button.garmin_ai_ask_question
generate_button_entity: button.garmin_ai_generate_report
```

```yaml
# Dashboard View for Member 2 (Sarah)
type: custom:garmin-ha-ai-card
title: 🧘 Sarah's AI Health Coach
sleep_score_entity: sensor.garmin_sleep_score_2
body_battery_entity: sensor.garmin_body_battery_2
stress_entity: sensor.garmin_stress_level_2
hrv_entity: sensor.garmin_hrv_status_2
resting_hr_entity: sensor.garmin_resting_heart_rate_2
steps_entity: sensor.garmin_steps_2
short_report_entity: sensor.garmin_ai_health_report_short_2
long_report_entity: sensor.garmin_ai_health_report_long_2
last_answer_entity: sensor.garmin_ai_last_answer_2
question_entity: text.garmin_ai_question_2
ask_button_entity: button.garmin_ai_ask_question_2
generate_button_entity: button.garmin_ai_generate_report_2
```

---

## ⚡ Targeted Service Calls

When triggering actions programmatically, use `entry_id` to target a specific user:

### Ask a specific member's coach:
```yaml
action: garmin_ha_ai.ask_question
data:
  question: "How was my recovery score compared to yesterday's long run?"
  entry_id: "01J5K9X8..."
```

### Refresh a specific member's report:
```yaml
action: garmin_ha_ai.generate_report
data:
  entry_id: "01J5K9X8..."
```

*(If `entry_id` is omitted, `generate_report` refreshes all configured accounts, while `ask_question` routes to the first active account).*
