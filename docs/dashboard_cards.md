# Lovelace Dashboard Card Patterns & UI Examples

This guide provides complete Lovelace dashboard configurations for the `garmin-ha-ai` integration, including interactive AI coaching question input, resizable report viewing cards (Short Summary, Long Report, and Latest Q&A Answer), on-demand report generation, and metric overview cards.

---

## 1. Interactive AI Health Coach & Resizable Report Panel (Recommended)

This all-in-one card stack gives you:
- **Interactive Question Input**: Type your question directly in `text.garmin_ai_question` (no manual helper needed!).
- **One-Click Send Button**: `button.garmin_ai_ask_question` triggers the AI analysis.
- **Report View Selector**: `select.garmin_ai_report_view` lets you toggle between **Short Summary**, **Long Report**, and **Latest Q&A Answer**.
- **Resizable Text Box**: A scrollable text box with a **draggable corner handle** (`resize: vertical`) allowing you to adjust the height of the displayed report directly in your browser.

```yaml
type: vertical-stack
title: 🤖 Garmin AI Health Coach
cards:
  # Question Input & Action Row
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

  # Resizable Report & Answer Display Card
  - type: markdown
    title: 📋 Coach Briefing & Responses
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 140px; max-height: 650px; padding: 12px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px; background: var(--card-background-color, rgba(0,0,0,0.05)); font-size: 14px; line-height: 1.5;">

      {{ state_attr('sensor.garmin_ai_selected_report', 'report_text') }}

      </div>
```

---

## 2. Dedicated Resizable Report Card

If you want a dedicated card displaying either the Short Summary or Long Report with interactive resizing:

### Resizable Daily Health Report Card
```yaml
type: markdown
title: 🏃 Daily AI Health Briefing
content: >
  <div style="resize: vertical; overflow: auto; min-height: 160px; max-height: 700px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">

  ### 📋 Summary
  {{ states('sensor.garmin_ai_health_report_short') }}

  ---

  {{ state_attr('sensor.garmin_ai_health_report_long', 'full_report') }}

  </div>
```

---

## 3. Dedicated Interactive Q&A Card

Ask ad-hoc recovery, nutrition, and workout questions grounded in your historical Garmin metrics:

```yaml
type: vertical-stack
title: 💬 Ask AI Coach
cards:
  - type: entities
    entities:
      - entity: text.garmin_ai_question
        name: Your Question
  - type: button
    entity: button.garmin_ai_ask_question
    name: Ask AI Coach
    icon: mdi:send
    tap_action:
      action: toggle
  - type: markdown
    title: 💡 Latest Answer
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 120px; max-height: 500px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">

      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Type a question above and tap "Ask AI Coach".*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}

        *Answered: {{ state_attr('sensor.garmin_ai_last_answer', 'timestamp') }}*
      {% endif %}

      </div>
```

---

## 4. Metrics Glance & Overview Card

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

---

## 5. Home Assistant Sections View Resizing (HA 2024.3+)

In addition to draggable in-card resizing, you can resize cards using Home Assistant's native **Sections View**:
1. Edit your dashboard and create or select a **Sections (experimental / default in modern HA)** view.
2. Add any of the Markdown or Entities cards above into a section.
3. Click the card options (pencil icon) and adjust the **Column span** and **Row span** to resize the card across the dashboard layout.
