# Garmin HA AI — Home Assistant Integration

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/default)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.1.0-emerald.svg?style=for-the-badge)](https://github.com/j333c/garmin-ha-ai/releases)

A privacy-first, subscription-free **Home Assistant custom integration** that pulls your daily health and performance metrics from **Garmin Connect** and delivers personalized, context-aware AI coaching briefings and interactive health intelligence.

---

## 🌟 Highlights

* **🔄 Automated Metric Sync**: Seamlessly syncs Sleep Score, Body Battery, Stress Level, Resting Heart Rate, HRV, Steps, Weight, and logged workout activities.
* **🧠 Pluggable AI Engine**: Native out-of-the-box support for:
  * **Google Gemini SDK** (e.g., `gemini-2.0-flash`, `gemini-1.5-pro`)
  * **Generic OpenAI / OpenAI-Compatible Endpoints** (e.g., OpenAI `gpt-4o`, Ollama, LocalAI, vLLM, LM Studio, Groq, Mistral).
* **🎯 5-Block Context Assembler**: AI recommendations are strictly grounded in your **rolling local metric history (up to 90 days)**, current recovery state, personalized **fitness goals**, and custom **coaching tone directives**.
* **💬 Interactive AI Health Coach**: Ask ad-hoc coaching questions via Home Assistant service calls (`garmin_ha_ai.ask_question`) or interactive dashboard buttons.
* **📲 Multi-Channel Notifications**: Receive your customized daily morning health briefing via Home Assistant Companion App mobile push notifications and persistent notifications.
* **🔒 Privacy & Local History Grounding**:
  * Passwords are never logged or stored in plain text.
  * OAuth session tokens are safely persisted in Home Assistant `.storage`.
  * AI analysis queries historical data from your local rolling storage (`garmin_ha_ai_history.json`), drastically minimizing cloud requests to Garmin.
* **🛡️ Home Assistant Standards Compliant**:
  * Enforces state character limits (<=250 chars in entity state, full Markdown reports stored in extra state attributes).
  * Full UI config flow, reauth flow, and options flow with English localization.

---

## 📖 Quick Links

* [**Installation Guide**](docs/installation.md) — Detailed HACS and manual installation steps.
* [**First Steps & Configuration**](docs/first_steps.md) — Initial setup, AI provider selection, and dashboard setup.

---

## 🚀 Quick Start

### 1. Installation

#### Via HACS (Recommended)
1. In Home Assistant, open **HACS** → **Integrations** → **Three dots (⋮)** → **Custom repositories**.
2. Add `https://github.com/j333c/garmin-ha-ai` as an **Integration**.
3. Search for **Garmin HA AI**, click **Download**, and restart Home Assistant.

#### Manual Installation
1. Download or clone this repository.
2. Copy `custom_components/garmin_ha_ai` into your Home Assistant `/config/custom_components/` directory.
3. Restart Home Assistant.

### 2. Setup Integration

1. Go to **Settings** → **Devices & Services** → **+ Add Integration**.
2. Search for **Garmin HA AI**.
3. Enter your Garmin credentials, select your AI provider (Gemini / OpenAI), enter your API key, and submit.
   *(If prompted, enter your 6-digit MFA code).*

---

## 📊 Entities

### Sensor Entities

| Entity ID | Name | Unit / Type | Description |
| :--- | :--- | :--- | :--- |
| `sensor.garmin_steps` | Garmin Steps | `steps` | Daily accumulated step count. |
| `sensor.garmin_sleep_score` | Garmin Sleep Score | `%` | Overnight sleep quality score (0–100). |
| `sensor.garmin_body_battery` | Garmin Body Battery | `%` | Current / minimum body battery level (0–100). |
| `sensor.garmin_stress_level` | Garmin Stress Level | - | Average daily stress score (0–100). |
| `sensor.garmin_resting_heart_rate` | Garmin Resting HR | `bpm` | Daily resting heart rate. |
| `sensor.garmin_weight` | Garmin Weight | `kg` | Latest logged body weight. |
| `sensor.garmin_ai_health_report_short` | AI Health Report (Short) | `text` | 1–2 sentence actionable summary for notifications/glance cards. |
| `sensor.garmin_ai_health_report_long` | AI Health Report (Long) | `text` | Status overview with full multi-section Markdown report in attributes. |
| `sensor.garmin_ai_last_answer` | AI Last Answer | `text` | Truncated response to the last interactive Q&A question asked. |
| `sensor.garmin_ai_last_update` | Garmin AI Last Update | `timestamp` | Datetime timestamp of the last successful Garmin sync. |
| `sensor.garmin_ai_selected_report` | AI Selected Report | `text` | Dynamically outputs the full content for whichever view is selected. |

### Text & Select Entities

| Entity ID | Name | Description |
| :--- | :--- | :--- |
| `text.garmin_ai_question` | Garmin AI Question | Direct dashboard text input field for typing questions to the AI Coach. |
| `select.garmin_ai_report_view` | Garmin AI Report View | Dropdown to switch between *Short Summary*, *Long Report*, and *Latest Q&A Answer*. |

### Button Entities

| Entity ID | Name | Description |
| :--- | :--- | :--- |
| `button.garmin_ai_generate_report` | Generate AI Health Report | Triggers on-demand Garmin data extraction and AI briefing generation. |
| `button.garmin_ai_ask_question` | Ask AI Question | Submits the question currently typed in `text.garmin_ai_question` to the AI coach. |

---

## 🛠️ Services

### `garmin_ha_ai.generate_report`
Manually triggers Garmin metric extraction, history update, AI report generation, and notification dispatch.

```yaml
action: garmin_ha_ai.generate_report
```

### `garmin_ha_ai.ask_question`
Asks your personal AI Health Coach a personalized question grounded in your rolling Garmin history.

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `question` | `string` | **Yes** | - | The health, fitness, or workout coaching question to ask. |
| `days_history` | `number` | No | `7` | Days of historical context to provide (1–90). |
| `response_entity` | `entity_id` | No | - | Optional target sensor entity to write the answer into. |

#### Service Call Example:
```yaml
action: garmin_ha_ai.ask_question
data:
  question: "My sleep score was 62 and stress was high yesterday. Should I do today's planned 10k threshold run or switch to easy recovery?"
  days_history: 7
```

---

## 🎨 Lovelace Dashboard Examples

### 1. Interactive Resizable Health Coach & Report Card (Recommended)

Includes interactive question typing, one-click submission, view switcher dropdown, and a **resizable text field** with a draggable bottom-right handle:

```yaml
type: vertical-stack
title: 🤖 Garmin AI Health Coach
cards:
  - type: entities
    entities:
      - entity: text.garmin_ai_question
        name: Coaching Question
      - entity: button.garmin_ai_ask_question
        name: Send Question
      - entity: select.garmin_ai_report_view
        name: Active View
      - entity: button.garmin_ai_generate_report
        name: Refresh Daily Report

  - type: markdown
    title: 📋 Coach Briefing & Responses
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 140px; max-height: 650px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">

      {{ state_attr('sensor.garmin_ai_selected_report', 'report_text') }}

      </div>
```

### 2. Metric Glance Card

```yaml
type: glance
title: 🏃 Garmin Health Overview
entities:
  - entity: sensor.garmin_sleep_score
    name: Sleep
  - entity: sensor.garmin_body_battery
    name: Body Battery
  - entity: sensor.garmin_stress_level
    name: Stress
  - entity: sensor.garmin_resting_heart_rate
    name: Resting HR
  - entity: sensor.garmin_steps
    name: Steps
```

---

## ⚙️ Options & Customization

Click **Configure** on the integration card under **Settings → Devices & Services** to adjust:

* **History Retention**: Set rolling history from 7 to 90 days (default: 30).
* **Fitness Goals**: Provide long-term goals (e.g. *"Running a sub-1:45 half marathon; strength training 2x/week"*).
* **Coaching Directives**: Customize AI coach personality and rules (e.g. *"Focus heavily on recovery; suggest mobility exercises when sleep < 70"*).
* **Notification Targets**: Comma-separated notify targets (e.g. `notify.mobile_app_phone, notify.persistent_notification`).
* **Scheduled Polling Time**: Set daily morning execution time (default: `06:00:00`).
* **AI Provider & Models**: Switch between Gemini and OpenAI, choose model IDs (`gemini-2.0-flash`, `gpt-4o`, etc.), or specify local Base URLs (`http://localhost:11434/v1` for Ollama).

---

## 🔒 Privacy & Security

* **Credential Protection**: Garmin credentials and MFA codes are processed transiently during login to establish an authenticated OAuth token session. Passwords are never saved to disk.
* **Token Isolation**: Session tokens and metric history are stored locally in Home Assistant's protected `.storage` directory.
* **No Unnecessary Cloud Calls**: Daily AI context is generated from your local rolling history store rather than continuously polling Garmin servers.

---

## ❓ Frequently Asked Questions & Troubleshooting

<details>
<summary><strong>How do I handle MFA / Two-Factor Authentication?</strong></summary>

When setting up or re-authenticating, if your Garmin account has MFA enabled, the setup wizard will transition to a 6-digit verification code screen. Enter the code received via email or authenticator app.
</details>

<details>
<summary><strong>Can I use a completely local AI model (Ollama / LocalAI / LM Studio)?</strong></summary>

Yes! In the Options Flow, select `openai` as the provider, specify your model name (e.g., `llama3.3:70b` or `mistral`), enter any dummy API key (e.g. `ollama`), and set **Custom AI Base URL** to your local endpoint (e.g., `http://192.168.1.100:11434/v1`).
</details>

<details>
<summary><strong>What happens if my Garmin session expires?</strong></summary>

Home Assistant will raise a notification and trigger a **Reauth Flow**. Simply click the re-authentication notification, confirm your credentials or MFA code, and session tokens will refresh automatically.
</details>

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
