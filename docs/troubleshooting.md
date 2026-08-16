# Troubleshooting Guide — Garmin HA AI

This guide helps diagnose and resolve common issues encountered during setup, authentication, data synchronization, AI generation, and dashboard card usage with **Garmin HA AI**.

---

## 📑 Table of Contents

1. [Garmin Authentication & MFA Issues](#1-garmin-authentication--mfa-issues)
2. [Garmin Connect API Rate Limiting (HTTP 429)](#2-garmin-connect-api-rate-limiting-http-429)
3. [Morning Sleep Score or Metric Shows 'N/A'](#3-morning-sleep-score-or-metric-shows-na)
4. [AI Provider & Generation Errors](#4-ai-provider--generation-errors)
5. [Local AI Endpoints (Ollama / LocalAI / LM Studio)](#5-local-ai-endpoints-ollama--localai--lm-studio)
6. [Notifications Not Arriving on Mobile Devices](#6-notifications-not-arriving-on-mobile-devices)
7. [Custom Lovelace Dashboard Cards Troubleshooting](#7-custom-lovelace-dashboard-cards-troubleshooting)
8. [Multi-Account Garmin Setups](#8-multi-account-garmin-setups)
9. [Viewing Logs & Diagnostics](#9-viewing-logs--diagnostics)

---

## 1. Garmin Authentication & MFA Issues

### Symptom: "Invalid Garmin credentials" or login loop
* **Check Your Password**: Verify your email and password by logging into the official [Garmin Connect Web Portal](https://connect.garmin.com/).
* **Special Characters**: If your password contains unusual unicode symbols, try temporarily updating your password on Garmin Connect to test.
* **Captcha / Account Lock**: If you attempted too many failed logins in a short window, Garmin may temporarily lock your IP address or present a captcha on web. Wait 15–30 minutes or log in via your browser first to clear any prompts.

### Symptom: MFA Code Times Out or Fails
* **120-Second Window**: Garmin MFA codes expire quickly. Ensure you enter the 6-digit code received via email/authenticator app promptly.
* **Re-Authentication Flow**: If your session token expires after several weeks, Home Assistant will create a notification prompting you to re-authenticate. Click **Reconfigure** on the integration card under **Settings → Devices & Services** to refresh tokens without losing historical data.

---

## 2. Garmin Connect API Rate Limiting (HTTP 429)

### Symptom: Log warning `Garmin Connect rate limit (HTTP 429)`
* **Behavior**: Garmin Connect enforces rate limits per IP address when polled too frequently.
* **Built-in Resilience**: The integration **automatically catches HTTP 429 errors**, logs a warning, and gracefully retains your latest cached health metrics without triggering false authentication errors or deleting your valid OAuth tokens.
* **Recommended Polling Interval**: Keep the background polling schedule to once daily (e.g. `06:00:00`) or at intervals >= 6 hours. Avoid setting rapid polling automations.

---

## 3. Morning Sleep Score or Metric Shows 'N/A'

### Symptom: Sleep score is `N/A (Pending sync or watch not worn)` in the early morning
* **Why this happens**: Garmin backend servers calculate detailed sleep stages and sleep scores only after your watch syncs with the Garmin Connect mobile app and the backend completes sleep processing (typically 7:00 AM – 8:30 AM depending on wake time).
* **AI Report Handling**: The integration formats pending sleep data explicitly as *"Pending sync"* so the AI Coach understands sync is pending and does **not** assume zero sleep or penalize your daily recovery briefing.
* **Fix**:
  1. Open your Garmin Connect phone app and ensure your watch finishes syncing.
  2. Adjust your scheduled briefing time in **Options Flow** to 30 minutes after your typical wake-up time (e.g. `07:30:00`).
  3. Tap the **Generate AI Health Report** button on your dashboard to refresh data on demand.

---

## 4. AI Provider & Generation Errors

### Symptom: Google Gemini API quota or model error (404 / 429)
* **Model Selection**: Ensure you are using an active Gemini model (`gemini-2.5-flash` or `gemini-2.5-pro`). Avoid deprecated models (such as `gemini-2.0-flash`).
* **API Key Quota**: Free tier Google AI Studio keys have requests-per-minute (RPM) and requests-per-day (RPD) limits. If exhausted, the integration catches `AIEngineQuotaError` without crashing Home Assistant.

### Symptom: Generic OpenAI / Custom API Client Error (400, 401, 403)
* **API Key Validation**: Double check your API key in **Options Flow**.
* **Model ID**: Make sure the specified model ID exists on your provider's account.

---

## 5. Local AI Endpoints (Ollama / LocalAI / LM Studio)

### Symptom: Cannot connect to local LLM server on LAN without SSL
* **HTTP is Fully Supported**: You do **not** need an SSL certificate (`https://`) for local AI servers. Endpoints like `http://192.168.1.50:11434/v1` or `http://localhost:11434/v1` are fully supported.
* **URL Format**: Make sure to include the full path `/v1` (e.g., `http://192.168.1.100:11434/v1`).
* **Ollama Host Binding**: If Ollama runs on a separate machine or Home Assistant add-on, ensure `OLLAMA_HOST=0.0.0.0` is set so it accepts connections from other devices on your local network.
* **Dummy API Key**: Local servers that do not enforce authentication still require non-empty text in the API Key field in Home Assistant (e.g. enter `ollama` or `local`).

---

## 6. Notifications Not Arriving on Mobile Devices

### Symptom: Morning report generated but no mobile push notification
* **Target Format**: Under **Options Flow → Notification Target Service**, specify valid Home Assistant notification entities, separated by commas:
  ```text
  notify.mobile_app_your_phone, persistent_notification
  ```
* **Verify Service**: Go to **Developer Tools → Services / Actions** and test calling `notify.mobile_app_your_phone` with a sample message to ensure your mobile app is registered.
* **Fault Isolation**: If a notification service fails or is misconfigured, the integration logs a warning and still updates your sensor entities and dashboard cards.

---

## 7. Custom Lovelace Dashboard Cards Troubleshooting

### Symptom: "Custom element doesn't exist: garmin-ha-ai-overview-card"
* **Browser Cache**: After updating or installing the integration, perform a hard refresh in your browser (`Ctrl + Shift + R` or `Cmd + Shift + R`) or clear the Home Assistant Companion App frontend cache (**Settings → Companion App → Debugging → Reset frontend cache**).
* **Card Registration**: The integration automatically serves cards at `/garmin_ha_ai_frontend/garmin-ha-ai-cards.js`. Check **Settings → System → Logs** to verify frontend static paths registered without error.

---

## 8. Multi-Account Garmin Setups

### Symptom: How to ask questions or generate reports for a specific account
* **Targeting Entry ID**: If you have multiple Garmin accounts configured in Home Assistant (e.g., family members), you can pass `entry_id` to service calls:
  ```yaml
  action: garmin_ha_ai.ask_question
  data:
    question: "Should I run today?"
    entry_id: "YOUR_CONFIG_ENTRY_ID"
  ```
  *(You can find your Config Entry ID in **Settings → Devices & Services → Garmin HA AI → Three dots → Integration info**).*

---

## 9. Viewing Logs & Diagnostics

To enable detailed debug logging for `garmin_ha_ai`:

Add the following to your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.garmin_ha_ai: debug
```

Restart Home Assistant, reproduce the issue, and inspect the log output under **Settings → System → Logs**.
