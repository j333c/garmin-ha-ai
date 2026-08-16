# First Steps & Getting Started — Garmin HA AI

This guide walks you through the initial configuration, goal setting, AI engine customization, and dashboard card setup for **Garmin HA AI**.

---

## Step 1: Add the Integration in Home Assistant

Once the integration is installed and Home Assistant has been restarted:

1. Navigate to **Settings** → **Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **Garmin HA AI** and click on it.

---

## Step 2: Garmin Authentication & MFA

1. Enter your **Garmin Connect Email** and **Password**.
2. Select your **AI Provider** using the radio buttons (`Google Gemini` or `OpenAI (or compatible)`).
3. Enter your **AI API Key**.
4. *(Optional)* Enter your initial **Fitness Goals** (e.g., *"Training for a sub-4:00 marathon in October; 40 km/week running"*).
5. Click **Submit**.

> [!NOTE]
> **Two-Factor Authentication (MFA / 2FA)**:
> If Garmin prompts for a verification code, a second screen will appear asking for your **6-digit MFA code**. Enter the code received via email or authenticator app within 2 minutes to complete login.
>
> **Token Security**: Your raw password is used solely to obtain OAuth session tokens. Tokens are securely persisted in Home Assistant's internal `.storage` folder. Your password is never logged or stored in plain text.

---

## Step 3: Configure Advanced Options & Coaching Preferences

Once added, you can customize polling, AI models, custom endpoints, coaching style, and notifications at any time:

1. Go to **Settings** → **Devices & Services** → **Garmin HA AI**.
2. Click **Configure** on the integration card.

### Available Settings in Options Flow:

| Option | Default | Description |
| :--- | :--- | :--- |
| **History Retention Window (days)** | `30` | Number of days of health metric snapshots to preserve locally (7 to 90 days). |
| **Fitness Goals & Milestones** | *Blank* | Your personal athletic objectives (e.g., *"Half-marathon under 1:45, build aerobic base"*). |
| **Coaching Directives & Tone** | *Blank* | Personality instructions for the AI coach (e.g., *"Be direct and analytical. Prioritize recovery and sleep quality over high mileage."*). |
| **Notification Target Service** | *Blank* | Comma-separated Home Assistant notify services (e.g., `notify.mobile_app_my_phone, notify.persistent_notification`). |
| **Daily Briefing Schedule** | `06:00:00` | Time of day (`HH:MM:SS`) to automatically pull data, generate the daily briefing, and send notifications. |
| **AI Provider** | `Google Gemini` | Radio button selection: `Google Gemini` or `OpenAI (or compatible)`. |
| **AI Model Name** | `gemini-2.5-flash` / `gpt-4o` | Dynamic dropdown populated via API model discovery (e.g., `gemini-2.5-flash`, `gpt-4o`, `gpt-4o-mini`, `llama3.3:70b`, `mistral:latest`), with support for custom typed model names. |
| **Custom AI Base URL** | `https://api.openai.com/v1` | Custom endpoint URL for local/alternative OpenAI-compatible APIs (e.g., `http://192.168.1.100:11434/v1` for Ollama, LocalAI, vLLM). |

---

## Step 4: Test Integration Services

You can test data polling and AI generation manually via **Developer Tools**:

### 1. Generate Daily AI Health Report
1. Go to **Developer Tools** → **Services** (or **Actions** in newer HA versions).
2. Select **`garmin_ha_ai.generate_report`**.
3. Click **Perform Action**.
4. Check `sensor.garmin_ai_health_report_short` and `sensor.garmin_ai_health_report_long` to view the generated recommendations.

### 2. Ask the AI Health Coach a Question
1. Select **`garmin_ha_ai.ask_question`**.
2. Enter a question:
   ```yaml
   action: garmin_ha_ai.ask_question
   data:
     question: "Based on my last 7 days of sleep and workouts, should I do high-intensity intervals today?"
     days_history: 7
   ```
3. View the response in the service response data or check `sensor.garmin_ai_last_answer`.

---

## Step 5: Add Lovelace Dashboard Cards

The integration provides ready-to-use entities for a complete 3-tier health dashboard (Fast Health Glance, Instant Q&A Coach, and Deep Insight Report).

> 💡 For complete full-dashboard presets for both modern **Sections** and **Classic** views, see the [**Lovelace Dashboard Guide**](dashboard_cards.md).

### Quick-Start Lovelace YAML Stack

```yaml
type: vertical-stack
title: 🤖 Garmin AI Health Coach
cards:
  # Tier 1: Fast Status Glance
  - type: glance
    entities:
      - entity: sensor.garmin_sleep_score
        name: Sleep
      - entity: sensor.garmin_body_battery
        name: Battery
      - entity: sensor.garmin_stress_level
        name: Stress
      - entity: sensor.garmin_resting_heart_rate
        name: Resting HR
      - entity: sensor.garmin_steps
        name: Steps

  - type: markdown
    content: >
      💡 **Today's Focus:** {{ states('sensor.garmin_ai_health_report_short') }}

  # Tier 2: Instant Q&A Coach (Zero Helper Setup)
  - type: entities
    show_header_toggle: false
    entities:
      - entity: text.garmin_ai_question
        name: Ask Coach
      - entity: button.garmin_ai_ask_question
        name: Submit Question

  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 100px; max-height: 350px; padding: 10px; border: 1px solid var(--divider-color); border-radius: 8px;">
      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Type a question above and tap "Submit Question".*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}
      {% endif %}
      </div>

  # Tier 3: Deep Insight View (Long AI Report)
  - type: entities
    entities:
      - entity: button.garmin_ai_generate_report
        name: Refresh Daily Report

  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 180px; max-height: 600px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">
      {{ state_attr('sensor.garmin_ai_health_report_long', 'full_report') }}
      </div>
```

---

## Step 6: Automated Daily Notifications

To receive your AI health briefing automatically on your phone every morning, configure your mobile app notification target in the Options Flow (e.g. `notify.mobile_app_jens_phone`) and set your preferred briefing time (e.g., `06:30:00`).

Alternatively, create an automation triggered by waking up or turning off an alarm:

```yaml
alias: "Garmin AI Morning Health Briefing"
trigger:
  - platform: time
    at: "06:30:00"
action:
  - action: garmin_ha_ai.generate_report
```

---

## Need Help or Found an Issue?

* [Installation Guide](installation.md)
* [Lovelace Dashboard Guide](dashboard_cards.md)
* [Troubleshooting Guide](troubleshooting.md)
* [Frequently Asked Questions (FAQ)](faq.md)
* [GitHub Issues](https://github.com/j333c/garmin-ha-ai/issues)

---

> [!NOTE]
> **AI & BMAD Method Disclaimer**: This integration was created fully through AI utilizing the [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) and builds upon open-source foundations including [Home Assistant](https://www.home-assistant.io/), [python-garminconnect](https://github.com/cyberjunky/python-garminconnect), [Google GenAI SDK](https://github.com/googleapis/python-genai), and [HTTPX](https://www.python-httpx.org/).

