# Interactive Lovelace Q&A Card Pattern

This document describes how to set up an interactive AI Health Coach Q&A interface on your Home Assistant Lovelace dashboard using the `garmin-ha-ai` integration.

---

## 🏗️ Architecture: Zero-Helper Setup

The interactive Q&A feature works directly with native entities provided by `garmin-ha-ai`, eliminating the need to create manual Home Assistant helpers (`input_text`, scripts, etc.):

1. **Question Input**: `text.garmin_ai_question` (native text entity for typing queries).
2. **Action Trigger**: `button.garmin_ai_ask_question` (submits the typed question to your configured AI provider).
3. **Response Display**: `sensor.garmin_ai_last_answer` (attributes `full_answer`, `question`, and `timestamp`).

---

## 📋 Recommended Dashboard Configurations

### Pattern 1: Streamlined Q&A Card (All-in-One)

This card gives you a clean input field, submit button, and a resizable Markdown response box:

```yaml
type: vertical-stack
title: 💬 Ask Garmin AI Coach
cards:
  - type: entities
    show_header_toggle: false
    entities:
      - entity: text.garmin_ai_question
        name: Coaching Question
      - entity: button.garmin_ai_ask_question
        name: Ask Coach

  - type: markdown
    title: 💡 Coach Response
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 120px; max-height: 500px; padding: 12px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px;">

      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Type a question above and tap "Ask Coach" to receive insights grounded in your 30-day Garmin metrics.*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        ---

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}

        <br>
        <small style="color: var(--secondary-text-color);">*Answered: {{ state_attr('sensor.garmin_ai_last_answer', 'timestamp') }}*</small>
      {% endif %}

      </div>
```

---

### Pattern 2: Quick-Prompt Action Buttons

For one-tap convenience, you can create pre-configured question buttons that invoke `garmin_ha_ai.ask_question` with specific queries:

```yaml
type: vertical-stack
title: ⚡ Quick Coach Check-Ins
cards:
  - type: horizontal-stack
    cards:
      - type: button
        name: Ready for Hard Run?
        icon: mdi:run-fast
        tap_action:
          action: call-service
          service: garmin_ha_ai.ask_question
          service_data:
            question: "Based on my sleep score, HRV, and yesterday's activity, is my body ready for a high-intensity interval workout today?"
            days_history: 7

      - type: button
        name: Analyze Sleep Trends
        icon: mdi:sleep
        tap_action:
          action: call-service
          service: garmin_ha_ai.ask_question
          service_data:
            question: "Analyze my sleep score and resting heart rate trends over the past 7 days and highlight any recovery concerns."
            days_history: 7

  - type: markdown
    title: 💡 Answer
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 120px; max-height: 450px; padding: 12px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px;">

      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Tap one of the quick check-in buttons above.*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        ---

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}
      {% endif %}

      </div>
```

---

### Pattern 3: Automations & Developer Tools Service Calls

You can also trigger `garmin_ha_ai.ask_question` directly from Home Assistant automations or Developer Tools:

```yaml
action: garmin_ha_ai.ask_question
data:
  question: "How has my stress level changed following long runs this week?"
  days_history: 14
```

Upon completion, `sensor.garmin_ai_last_answer` updates automatically and renders the response on your dashboard.

