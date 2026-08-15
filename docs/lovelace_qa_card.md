# Interactive Lovelace Q&A Card Pattern

This document describes how to set up an interactive Q&A card pattern on your Home Assistant Lovelace dashboard for the `garmin-ha-ai` integration.

## Dashboard Card Architecture

The Interactive Q&A Card pattern consists of two components:
1. **Interactive Question Input & Submit Action**: An input text field or script/button allowing users to submit a query to service `garmin_ha_ai.ask_question`.
2. **Answer Display Card**: A Markdown card bound to `sensor.garmin_ai_last_answer.attributes.full_answer` displaying the formatted AI response.

## Example Lovelace YAML Configuration

### Option 1: Native Markdown & Input Text Card Pattern

Add an `input_text` helper in Home Assistant (`input_text.garmin_ai_question`) and place the following cards in your Lovelace view:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: 🤖 Ask Garmin AI Coach
    entities:
      - entity: input_text.garmin_ai_question
        name: Your Question
  - type: button
    name: Ask Coach
    icon: mdi:send
    tap_action:
      action: call-service
      service: garmin_ha_ai.ask_question
      service_data:
        question: "{{ states('input_text.garmin_ai_question') }}"
        days_history: 7
  - type: markdown
    title: 💬 Latest Coach Answer
    content: >
      {% if is_state('sensor.garmin_ai_last_answer', 'No question asked yet') %}
        *No questions asked yet. Enter a question above and tap "Ask Coach".*
      {% else %}
        **Q: {{ state_attr('sensor.garmin_ai_last_answer', 'question') }}**

        {{ state_attr('sensor.garmin_ai_last_answer', 'full_answer') }}
        
        *Answered at: {{ state_attr('sensor.garmin_ai_last_answer', 'timestamp') }}*
      {% endif %}
```

### Option 2: Custom Developer / Script Trigger Pattern

You can also trigger `garmin_ha_ai.ask_question` directly from Home Assistant Developer Tools, scripts, or automations:

```yaml
service: garmin_ha_ai.ask_question
data:
  question: "How is my recovery status today compared to last week?"
  days_history: 7
```

Upon completion, `sensor.garmin_ai_last_answer` updates automatically and renders the response on your dashboard.
