---
title: DESIGN.md - Garmin Home Assistant AI Integration (garmin-ha-ai)
status: final
created: 2026-08-15
updated: 2026-08-15
sources:
  - planning_artifacts/prds/prd-garmin-ha-ai-2026-08-14/prd.md
  - planning_artifacts/briefs/brief-garmin-ha-ai-2026-08-14/brief.md
colors:
  primary: "#03A9F4"
  primary_variant: "#0288D1"
  secondary: "#00ATC6"
  background: "var(--primary-background-color, #111b27)"
  surface: "var(--ha-card-background, var(--card-background-color, #1c2a3a))"
  text:
    primary: "var(--primary-text-color, #e1e8ed)"
    secondary: "var(--secondary-text-color, #8b9dc3)"
    inverse: "#ffffff"
  status:
    optimal: "#10B981"
    moderate: "#F59E0B"
    rest: "#EF4444"
    ai_accent: "#8B5CF6"
typography:
  font_family: "var(--ha-card-font-family, Roboto, system-ui, sans-serif)"
  sizes:
    badge: "12px"
    body: "14px"
    title: "16px"
    heading: "20px"
  weights:
    regular: 400
    medium: 500
    bold: 700
rounded:
  badge: "16px"
  card: "var(--ha-card-border-radius, 12px)"
  button: "8px"
  input: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  small_view:
    type: "badge-row"
    max_badges: 3
    badge_height: "28px"
  medium_view:
    type: "glance-card"
    max_lines: 3
  large_view:
    type: "markdown-card"
    scrollable: true
  qa_card:
    type: "interactive-dialog"
---

# DESIGN.md — Visual Identity & Component Design Specification

## 1. Brand & Style
`garmin-ha-ai` integrates personal athletic performance tracking with artificial intelligence natively inside Home Assistant. The aesthetic is clean, data-focused, and seamlessly harmonized with standard Home Assistant Lovelace themes (both Dark and Light modes). It balances athletic energy (cyan, emerald, gold accents) with high-legibility AI coaching text.

- **Design Philosophy**: Home Assistant Native First. Uses standard CSS custom properties (`var(--ha-card-background)`, `var(--primary-text-color)`) so the UI automatically adapts to any user theme.
- **Visual Personality**: Precise, encouraging, high-contrast, uncluttered.

---

## 2. Colors
Colors reflect fitness recovery states and AI insights using accessible high-contrast palettes.

| Token | Hex / CSS Variable | Usage |
| :--- | :--- | :--- |
| `colors.primary` | `#03A9F4` | Primary brand accent, Garmin Blue |
| `colors.surface` | `var(--ha-card-background)` | Card container backgrounds |
| `colors.status.optimal` | `#10B981` (Emerald) | High recovery, Sleep score > 80, Goal On-Track |
| `colors.status.moderate` | `#F59E0B` (Amber) | Moderate fatigue, HRV baseline shift |
| `colors.status.rest` | `#EF4444` (Coral Red) | Low body battery (<25), High stress, Rest recommended |
| `colors.status.ai_accent` | `#8B5CF6` (Purple/Indigo) | AI spark icons, coach insights badge |

---

## 3. Typography
Adheres to Home Assistant default typographic hierarchy for seamless dashboard embedding.

- **Badge Text**: `12px`, Medium (500), uppercase or pill layout.
- **Body Text**: `14px`, Regular (400), line height `1.5`. Used in Medium & Large markdown views.
- **Card Titles**: `16px`, Medium (500).
- **Section Headers**: `20px`, Bold (700).

---

## 4. Layout & Spacing
Designs scale across three distinct density tiers to support diverse Lovelace dashboard layouts.

### 4.1 Small View (Glance / Header Badge Row)
- **Compact Layout**: Single line badge row or grid cell holding **2 to 3 status symbols**.
- **Badges**:
  1. 💚 **Recovery & HRV Badge**: Icon + percentage / status (`mdi:heart-pulse`). Color coded (Optimal / Moderate / Rest).
  2. ⚡ **Body Battery & Sleep Badge**: Icon + score (`mdi:battery-charging-80`).
  3. 🎯 **Goal Track Badge**: Target icon (`mdi:target`) with "On Track" / "Behind" indicator.

### 4.2 Medium View (Brief Recommendation Card)
- **Glanceable Card**: Compact card format containing header title + 2-3 lines of direct coaching text.
- **Content**: Recommended action for today's workout + key recovery insight.
- **Spacing**: `16px` padding, max line count 3, optional "Read Full Report" action button.

### 4.3 Large View (Full Markdown Health Report Card)
- **Deep Report Card**: Full-width or vertical dashboard card with scrollable rich Markdown.
- **Content**: Daily summary, 7-day trend analysis, recovery score break-down, structured 3-day workout recommendations, and goal progression advice.
- **Formatting**: H2 headers, bullet lists, bold highlights, and timestamp footer.

---

## 5. Elevation & Depth
- **Native HA Cards**: Uses standard `--ha-card-border-radius` (default `12px`) and subtle elevation box-shadow (`0px 2px 4px rgba(0,0,0,0.1)`).
- **Borders**: Optional `1px solid var(--divider-color, rgba(255,255,255,0.1))` for clean grid separation.

---

## 6. Shapes & Icons
Uses official Material Design Icons (`mdi`) natively available in Home Assistant:

- `mdi:brain` / `mdi:sparkles`: AI Provider / AI Coach indicator
- `mdi:heart-pulse`: HRV & Heart Rate Status
- `mdi:sleep`: Sleep Score & Quality
- `mdi:battery-charging-100`: Body Battery Status
- `mdi:run-fast` / `mdi:weight-lifter`: Activity Recommendations
- `mdi:target`: Fitness Goal Track Status
- `mdi:message-text-outline`: Interactive Q&A Service Trigger

---

## 7. Components

### 7.1 Home Assistant UI Config Flow Forms
- **Step 1: Garmin Auth**: Email, Password, MFA Callback (6-digit input).
- **Step 2: AI Provider Setup**: Dropdown (Google Gemini / Custom OpenAI), API Key input, Model Selector (`gemini-2.0-flash` default).
- **Step 3: Personal Goals**: Target weight input (kg), Weekly workout goal input, Focus Directive textarea.

### 7.2 Home Assistant Lovelace Card Tiers
- **Small Card Component**: `custom:button-card` or native `glance` / `grid` layout.
- **Medium Card Component**: `custom:markdown-card` or native `entities` / `tile` layout.
- **Large Card Component**: `custom:markdown-card` with full report template.
- **Interactive Q&A Card**: Form with `paper-input` or text box + "Ask Coach" button calling service `garmin_ha_ai.ask_question`.

---

## 8. Do's and Don'ts

### Do's:
- **DO** use Home Assistant CSS custom properties for all colors, fonts, and borders so custom themes work automatically.
- **DO** keep the Small View limited strictly to 2–3 easily identifiable status symbols/badges.
- **DO** render the Large View report in clean, well-formatted Markdown with bold key actions.

### Don'ts:
- **DON'T** hardcode dark text on dark backgrounds or light text on light backgrounds.
- **DON'T** display long medical disclaimers in Small or Medium views (keep disclaimers to small footer text in Large view or setup wizard).
- **DON'T** clutter the UI with excessive raw numbers without status color coding.
