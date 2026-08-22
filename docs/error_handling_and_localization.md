# Error Handling Taxonomy, Localization & Dual-Mode Polling

---

## 🛡️ Centralized Exception Taxonomy (`exceptions.py`)

All exceptions raised across Garmin Connect API communication and AI Engine generation are normalized into a strongly typed, hierarchical taxonomy rooted in Home Assistant's `HomeAssistantError`:

```text
GarminAIError (Base HomeAssistantError)
├── GarminError (Base for all Garmin operations)
│   ├── GarminAuthError (Invalid/revoked credentials; triggers reauth flow)
│   ├── GarminMfaRequired (Intercepts 2FA verification challenges)
│   ├── GarminRateLimitError (HTTP 429 rate limit resilience; preserves cache)
│   ├── GarminConnectionError (Network connection timeouts and drops)
│   ├── GarminDataParsingError (Malformed or altered Garmin payload schemas)
│   └── GarminSessionExpiredError (Session token invalidated after inactivity)
└── AIEngineError (Base for all LLM / AI providers)
    ├── AIEngineAuthError (API key authentication failure - 401/403)
    ├── AIEngineQuotaError (Rate limits / credit exhaustion - 429)
    ├── AIEngineTimeoutError (Request exceeded client timeout)
    ├── AIEngineModelNotFoundError (Model ID deprecated or unavailable - 404)
    ├── AIEngineClientError (Non-transient 4xx client errors; fails fast without retries)
    └── AIEngineConnectionError (Cannot reach LLM endpoint / local LAN server down)
```

---

## 🔄 Resilience & Error Handling Strategies

### 1. HTTP 429 Rate Limit Graceful Degradation
* **Problem**: Rapid polling or Garmin cloud rate limiting triggers HTTP 429 responses.
* **Solution**: `GarminRateLimitError` is caught at the coordinator level. The integration logs a structured warning and **retains the most recent cached snapshot**, ensuring sensor values remain available and valid OAuth tokens are **never deleted**.

### 2. Exponential Backoff & Retry Policies
* **Transient AI Failures**: Up to 2 retries with exponential backoff for transient AI timeouts or 5xx server issues.
* **Fail-Fast Client Errors**: If an AI request returns HTTP 400 (Bad Request) or 404 (Model Not Found), the integration raises `AIEngineClientError` / `AIEngineModelNotFoundError` immediately without stalling in futile retry loops.

### 3. Non-Blocking Event Loop Execution
* All Garmin HTTP requests and AI SDK calls run inside Home Assistant executor jobs (`hass.async_add_executor_job`) or native async HTTP clients (`httpx`), guaranteeing that the Home Assistant main thread is **never blocked**.

---

## 🌐 Full UI Localization (English & German)

Every user-facing string across the integration is fully localized:
* **`translations/en.json`** — English (Default)
* **`translations/de.json`** — German (Deutsch)
* **`strings.json`** — Canonical base template for Home Assistant Core localization tools.

### What is Localized:
1. **Config Flow Wizard**: Step titles, instructions, field labels, MFA prompts, and error dialogs.
2. **Options Flow Form**: Goal setting, directives, polling time/mode pickers, model selection dropdowns, and retention sliders.
3. **Entity Names**: Button labels, text input fields, selector options, and sensor names.
4. **Services Description**: Parameter descriptions and examples in Developer Tools.

---

## ⏱️ Dual-Mode Polling Engine

Configure your data synchronization cadence in **Options Flow** to match your preferences:

| Polling Mode | Configuration | Use Case |
| :--- | :--- | :--- |
| **Daily Fixed Time** | Native `TimeSelector` (e.g. `06:00:00`, `07:30:00`) | Perfect for receiving your daily health briefing right after waking up without unnecessary battery or network consumption. |
| **Periodic Interval** | Dropdown interval (`1`, `3`, `6`, `12`, or `24` hours) | Ideal for active athletes who record multiple workouts throughout the day and want up-to-date recovery metrics. |
| **On-Demand Manual** | `button.garmin_ai_generate_report` or action `garmin_ha_ai.generate_report` | Trigger instant data extraction and AI briefing anytime from dashboards or automations. |

