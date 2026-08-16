# Interactive Lovelace Q&A Card Pattern

This document describes how to set up an interactive Q&A card pattern on your Home Assistant Lovelace dashboard for the `garmin-ha-ai` integration.

## Dashboard Card Architecture

The Interactive Q&A Card pattern consists of two components:
1. **Interactive Question Input & Submit Action**: The native `text.garmin_ai_question` text input and `button.garmin_ai_ask_question` button (or service `garmin_ha_ai.ask_question`).
2. **Answer Display Card**: A resizable Markdown card bound to `sensor.garmin_ai_last_answer.attributes.full_answer` (or `sensor.garmin_ai_selected_report`) displaying the formatted AI response.

## Example Lovelace YAML Configuration

### Option 1: Native Integration Entities (Zero Helper Configuration)

Place the following vertical stack directly in your Lovelace view:

```yaml
type: vertical-stack
title: 🤖 Ask Garmin AI Coach
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
    title: 💬 Latest Coach Answer
    content: >
      <div style="resize: vertical; overflow: auto; min-height: 120px; max-height: 500px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 8px;">

      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *No questions asked yet. Enter a question above and tap "Ask AI Coach".*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}
        
        *Answered at: {{ state_attr('sensor.garmin_ai_last_answer', 'timestamp') }}*
      {% endif %}

      </div>
```

### Option 2: Custom Developer / Script Trigger Pattern

You can also trigger `garmin_ha_ai.ask_question` directly from Home Assistant Developer Tools, scripts, or automations:

```yaml
action: garmin_ha_ai.ask_question
data:
  question: "How is my recovery status today compared to last week?"
  days_history: 7
```

Upon completion, `sensor.garmin_ai_last_answer` updates automatically and renders the response on your dashboard.
