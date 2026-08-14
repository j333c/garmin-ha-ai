---
title: Product Brief - Garmin Home Assistant AI Integration (garmin-ha-ai)
status: draft
created: 2026-08-14
updated: 2026-08-14
---

# Product Brief: Garmin Home Assistant AI Integration (`garmin-ha-ai`)

## Executive Summary

**Garmin Home Assistant AI (`garmin-ha-ai`)** is a privacy-focused Home Assistant custom component that bridges fitness tracking data from Garmin Connect with artificial intelligence (specifically Google Gemini or any standard LLM API). 

Garmin devices collect rich daily metrics (heart rate, HRV, sleep quality, stress, VO2 max, body composition, and workout logs), but vendor applications often restrict analysis to generic algorithms or fixed canned insights. `garmin-ha-ai` automatically ingests and stores your Garmin health data locally inside Home Assistant, combines it with user-defined fitness and weight goals, and passes it to your configured AI model. 

The AI acts as a personalized, context-aware health and fitness coach. It produces tailored workout proposals, lifestyle adjustment advice, and structured daily/weekly reports delivered via Home Assistant dashboards, push notifications, or email. Furthermore, users can ask interactive health questions directly through Home Assistant, giving the AI immediate access to historical health metrics to provide grounded, informed answers.

---

## The Problem

1. **Siloed and Surface-Level Health Insights**: Garmin Connect provides accurate raw data, but native insights are static and rarely adapt to long-term personalized goals, changing lifestyle conditions, or specific user questions.
2. **Privacy & Lock-in Concerns**: Commercial AI fitness apps require uploading personal health metrics to third-party cloud services with expensive subscriptions and proprietary data lock-in.
3. **Lack of Smart Home Integration**: Health metrics are disconnected from Home Assistant context (such as room temperature, daily routines, or notification systems).
4. **Static Dashboards without Actionable Advice**: Home Assistant can display raw numbers (e.g. 7,000 steps), but lacks intelligent interpretation (e.g. "Your HRV is lower than average today; consider replacing your hard run with light recovery").

---

## The Solution

`garmin-ha-ai` connects your Garmin Connect account to Home Assistant and couples it with your own AI API key (Google Gemini via Google AI Pro plan, or any OpenAI-compatible API). 

- **Local Data Persistence**: Daily stats, heart rates, sleep scores, stress levels, and activities are retrieved via `python-garminconnect` and cached locally in Home Assistant.
- **Configurable AI Analysis**: The integration constructs structured prompts combining your latest Garmin metrics, historical trends, personal goals (target weight, step targets, fitness goals), and AI focus areas (e.g. "Focus on marathon prep", "Prioritize sleep recovery", "Weight loss guidance").
- **Multi-Channel Delivery**: Generated reports and advice are stored in Home Assistant entities for dashboard display, and optionally dispatched via Home Assistant notify services (mobile push, persistent notification, email).
- **Interactive Q&A Service**: A dedicated Home Assistant service allows users to send health-related questions to the AI, which automatically injects recent health history into the context before answering.

---

## Key Features & User Experience

### 1. Seamless Garmin Data Sync
- Uses `python-garminconnect` to fetch daily statistics, sleep stages, stress data, HRV, activity logs, and body composition.
- Supports multi-factor authentication (MFA) and OAuth token persistence (`garmin_tokens.json`) to prevent repeated logins.

### 2. Flexible AI Provider Engine
- **Primary**: Google Gemini API (leveraging Google AI Pro plan credentials).
- **Generic/Custom**: Configurable endpoint, model name, and API key for any standard LLM provider (OpenAI, Anthropic, local Ollama / LM Studio).

### 3. Comprehensive Minimum User Settings (Config & Options Flow)
- **Garmin Credentials**: Username, password, MFA verification token, session storage path.
- **AI Configuration**: Provider type (Gemini / Standard OpenAI API), API Key, Model ID (e.g. `gemini-1.5-pro`, `gpt-4o`), Custom Endpoint URL.
- **Health & Goal Inputs**: Fitness goals, weight targets, sport focus, medical or lifestyle notes.
- **AI Persona & Directives**: Custom prompt focus (e.g., "Act as a tough triathlon coach" vs. "Act as a gentle wellness advisor").
- **Automation & Schedules**: Configurable daily/weekly/monthly/etc sync time, report generation schedule.
- **Report & Output Preferences**: Report length (Short summary for dashboard / Long deep-dive report), delivery targets (Dashboard entity, Push message, E-Mail).

### 4. Interactive Health Q&A
- Exposes a Home Assistant service (`garmin_ha_ai.ask_question`) usable from Lovelace dashboards, scripts, or voice assistants (Assist).
- Automatically retrieves relevant recent Garmin metrics (e.g. past 7 days) as grounding context for the prompt.

---

## Technical Architecture & Design Principles

Following Home Assistant best practices (based on `home-assistant/example-custom-config/tree/master/custom_components/`):

1. **Component Directory Structure**:
   - `custom_components/garmin_ha_ai/`
     - `__init__.py`: Component setup, entry loading, service registrations.
     - `manifest.json`: Dependencies (`python-garminconnect`, `google-genai` / `httpx`), version, domain (`garmin_ha_ai`).
     - `config_flow.py`: Initial setup UI for Garmin login and AI keys, plus Options Flow for adjusting goals and schedules.
     - `coordinator.py`: `DataUpdateCoordinator` managing scheduled polling and caching of Garmin Connect data.
     - `sensor.py`: Exposes sensors for latest Garmin metrics and AI generated report entities (short text, long report, recommendations).
     - `services.yaml`: Schema definition for interactive Q&A and manual report triggers.
2. **Local Storage & Persistence**:
   - Garmin authentication tokens saved in HA `.storage` or custom config directory.
   - Recent health history kept in local state/history or JSON store for LLM context assembly.
3. **Async Execution**:
   - Network requests to Garmin API and AI provider executed asynchronously via `asyncio` and `aiohttp`/`httpx` to avoid blocking the Home Assistant event loop.

---

## Scope & Implementation Roadmap

### Phase 1: MVP (Initial Release)
- Custom component setup with Config Flow for Garmin credentials + Gemini API key.
- Polling Garmin Connect daily metrics via `python-garminconnect`.
- Exposing core health sensors (Steps, Sleep Score, HRV, Stress, Weight).
- Scheduled daily AI report generation (Gemini) producing a summary sensor entity.
- Basic interactive service `garmin_ha_ai.ask_question`.
- Git repository setup at `http://git.crins:3000/jens/garmin-ha-ai` with structured commit history.

### Phase 2: Enhanced Features
- Extended AI provider support (OpenAI-compatible endpoints, local LLMs).
- Advanced notification routing (Push, Email integration).
- Options Flow UI for dynamically adjusting goals, prompt directives, and schedules without re-authenticating.
- Historical trend analysis (7-day, 30-day comparative context window for AI prompts).

---

## Success Criteria

1. **Reliable Sync**: Successful daily fetch of Garmin metrics without session disconnects or rate-limit issues.
2. **Actionable AI Feedback**: AI responses consistently reference actual user metrics (e.g. sleep score, workout intensity) and user goals to provide realistic advice.
3. **Seamless HA Native Experience**: Integrates smoothly into Home Assistant via UI Config Flow, native sensors, and standard notifications.
4. **Clean Code & Version Control**: Structured repository with semantic commit messages pushed to `http://git.crins:3000/jens/garmin-ha-ai`.
5. **Deployable**: Instant deployable integration into a standard home assistant installation.
