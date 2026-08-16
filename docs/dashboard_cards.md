# Lovelace Dashboard Card Patterns & Setup Guide

This guide provides complete, copy-and-paste Lovelace dashboard configurations for the `garmin-ha-ai` integration. It is designed around three core user needs:

1. **⚡ Fast Health Status (Brief Glance)**: At-a-glance recovery, sleep, battery, stress, and steps paired with a concise 1–2 sentence AI daily coaching summary.
2. **💬 Instant Q&A Coach**: Ask ad-hoc health, training, and recovery questions directly from your dashboard with zero helper setup.
3. **📋 Deep Insight View (Long Report)**: Full-width, detailed Markdown health analysis with multi-day training plans and on-demand refresh.

---

## 🌟 Complete Dashboard Presets

### Preset A: Modern Sections Dashboard (Home Assistant 2024.3+)

If your Home Assistant dashboard uses the modern **Sections** layout, paste this YAML directly into a new or existing view:

```yaml
title: 🤖 Garmin AI Health Coach
type: sections
max_columns: 3
sections:
  # Section 1: Fast Status & Daily Summary
  - title: ⚡ Today's Recovery & Health Status
    cards:
      - type: glance
        show_name: true
        show_icon: true
        show_state: true
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

      - type: markdown
        title: 💡 Daily Coach Briefing
        content: >
          <div style="padding: 12px; border-left: 4px solid var(--primary-color, #03a9f4); background: var(--card-background-color, rgba(0,0,0,0.03)); border-radius: 4px;">

          **Recommendation:** {{ states('sensor.garmin_ai_health_report_short') }}

          </div>

  # Section 2: Instant Interactive Q&A Coach
  - title: 💬 Ask AI Health Coach
    cards:
      - type: entities
        show_header_toggle: false
        entities:
          - entity: text.garmin_ai_question
            name: Your Question
          - entity: button.garmin_ai_ask_question
            name: Submit Question

      - type: markdown
        title: 🤖 Latest Coach Answer
        content: >
          <div style="resize: vertical; overflow: auto; min-height: 140px; max-height: 500px; padding: 12px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px;">

          {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
            *Type a question above and tap "Submit Question" to ask your coach.*
          {% else %}
            **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

            ---

            {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}

            <br>
            <small style="color: var(--secondary-text-color);">*Answered: {{ state_attr('sensor.garmin_ai_last_answer', 'timestamp') }}*</small>
          {% endif %}

          </div>

  # Section 3: Deep Insight View (Detailed AI Report)
  - title: 📋 Comprehensive Health Report
    cards:
      - type: entities
        entities:
          - entity: button.garmin_ai_generate_report
            name: Refresh Report Now
          - entity: sensor.garmin_ai_last_update
            name: Last Sync & Update

      - type: markdown
        content: >
          <div style="resize: vertical; overflow: auto; min-height: 220px; max-height: 700px; padding: 14px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px;">

          {{ state_attr('sensor.garmin_ai_health_report_long', 'full_report') | default('No detailed report generated yet. Tap "Refresh Report Now" above.', true) }}

          </div>
```

---

### Preset B: Classic Vertical Stack Dashboard (Any HA Version)

For standard Masonry dashboards or vertical stack panels:

```yaml
type: vertical-stack
cards:
  # Tier 1: Brief Health Status Glance
  - type: glance
    title: 🏃 Garmin Health Status
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
      <div style="padding: 10px 14px; border-left: 4px solid var(--primary-color, #03a9f4); background: var(--card-background-color, rgba(0,0,0,0.03)); border-radius: 6px; font-size: 14px;">
      🤖 <strong>Today's Focus:</strong> {{ states('sensor.garmin_ai_health_report_short') }}
      </div>

  # Tier 2: Instant Q&A Coach
  - type: entities
    title: 💬 Ask AI Coach
    show_header_toggle: false
    entities:
      - entity: text.garmin_ai_question
        name: Question
      - entity: button.garmin_ai_ask_question
        name: Ask Coach

  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 120px; max-height: 400px; padding: 12px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px;">
      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Type a coaching question above and press "Ask Coach".*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}
      {% endif %}
      </div>

  # Tier 3: Deep Insight View (Long Report)
  - type: entities
    title: 📋 Detailed Daily AI Report
    entities:
      - entity: button.garmin_ai_generate_report
        name: Refresh Daily Report

  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 200px; max-height: 600px; padding: 14px; border: 1px solid var(--divider-color, rgba(255,255,255,0.12)); border-radius: 8px;">
      {{ state_attr('sensor.garmin_ai_health_report_long', 'full_report') }}
      </div>
```

---

## 🧩 Modular Standalone Cards

If you prefer adding individual cards to your existing dashboard views:

### 1. Fast Health Status & Briefing Card

Glanceable recovery metrics with the concise AI recommendation banner:

```yaml
type: vertical-stack
cards:
  - type: glance
    title: ⚡ Health & Recovery Overview
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
      **AI Coach Recommendation:** {{ states('sensor.garmin_ai_health_report_short') }}
```

---

### 2. Standalone Instant Q&A Card

Instant question input with automatic zero-helper state management:

```yaml
type: vertical-stack
title: 💬 Ask AI Coach
cards:
  - type: entities
    show_header_toggle: false
    entities:
      - entity: text.garmin_ai_question
        name: Question
      - entity: button.garmin_ai_ask_question
        name: Send Question
  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 120px; max-height: 450px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">

      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *Ask any training or recovery question grounded in your 30-day Garmin history.*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}
      {% endif %}

      </div>
```

---

### 3. Standalone Deep Insight Report Card

Full Markdown analysis with resizable vertical handle:

```yaml
type: vertical-stack
title: 📋 AI Health & Recovery Report
cards:
  - type: entities
    entities:
      - entity: button.garmin_ai_generate_report
        name: Regenerate Report
      - entity: sensor.garmin_ai_last_update
        name: Last Updated
  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 200px; max-height: 650px; padding: 14px; border: 1px solid var(--divider-color); border-radius: 8px;">

      {{ state_attr('sensor.garmin_ai_health_report_long', 'full_report') }}

      </div>
```

---

## 🎛️ Optional Compact Pattern (View Switcher Dropdown)

For minimalists who want a single card that switches between Short Summary, Long Report, and Q&A Answer using a dropdown:

```yaml
type: vertical-stack
title: 🤖 Garmin AI Coach (Compact Switcher)
cards:
  - type: entities
    entities:
      - entity: text.garmin_ai_question
        name: Question
      - entity: button.garmin_ai_ask_question
        name: Ask Coach
      - entity: select.garmin_ai_report_view
        name: Display Mode
      - entity: button.garmin_ai_generate_report
        name: Refresh Report

  - type: markdown
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 140px; max-height: 600px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">

      {{ state_attr('sensor.garmin_ai_selected_report', 'report_text') }}

      </div>
```

---

## 💡 Pro Tips for Lovelace Dashboards

1. **Resizable Containers (`resize: vertical`)**:
   Adding `style="resize: vertical; overflow: auto;"` to the HTML `<div>` in any Markdown card creates a native draggable resize grip at the bottom right corner of the card, allowing you to expand or shrink long reports dynamically in your browser.
2. **Theme Compatibility**:
   All examples use Home Assistant CSS custom properties (`var(--primary-color)`, `var(--card-background-color)`, `var(--divider-color)`, `var(--secondary-text-color)`), ensuring full compatibility with both Light and Dark themes.
3. **Sections View Column Span**:
   In Home Assistant 2024.3+, edit any card in the Sections view and set **Column span: 2** or **3** to give the Deep Insight Report card a wide, spacious layout.

