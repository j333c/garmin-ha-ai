# Lovelace Dashboard Card Patterns & UI Examples

This guide provides complete Lovelace dashboard configurations for the `garmin-ha-ai` integration, including on-demand report generation, interactive AI health coaching Q&A, and metric overview cards.

---

## 1. On-Demand AI Health Report Button

Generate a fresh health briefing on demand with a single click.

### Option A: Native Button Entity Card (Recommended)
Add the entity `button.garmin_ai_generate_report` directly to any Entities or Grid card:

```yaml
type: button
entity: button.garmin_ai_generate_report
name: Generate AI Report Now
icon: mdi:creation
tap_action:
  action: toggle
```

### Option B: Custom Service Call Button Card
```yaml
type: button
name: Refresh AI Health Report
icon: mdi:refresh
tap_action:
  action: call-service
  service: garmin_ha_ai.generate_report
```

---

## 2. Interactive AI Coach Q&A Card Stack

Ask ad-hoc health, recovery, and workout questions grounded in your historical Garmin metrics (distinct from your morning summary).

### Setup:
1. Create a text helper under **Settings → Devices & Services → Helpers → Create Helper → Text** named `Garmin AI Question` (entity ID: `input_text.garmin_ai_question`).
2. Add the following vertical stack card to your dashboard:

```yaml
type: vertical-stack
title: 🤖 Ask Garmin AI Coach
cards:
  # Input text field for asking a question
  - type: entities
    entities:
      - entity: input_text.garmin_ai_question
        name: Your Question
  # Send button to invoke the AI Coach Q&A service
  - type: button
    name: Ask AI Coach
    icon: mdi:send
    tap_action:
      action: call-service
      service: garmin_ha_ai.ask_question
      service_data:
        question: "{{ states('input_text.garmin_ai_question') }}"
        days_history: 7
  # Dedicated response card displaying the latest answer
  - type: markdown
    title: 💬 Coach Answer
    content: >
      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Enter a question above and tap "Ask AI Coach".*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}

        *Answered: {{ state_attr('sensor.garmin_ai_last_answer', 'timestamp') }}*
      {% endif %}
```

---

## 3. Daily AI Briefing & Metric Overview Cards

### Daily Health Coach Briefing Card
Displays the concise daily recommendation with the option to expand the full multi-section report:

```yaml
type: vertical-stack
cards:
  - type: markdown
    title: 🏃 Daily AI Health Briefing
    content: >
      ### Summary
      {{ states('sensor.garmin_ai_health_report_short') }}

      ---
      {{ state_attr('sensor.garmin_ai_health_report_long', 'full_report') }}
  - type: button
    entity: button.garmin_ai_generate_report
    name: Re-generate Briefing
```

### Metrics Glance Card
```yaml
type: glance
title: 📊 Garmin Health Overview
entities:
  - entity: sensor.garmin_sleep_score
    name: Sleep Score
  - entity: sensor.garmin_body_battery
    name: Body Battery
  - entity: sensor.garmin_stress_level
    name: Stress
  - entity: sensor.garmin_resting_heart_rate
    name: Resting HR
  - entity: sensor.garmin_steps
    name: Steps
  - entity: sensor.garmin_weight
    name: Weight
```
