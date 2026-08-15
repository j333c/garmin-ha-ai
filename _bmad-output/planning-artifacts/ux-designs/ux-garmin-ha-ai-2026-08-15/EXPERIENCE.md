---
title: EXPERIENCE.md - Garmin Home Assistant AI Integration (garmin-ha-ai)
status: final
created: 2026-08-15
updated: 2026-08-15
sources:
  - planning_artifacts/prds/prd-garmin-ha-ai-2026-08-14/prd.md
  - planning_artifacts/briefs/brief-garmin-ha-ai-2026-08-14/brief.md
  - planning_artifacts/ux-designs/ux-garmin-ha-ai-2026-08-15/DESIGN.md
---

# EXPERIENCE.md — Information Architecture & User Experience Specification

## 1. Foundation
- **Platform**: Home Assistant Core Web Interface, Lovelace Dashboards, Native Config Flow UI, Mobile Companion App (iOS & Android).
- **Design System Reference**: Home Assistant Frontend / Material Design 3 (M3) UI components. Visual tokens are inherited from `DESIGN.md`.
- **Primary Goal**: Deliver intuitive, glanceable, and context-aware health insights directly inside the user's smart home dashboard without requiring external apps.

---

## 2. Information Architecture & UI Surfaces

```
garmin_ha_ai Integration Architecture
├── UI Configuration & Setup
│   ├── Config Flow Setup (Garmin Credentials -> MFA -> AI Provider -> User Goals)
│   └── Options Flow Settings (Update Goals, Directives, Polling Schedule, Notification Target)
├── Sensor & Data Layer
│   ├── Native Garmin Sensors (sensor.garmin_steps, sensor.garmin_sleep_score, sensor.garmin_stress_level, etc.)
│   ├── AI Report Entities (sensor.garmin_ai_health_report_short, sensor.garmin_ai_health_report_long)
│   └── Last Sync & Q&A Sensors (sensor.garmin_ai_last_update, sensor.garmin_ai_last_answer)
├── Dashboard Visual Density Tiers (Lovelace)
│   ├── Small View (2-3 Status Badges: Recovery, Sleep, Goal Track)
│   ├── Medium View (Brief 1-2 sentence workout & recovery recommendation)
│   └── Large View (Full Markdown health report with multi-day training advice)
├── Interactive Q&A Surface
│   ├── HA Service Call: garmin_ha_ai.ask_question
│   └── Dashboard Input Card: Text Question Box + "Ask Coach" submit button
└── Multi-Channel Notifications
    └── Mobile Push Notification / Persistent Notification Dispatch
```

---

## 3. Voice and Tone (Microcopy)

- **AI Coach Persona**: Direct, supportive, data-driven personal athletic coach. Speaks with clarity and focus.
- **Tone Guidelines**:
  - *Encouraging*: Celebrate consistency and high recovery.
  - *Pragmatic*: When recovery is low or stress is high, give explicit permission to rest/taper without guilt.
  - *Actionable*: Always conclude recommendations with a clear workout type (e.g., "Recommended: 45 min Zone 2 run" or "Recommended: Rest & Mobility").
- **Disclaimers**: Keep technical/non-medical disclaimers subtle: *"AI recommendations are for fitness coaching, not medical diagnosis."*

---

## 4. Component Patterns

### 4.1 Small View Pattern (Status Badges)
- **Purpose**: At-a-glance fitness and goal tracking in dense headers or glance grids (`{components.small_view}`).
- **Structure**: 2 to 3 pill badges:
  1. **Recovery / HRV Symbol**: Color-coded pill (`{colors.status.optimal}`, `{colors.status.moderate}`, `{colors.status.rest}`) showing Recovery status (e.g., `💚 Optimal HRV`).
  2. **Sleep / Body Battery Symbol**: Pill showing overnight sleep score & current body battery (e.g., `⚡ Sleep 88 | Battery 92%`).
  3. **Goal Track Symbol**: Target icon showing weekly progress status (e.g., `🎯 Goal: On Track (4/5 runs)`).

### 4.2 Medium View Pattern (Brief Workout Recommendation)
- **Purpose**: Quick dashboard card providing today's immediate recommendation (`{components.medium_view}`).
- **Structure**:
  - Header: `🤖 AI Health Coach`
  - Body: Concise 2-line recommendation text from `sensor.garmin_ai_health_report_short`.
  - Example: *"Recovery is high (Sleep 88/100, Body Battery 92). Recommended today: 45 min Zone 2 aerobic run."*

### 4.3 Large View Pattern (Detailed Markdown Health Report)
- **Purpose**: Deep analytical review for daily/weekly health tracking (`{components.large_view}`).
- **Structure**:
  - Title & Timestamp Header.
  - **Section 1: Daily Health & Recovery Breakdown** (Sleep, HRV, Stress, Resting HR).
  - **Section 2: Workout Recommendation for Today** (Specific target zone, duration, intensity rationale).
  - **Section 3: 3-Day Outlook & Weekly Goal Alignment** (Adjustments based on weekly fatigue trends).
  - Footer: Refresh button (`garmin_ha_ai.generate_report`) + non-medical disclaimer.

### 4.4 Interactive Q&A Card Pattern
- **Purpose**: On-demand questions with 7-day historical Garmin data grounding (`{components.qa_card}`).
- **Structure**:
  - Input field: `Ask your Garmin AI Coach a question...`
  - Action button: `Ask Coach`
  - Output display: Markdown card rendering the latest answer from `sensor.garmin_ai_last_answer`.

---

## 5. State Patterns

| State | Visual Indicator | User Guidance |
| :--- | :--- | :--- |
| **Initial Setup** | Config Flow Form | Step 1/3 wizard prompts for credentials. |
| **MFA Code Required** | Special Form Prompt | Displays 6-digit passcode input box (120s countdown). |
| **Syncing Data** | `mdi:spin mdi:loading` | "Syncing latest Garmin metrics..." |
| **Generating Report** | `{colors.status.ai_accent}` pulse | "AI Coach is analyzing your recovery and goals..." |
| **Ready / Normal** | Complete Badges & Cards | Metrics and AI reports rendered cleanly. |
| **Garmin Auth Error** | Red Alert Banner | "Garmin login expired. Re-enter credentials in Options Flow." |
| **Rate Limited / Offline** | Orange Warning Banner | "Garmin rate limit reached. Showing cached metrics from 06:00 AM." |

---

## 6. Interaction Primitives

1. **Manual Report Refresh**: Lovelace button or entity tap triggers `garmin_ha_ai.generate_report`.
2. **Interactive Question Submit**: Entering text into the Q&A card calls `garmin_ha_ai.ask_question(question=...)`.
3. **Options Update**: Re-configuring target weight or workout directives in Options Flow takes effect on next automated sync.

---

## 7. Accessibility Floor

- **Screen Readers**: All status badges in Small View include full text `aria-label` descriptions (e.g. `aria-label="Recovery level high, sleep score 88 out of 100"`).
- **Color Contrast**: All badge text and icons maintain > 4.5:1 contrast against surface backgrounds (`{colors.surface}`).
- **Keyboard Navigation**: Config Flow forms and Q&A input fields support standard Tab and Enter submission.

---

## 8. Key User Journeys

### Journey 1: Setup & Initial Configuration
- **Protagonist**: Jens (Home Assistant user).
- **Goal**: Connect Garmin Connect and Google Gemini to set up automated health coaching.
- **Flow**:
  1. Jens goes to Settings -> Integrations -> Add Integration -> "Garmin HA AI".
  2. Enters Garmin email and password. Receives MFA prompt on phone; enters 6-digit MFA code in setup form.
  3. Selects AI Provider (`Google Gemini`), enters API Key, specifies target weight (78 kg) and fitness directive ("Training for half marathon").
  4. Form validates credentials and creates entities immediately.

### Journey 2: Morning Fitness Briefing
- **Protagonist**: Jens waking up at 07:00 AM.
- **Goal**: Know what workout to do today based on overnight recovery.
- **Flow**:
  1. Automated sync triggers at 06:00 AM.
  2. Jens opens Home Assistant on phone or desktop dashboard.
  3. **Small View Badge Row** at top of screen displays `💚 HRV Optimal | ⚡ Sleep 88 | 🎯 Goal On Track`.
  4. **Medium View Card** right below shows: *"Recovery high. Today's recommendation: 45 min Zone 2 run."*
  5. Jens taps card to expand to **Large View** to read 3-day workout recommendations and sleep breakdown.

### Journey 3: Interactive Question ("Should I lift heavy today?")
- **Protagonist**: Jens feeling stiff after yesterday's run.
- **Goal**: Ask AI coach for specific advice given stiff muscles.
- **Flow**:
  1. Jens opens the **Interactive Q&A Card** on his HA dashboard.
  2. Types: *"My calves feel tight from yesterday's 12km run. Should I do heavy leg workouts today?"*
  3. Service `garmin_ha_ai.ask_question` fetches 7-day Garmin history and sends prompt to Gemini.
  4. Response appears within 5 seconds: *"Your 12km run yesterday had an elevated strain score (14.2). Given your calf tightness, skip heavy leg workouts today. Swap for 30 minutes of low-impact cycling and foam rolling."*
