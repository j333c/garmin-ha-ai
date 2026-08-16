# Installation Guide — Garmin HA AI

This guide walks you through installing the **Garmin HA AI** integration on your Home Assistant instance.

---

## Prerequisites

Before installing, ensure you have:

1. **Home Assistant**: Version `2024.1.0` or newer (Home Assistant OS, Supervised, Container, or Core).
2. **Garmin Connect Account**: Active Garmin credentials (email and password).
   * *Note: If Two-Factor Authentication (MFA) is enabled on your Garmin account, have your email/authenticator app ready during setup.*
3. **AI Engine Provider**:
   * **Google Gemini**: A free or paid API key from [Google AI Studio](https://aistudio.google.com/). *(Recommended: `gemini-2.0-flash`)*
   * **OpenAI or OpenAI-Compatible Endpoint**: An API key from [OpenAI](https://platform.openai.com/) or a local OpenAI-compatible endpoint (e.g., Ollama, LocalAI, vLLM, LM Studio, Groq).

---

## Installation Methods

### Method 1: Via HACS (Recommended)

If you use **HACS (Home Assistant Community Store)**:

1. Open **Home Assistant** and navigate to **HACS** in the left sidebar.
2. Click the **three dots (⋮)** in the top right corner and select **Custom repositories**.
3. In the dialog:
   * **Repository**: `https://github.com/j333c/garmin-ha-ai`
   * **Type**: `Integration`
4. Click **Add**.
5. Find **Garmin HA AI** in the HACS integrations list and click **Download**.
6. Select the latest release and confirm the download.
7. **Restart Home Assistant**:
   * Navigate to **Settings** → **System** → Click the **Power icon** (top right) → **Restart Home Assistant**.

---

### Method 2: Manual Installation

If you do not use HACS or prefer manual installation:

1. **Download the Release**:
   * Download the latest release `.zip` archive or clone the repository from GitHub:
     ```bash
     git clone https://github.com/j333c/garmin-ha-ai.git
     ```

2. **Locate your `custom_components` directory**:
   * On Home Assistant OS / Supervised: `/config/custom_components/`
   * On Home Assistant Core / Container: `<config-directory>/custom_components/`
   * *(If the `custom_components` directory does not exist, create it).*

3. **Copy the Integration Files**:
   * Copy the folder `custom_components/garmin_ha_ai` into your Home Assistant `/config/custom_components/` directory.
   * The final directory structure should look like this:
     ```text
     /config/
     └── custom_components/
         └── garmin_ha_ai/
             ├── __init__.py
             ├── manifest.json
             ├── const.py
             ├── coordinator.py
             ├── config_flow.py
             ├── options_flow.py
             ├── garmin_client.py
             ├── storage.py
             ├── sensor.py
             ├── services.py
             ├── services.yaml
             ├── models.py
             ├── ai_engine/
             │   ├── __init__.py
             │   ├── base.py
             │   ├── gemini.py
             │   ├── openai.py
             │   └── prompt.py
             └── translations/
                 └── en.json
     ```

4. **Restart Home Assistant**:
   * Navigate to **Settings** → **System** → **Restart Home Assistant**.

---

## Verifying the Installation

## Next Steps & Documentation

* [First Steps & Getting Started](first_steps.md) — Initial configuration, goal setting, and provider options.
* [Lovelace Dashboard Guide](dashboard_cards.md) — Card picker, overview cards, and Lovelace YAML examples.
* [Troubleshooting Guide](troubleshooting.md) — Solutions for MFA, 429 rate limits, local AI setups, and logs.
* [Frequently Asked Questions (FAQ)](faq.md) — Architecture, privacy, supported models, and common questions.

---

> [!NOTE]
> **AI & BMAD Method Disclaimer**: This integration was created fully through AI utilizing the [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) and builds upon open-source foundations including [Home Assistant](https://www.home-assistant.io/), [python-garminconnect](https://github.com/cyberjunky/python-garminconnect), [Google GenAI SDK](https://github.com/googleapis/python-genai), and [HTTPX](https://www.python-httpx.org/).

