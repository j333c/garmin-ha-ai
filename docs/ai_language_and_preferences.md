# AI Language & Coaching Preferences Guide

## Overview

Garmin HA AI provides multilingual coaching support, enabling users to receive daily health briefings, recovery analysis, and interactive Q&A in their preferred language. The language preference is configured in the integration's **Options Flow** and injected deterministically into the AI Engine's prompt assembler.

---

## Supported Languages

The integration supports the following standard language selections:

* **English (`en`)** *(Default)*
* **German (`de` - Deutsch)**
* **French (`fr` - Français)**
* **Spanish (`es` - Español)**
* **Italian (`it` - Italiano)**
* **Dutch (`nl` - Nederlands)**
* **Follow Home Assistant Language (`system`)** — Automatically matches the current user's active Home Assistant locale.

---

## How It Works: Prompt Context Injection

In [`custom_components/garmin_ha_ai/ai_engine/prompt.py`](file:///home/jens/Projekte/garmin-ha-ai/custom_components/garmin_ha_ai/ai_engine/prompt.py), Block 5 of the prompt payload defines the structural output formatting rules. When a language preference is set, a strict language directive is injected into Block 5 and into the system prompt:

```markdown
### BLOCK 5: STRUCTURAL OUTPUT FORMATTING RULES
1. You MUST start your response with a concise 1-2 sentence summary enclosed in <summary>...</summary> tags.
   - The summary text inside <summary> MUST NOT exceed 200 characters.
2. Following the <summary> block, provide the complete, detailed Daily Health Briefing in Markdown format.
3. LANGUAGE DIRECTIVE (CRITICAL):
   - You MUST write the ENTIRE response, including both the <summary>...</summary> content and the markdown body, in German (Deutsch).
   - Use standard fitness, medical, and biometric terminology natural to a German-speaking coach (e.g. "Ruhepuls", "Herzfrequenzvariabilität (HRV)", "Schlafindex", "Körperbatterie").
```

---

## Prompt & Output Examples Across Languages

### 1. English (Default)

#### Generated Output:
```markdown
<summary>Excellent recovery with an 86 Sleep Score and +70 Body Battery. Ready for quality threshold intervals today.</summary>

## Summary & Recovery Status
Your physiological readiness is peak today. Resting heart rate held steady at 48 bpm, and your overnight HRV of 62 ms indicates your parasympathetic nervous system is thoroughly restored following Tuesday's endurance session.

## Sleep & Stress Analysis
- **Sleep Quality:** 86/100 (Deep Sleep: 1h 45m | REM: 2h 05m). Restorative sleep accounted for 42% of your night.
- **Overnight Stress:** Averaged a calm 14/100 with zero stress spikes after 01:00 AM.

## Actionable Recommendations
- **Workout:** Primary window for a high-intensity session or tempo run.
- **Nutrition & Hydration:** Maintain electrolyte intake before afternoon training.
```

---

### 2. German (Deutsch)

#### Generated Output:
```markdown
<summary>Hervorragende Regeneration mit Schlafindex 86 und Body Battery 90. Optimaler Tag für ein intensives Intervalltraining.</summary>

## Zusammenfassung & Erholungsstatus
Deine physiologische Leistungsbereitschaft ist heute auf Höchststand. Dein Ruhepuls liegt stabil bei 48 bpm, und eine nächtliche HRV von 62 ms zeigt, dass sich dein vegetatives Nervensystem nach der Ausdauereinheit am Dienstag vollständig erholt hat.

## Schlaf- & Stressanalyse
- **Schlafqualität:** 86/100 (Tiefschlaf: 1h 45m | REM-Schlaf: 2h 05m). Regenerative Schlafphasen machten über 40% der Nacht aus.
- **Stresslevel:** Durchschnittlich sehr entspannte 14/100 ohne nennenswerte Stressspitzen nach 01:00 Uhr.

## Konkrete Handlungsempfehlungen
- **Training:** Ideales Zeitfenster für ein Tempotraining oder Schwellenintervalle.
- **Ernährung & Flüssigkeit:** Ausreichend Elektrolyte vor dem Nachmittagstraining zuführen.
```

---

### 3. French (Français)

#### Generated Output:
```markdown
<summary>Excellente récupération avec un score de sommeil de 86 et une Body Battery à 90. Journée idéale pour un entraînement au seuil.</summary>

## Résumé et État de Récupération
Votre préparation physiologique est optimale aujourd'hui. Votre fréquence cardiaque au repos est stable à 48 bpm, et votre VFC nocturne de 62 ms confirme une restauration parasympathique complète.

## Analyse du Sommeil et du Stress
- **Score de Sommeil :** 86/100 (Sommeil profond : 1h 45m | Sommeil paradoxal : 2h 05m).
- **Niveau de Stress :** Moyenne de 14/100, nuit très calme sans perturbations.

## Recommandations pour la Journée
- **Séance :** Feu vert pour une séance d'intervalles ou de travail d'allure spécifique.
- **Hydratation :** Pensez à bien vous hydrater avant votre séance de l'après-midi.
```

---

### 4. Spanish (Español)

#### Generated Output:
```markdown
<summary>Excelente recuperación con puntuación de sueño de 86 y Body Battery al 90%. Día perfecto para entrenamiento de series.</summary>

## Resumen y Estado de Recuperación
Tu preparación física está en su punto óptimo hoy. La frecuencia cardíaca en reposo se mantiene baja en 48 ppm, y la VFC de 62 ms demuestra una recuperación completa del sistema nervioso.

## Análisis de Sueño y Estrés
- **Calidad de Sueño:** 86/100 (Sueño profundo: 1h 45m | REM: 2h 05m).
- **Estrés Nocturno:** Promedio de 14/100 sin picos de fatiga.

## Recomendaciones para Hoy
- **Entrenamiento:** Condiciones óptimas para series en pista o carrera a ritmo controlado.
- **Recuperación:** Mantén una buena hidratación previa a la sesión.
```

---

## Configuring Language in Home Assistant

1. Navigate to **Settings > Devices & Services > Garmin HA AI**.
2. Click **Configure** on your configured entry.
3. In the Options dialog, locate **AI Response Language**.
4. Select your preferred language (e.g. `German (de)`).
5. Click **Submit**. Subsequent reports and interactive Q&A queries will immediately adopt the selected language.
