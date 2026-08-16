# Frequently Asked Questions (FAQ) — Garmin HA AI

---

## 📌 General Questions

### What makes Garmin HA AI different from other Garmin integrations?
Most integrations simply dump raw metric sensors into Home Assistant. **Garmin HA AI** adds an intelligent **5-Block AI Context Assembler** that grounds a personalized AI Health Coach in your **rolling 7- to 90-day local history**, personal **fitness targets**, and custom **coaching directives**. It synthesizes sleep, stress, HRV, body battery, and workout loads into clear, daily morning briefings and answers ad-hoc questions interactively.

### Does this require a paid subscription?
No! There are **no subscriptions, cloud relays, or SaaS middlemen**. You can use:
* **Google Gemini** with a free API key from Google AI Studio.
* **Local LLMs** (Ollama, LM Studio, LocalAI, vLLM) on your local hardware completely free.
* **OpenAI / Groq / Mistral / Anthropic (via proxy)** with your own pay-per-use API key.

### Is my Garmin password stored securely?
Yes. Your password is only used in memory during setup or re-authentication to obtain Garmin OAuth session tokens. Tokens are securely persisted in Home Assistant's local `.storage` directory. Plaintext passwords are **never** written to disk.

---

## 🤖 AI Models & Customization

### Which AI model is recommended?
* **Google Gemini**: `gemini-2.5-flash` is the recommended default — it is extremely fast, highly capable, and offers generous free-tier limits on Google AI Studio.
* **OpenAI**: `gpt-4o-mini` or `gpt-4o` for sharp reasoning.
* **Local Models**: `llama3.3:70b` (if hardware allows) or `mistral:latest` / `qwen2.5:14b` via Ollama provide private, on-premise coaching.

### How do I configure local AI models (Ollama, LocalAI, LM Studio)?
1. Under **Settings → Devices & Services → Garmin HA AI → Configure**:
2. Select **OpenAI (or compatible)** as the provider.
3. Enter your model name (e.g. `llama3.3:70b`, `mistral:latest`).
4. Enter any non-empty placeholder string in **API Key** (e.g. `ollama`).
5. Set **Custom AI Base URL** to your local LAN endpoint (e.g. `http://192.168.1.100:11434/v1` or `http://localhost:11434/v1`).
6. *Note: Plain HTTP is fully supported — no SSL certificate is needed for local LAN endpoints.*

### Can I adjust the AI coach's personality?
Yes! In **Options Flow**, enter custom **Coaching Directives & Tone**. For example:
* *"Be encouraging, concise, and prioritize longevity and injury prevention."*
* *"Act as a strict Ironman triathlon coach. Focus on heart rate zones, tempo pace, and carb recovery."*

---

## 📈 Health Metrics & Sensors

### Which Garmin metrics are extracted?
* **Sleep Score** (0–100) & overnight sleep quality
* **Body Battery** (Min & Max / current charge)
* **Average Stress Level** (0–100)
* **Resting Heart Rate** (bpm)
* **HRV Status** (Balanced, Unbalanced, Low, Poor)
* **Daily Steps & Distance** (km)
* **Total Calories & Active Calories** (kcal)
* **Weight** (kg)
* **Logged Activities & Workouts** (Type, duration, calories burned)

### Why is the short report sensor truncated?
Home Assistant strictly enforces a **255-character hard limit** on all entity state values. `sensor.garmin_ai_health_report_short` is safely capped under 250 characters for clean glance cards and mobile notifications. The complete, detailed multi-section Markdown report is preserved in full within `extra_state_attributes["full_report"]` on `sensor.garmin_ai_health_report_long`.

---

## 📲 Notifications & Automations

### How do I receive morning briefings on my phone?
Under **Options Flow**, add your mobile companion app entity to **Notification Target Service** (e.g. `notify.mobile_app_phone`). The integration will automatically dispatch your briefing at your configured daily schedule time.

### Can I trigger briefings from a Home Assistant automation?
Yes! Call the `garmin_ha_ai.generate_report` action at any time in an automation or script (e.g., when your bedroom morning motion sensor triggers or when your morning alarm turns off).

---

## 🎨 Lovelace Cards

### Where do I find the dashboard cards?
The integration automatically registers custom cards in Home Assistant's card picker:
1. Open your Lovelace dashboard.
2. Click **Add Card** (bottom right).
3. Search for **Garmin AI** to find the **Overview Card**, **Q&A Coach Card**, and **Report Card**.
4. See the [**Lovelace Dashboard Guide**](dashboard_cards.md) for full YAML and layout options.
