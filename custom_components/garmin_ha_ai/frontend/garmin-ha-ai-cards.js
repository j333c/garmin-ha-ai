/**
 * Garmin HA AI - Lovelace Custom Dashboard Cards
 *
 * Provides native custom cards for Home Assistant Lovelace:
 * 1. custom:garmin-ha-ai-qa-card        (Interactive Q&A Coach Card)
 * 2. custom:garmin-ha-ai-report-card    (Comprehensive AI Health Report Card)
 * 3. custom:garmin-ha-ai-overview-card  (All-in-one Health & Coach Overview Card)
 */

(function () {
  "use strict";

  /**
   * Lightweight, robust, and safe Markdown parser for rendering formatted AI coaching text.
   * Uses linear line-by-line block parsing to eliminate catastrophic regex backtracking.
   */
  function renderMarkdown(md) {
    if (!md || typeof md !== "string") {
      return "";
    }

    try {
      // 1. Escape HTML entities to prevent XSS
      let html = md
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

      // 2. Fenced code blocks: ```code```
      html = html.replace(/```([\s\S]*?)```/g, function (_, code) {
        return `<pre class="garmin-code-block"><code>${code.trim()}</code></pre>`;
      });

      // 3. Inline code: `code`
      html = html.replace(/`([^`\n]+)`/g, '<code class="garmin-inline-code">$1</code>');

      // 4. Horizontal rules: --- or *** or ___
      html = html.replace(/^(?:---|[*]{3}|_{3})\s*$/gm, '<hr class="garmin-hr" />');

      // 5. Headers (#, ##, ###, ####)
      html = html.replace(/^#### (.*$)/gm, '<h5 class="garmin-h5">$1</h5>');
      html = html.replace(/^### (.*$)/gm, '<h4 class="garmin-h4">$1</h4>');
      html = html.replace(/^## (.*$)/gm, '<h3 class="garmin-h3">$1</h3>');
      html = html.replace(/^# (.*$)/gm, '<h2 class="garmin-h2">$1</h2>');

      // 6. Bold & Italics
      html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
      html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');
      html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
      html = html.replace(/_([^_\n]+)_/g, '<em>$1</em>');

      // 7. GitHub-style alerts & blockquotes
      html = html.replace(/^&gt;\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$/gm, function (_, type, text) {
        const cls = type.toLowerCase();
        return `<div class="garmin-alert garmin-alert-${cls}"><strong>${type}:</strong> ${text}</div>`;
      });
      html = html.replace(/^&gt;\s*(.*)$/gm, '<blockquote class="garmin-quote">$1</blockquote>');

      // 8. Markdown Links [text](url)
      html = html.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="garmin-link">$1</a>');

      // 9. Safe Linear Line-by-Line Block & List Parser (No backtracking regexes)
      const lines = html.split("\n");
      const out = [];
      let inUl = false;
      let inOl = false;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // Check for bullet list item: * text or - text or + text
        const ulMatch = line.match(/^(\s*)[*\-+]\s+(.*)$/);
        // Check for numbered list item: 1. text
        const olMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);

        if (ulMatch) {
          if (inOl) {
            out.push("</ol>");
            inOl = false;
          }
          if (!inUl) {
            out.push('<ul class="garmin-ul">');
            inUl = true;
          }
          out.push(`<li class="garmin-li">${ulMatch[2]}</li>`);
          continue;
        }

        if (olMatch) {
          if (inUl) {
            out.push("</ul>");
            inUl = false;
          }
          if (!inOl) {
            out.push('<ol class="garmin-ol">');
            inOl = true;
          }
          out.push(`<li class="garmin-oli">${olMatch[2]}</li>`);
          continue;
        }

        // If open list, close it on non-list line
        if (inUl) {
          out.push("</ul>");
          inUl = false;
        }
        if (inOl) {
          out.push("</ol>");
          inOl = false;
        }

        if (!trimmed) {
          continue;
        }

        if (
          trimmed.startsWith("<h") ||
          trimmed.startsWith("<pre") ||
          trimmed.startsWith("<blockquote") ||
          trimmed.startsWith("<div") ||
          trimmed.startsWith("<hr")
        ) {
          out.push(trimmed);
        } else {
          out.push(`<p class="garmin-p">${trimmed}</p>`);
        }
      }

      if (inUl) out.push("</ul>");
      if (inOl) out.push("</ol>");

      return out.filter(Boolean).join("\n");
    } catch (err) {
      console.warn("Garmin HA AI Markdown parse fallback:", err);
      return `<p class="garmin-p">${String(md).replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\n/g, "<br/>")}</p>`;
    }
  }

  const BASE_STYLES = `
    ha-card {
      padding: 16px;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #212121);
      box-sizing: border-box;
      position: relative;
    }
    .garmin-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
      gap: 8px;
    }
    .garmin-card-title {
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--primary-text-color, #212121);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .garmin-card-title ha-icon {
      color: var(--primary-color, #03a9f4);
    }
    .garmin-btn {
      background-color: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #ffffff);
      border: none;
      border-radius: 6px;
      padding: 8px 16px;
      font-size: 0.9rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: opacity 0.2s, transform 0.1s;
    }
    .garmin-btn:hover {
      opacity: 0.9;
    }
    .garmin-btn:active {
      transform: scale(0.98);
    }
    .garmin-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .garmin-btn-secondary {
      background-color: var(--card-background-color, rgba(128,128,128,0.1));
      color: var(--primary-text-color, #212121);
      border: 1px solid var(--divider-color, rgba(128,128,128,0.2));
    }
    .garmin-error-banner {
      background-color: rgba(244, 67, 54, 0.12);
      border-left: 4px solid var(--error-color, #f44336);
      color: var(--error-color, #f44336);
      padding: 10px 12px;
      border-radius: 6px;
      margin-bottom: 12px;
      font-size: 0.9rem;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
      line-height: 1.4;
    }
    .garmin-error-banner ha-icon {
      color: var(--error-color, #f44336);
      flex-shrink: 0;
      margin-top: 1px;
    }
    .garmin-error-text {
      flex: 1;
    }
    .garmin-error-close {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #757575);
      cursor: pointer;
      padding: 2px 4px;
      font-size: 0.85rem;
      font-weight: 600;
    }
    .garmin-input-container {
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
      align-items: flex-start;
    }
    .garmin-textarea {
      flex: 1;
      width: 100%;
      min-height: 44px;
      max-height: 120px;
      padding: 10px 12px;
      font-family: inherit;
      font-size: 0.95rem;
      border-radius: 8px;
      border: 1px solid var(--divider-color, rgba(128,128,128,0.3));
      background: var(--input-fill-color, var(--card-background-color, #ffffff));
      color: var(--primary-text-color, #212121);
      resize: vertical;
      box-sizing: border-box;
      outline: none;
      transition: border-color 0.2s;
    }
    .garmin-textarea:focus {
      border-color: var(--primary-color, #03a9f4);
    }
    .garmin-content-box {
      border: 1px solid var(--divider-color, rgba(128,128,128,0.2));
      border-radius: 8px;
      padding: 14px;
      background: var(--card-background-color, rgba(0,0,0,0.02));
      overflow-y: auto;
      resize: vertical;
      min-height: 120px;
      max-height: 500px;
      font-size: 0.95rem;
      line-height: 1.55;
      box-sizing: border-box;
    }
    .garmin-empty-state {
      color: var(--secondary-text-color, #757575);
      font-style: italic;
      text-align: center;
      padding: 24px 12px;
    }
    .garmin-loading-spinner {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      color: var(--secondary-text-color, #757575);
      font-style: italic;
      padding: 24px 12px;
    }
    .garmin-spinner {
      width: 20px;
      height: 20px;
      border: 3px solid var(--divider-color, rgba(128,128,128,0.2));
      border-top: 3px solid var(--primary-color, #03a9f4);
      border-radius: 50%;
      animation: garmin-spin 1s linear infinite;
    }
    @keyframes garmin-spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .garmin-q-banner {
      font-weight: 600;
      color: var(--primary-text-color, #212121);
      margin-bottom: 8px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--divider-color, rgba(128,128,128,0.2));
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .garmin-meta-time {
      font-size: 0.8rem;
      font-weight: 400;
      color: var(--secondary-text-color, #757575);
    }
    .garmin-glance-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(65px, 1fr));
      gap: 8px;
      margin-bottom: 14px;
    }
    .garmin-metric-pill {
      background: var(--card-background-color, rgba(128,128,128,0.06));
      border: 1px solid var(--divider-color, rgba(128,128,128,0.15));
      border-radius: 8px;
      padding: 8px 4px;
      text-align: center;
    }
    .garmin-metric-label {
      font-size: 0.75rem;
      color: var(--secondary-text-color, #757575);
      margin-bottom: 2px;
    }
    .garmin-metric-val {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--primary-text-color, #212121);
    }
    .garmin-focus-banner {
      border-left: 4px solid var(--primary-color, #03a9f4);
      background: var(--card-background-color, rgba(3, 169, 244, 0.08));
      padding: 10px 14px;
      border-radius: 6px;
      margin-bottom: 14px;
      font-size: 0.95rem;
      line-height: 1.45;
    }
    .garmin-tab-bar {
      display: flex;
      gap: 6px;
      margin-bottom: 12px;
      border-bottom: 1px solid var(--divider-color, rgba(128,128,128,0.2));
      padding-bottom: 6px;
    }
    .garmin-tab-btn {
      background: transparent;
      border: none;
      padding: 6px 12px;
      font-size: 0.9rem;
      font-weight: 500;
      color: var(--secondary-text-color, #757575);
      cursor: pointer;
      border-radius: 4px;
    }
    .garmin-tab-btn.active {
      color: var(--primary-color, #03a9f4);
      background: var(--card-background-color, rgba(3, 169, 244, 0.1));
      font-weight: 600;
    }
    .garmin-p { margin: 0 0 10px 0; }
    .garmin-p:last-child { margin-bottom: 0; }
    .garmin-h2 { margin: 12px 0 6px 0; font-size: 1.15rem; font-weight: 700; }
    .garmin-h3 { margin: 10px 0 4px 0; font-size: 1.05rem; font-weight: 600; }
    .garmin-h4 { margin: 8px 0 4px 0; font-size: 0.95rem; font-weight: 600; }
    .garmin-h5 { margin: 6px 0 3px 0; font-size: 0.90rem; font-weight: 600; }
    .garmin-ul, .garmin-ol { margin: 0 0 10px 0; padding-left: 22px; }
    .garmin-li, .garmin-oli { margin-bottom: 4px; }
    .garmin-code-block {
      background: var(--code-editor-background-color, #1e1e1e);
      color: #f8f8f2;
      padding: 10px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 0.85rem;
    }
    .garmin-inline-code {
      background: var(--card-background-color, rgba(128,128,128,0.15));
      padding: 2px 5px;
      border-radius: 4px;
      font-size: 0.88em;
    }
    .garmin-quote {
      margin: 8px 0;
      padding: 6px 12px;
      border-left: 3px solid var(--primary-color, #03a9f4);
      color: var(--secondary-text-color, #757575);
      background: var(--card-background-color, rgba(0,0,0,0.02));
    }
    .garmin-alert {
      padding: 8px 12px;
      border-radius: 6px;
      margin: 8px 0;
      font-size: 0.9rem;
    }
    .garmin-alert-note { background: rgba(3, 169, 244, 0.1); border-left: 4px solid #03a9f4; }
    .garmin-alert-tip { background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4caf50; }
    .garmin-alert-warning { background: rgba(255, 152, 0, 0.1); border-left: 4px solid #ff9800; }
    .garmin-hr {
      border: 0;
      height: 1px;
      background: var(--divider-color, rgba(128,128,128,0.2));
      margin: 12px 0;
    }
  `;

  /**
   * 1. Garmin AI Q&A Coach Card
   */
  class GarminHAIQAQuestionCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._loading = false;
      this._error = null;
      this._directAnswer = null;
      this._lastAnswerTimestamp = null;
      this._initialized = false;
      this._config = {
        title: "Garmin AI Coach Q&A",
        question_entity: "text.garmin_ai_question",
        button_entity: "button.garmin_ai_ask_question",
        answer_entity: "sensor.garmin_ai_last_answer",
      };
    }

    setConfig(config) {
      this._config = Object.assign(
        {
          title: "Garmin AI Coach Q&A",
          question_entity: "text.garmin_ai_question",
          button_entity: "button.garmin_ai_ask_question",
          answer_entity: "sensor.garmin_ai_last_answer",
        },
        config || {}
      );
      if (!this._initialized) {
        this._render();
        this._initialized = true;
      }
      this._updateContent();
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._config) return;

      try {
        const answerState = hass && hass.states ? hass.states[this._config.answer_entity] : undefined;
        const currentTimestamp = answerState?.attributes?.timestamp || null;

        // If we were waiting for an answer and a new timestamp arrived, stop loading
        if (this._loading && currentTimestamp && currentTimestamp !== this._lastAnswerTimestamp) {
          this._loading = false;
          this._error = null;
          this._directAnswer = null;
        }
        this._lastAnswerTimestamp = currentTimestamp;

        this._updateContent();
      } catch (err) {
        console.error("Error in GarminHAIQAQuestionCard set hass:", err);
      }
    }

    static getStubConfig() {
      return {
        type: "custom:garmin-ha-ai-qa-card",
        title: "Garmin AI Coach Q&A",
        question_entity: "text.garmin_ai_question",
        button_entity: "button.garmin_ai_ask_question",
        answer_entity: "sensor.garmin_ai_last_answer",
      };
    }

    getCardSize() {
      return 4;
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>${BASE_STYLES}</style>
        <ha-card>
          <div class="garmin-card-header">
            <div class="garmin-card-title">
              <ha-icon icon="mdi:chat-question"></ha-icon>
              <span>${this._config.title}</span>
            </div>
          </div>
          <div id="errorBox"></div>
          <div class="garmin-input-container">
            <textarea
              class="garmin-textarea"
              placeholder="Ask about your recovery, sleep, workout readiness, or Garmin stats..."
              rows="2"
            ></textarea>
            <button class="garmin-btn" id="askBtn">
              <ha-icon icon="mdi:send"></ha-icon>
              <span>Ask</span>
            </button>
          </div>
          <div class="garmin-content-box" id="answerBox">
            <div class="garmin-empty-state">
              Type a question above and click "Ask" to consult your AI Health Coach.
            </div>
          </div>
        </ha-card>
      `;

      const askBtn = this.shadowRoot.getElementById("askBtn");
      const textarea = this.shadowRoot.querySelector(".garmin-textarea");

      if (askBtn && textarea) {
        askBtn.addEventListener("click", () => this._submitQuestion());
        textarea.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
            e.preventDefault();
            this._submitQuestion();
          }
        });
      }
    }

    async _submitQuestion() {
      const textarea = this.shadowRoot ? this.shadowRoot.querySelector(".garmin-textarea") : null;
      const question = (textarea?.value || "").trim();
      if (!question || !this._hass) return;

      this._loading = true;
      this._error = null;
      this._updateContent();

      try {
        const response = await this._hass.callService(
          "garmin_ha_ai",
          "ask_question",
          { question: question },
          undefined,
          true,
          true
        );
        if (textarea) textarea.value = "";
        this._loading = false;
        this._error = null;
        if (response && response.response && response.response.answer) {
          this._directAnswer = response.response;
        }
        this._updateContent();
      } catch (err) {
        console.error("Garmin AI Q&A Error:", err);
        let errorMsg = err?.message || String(err);
        if (errorMsg.includes("503") || errorMsg.includes("UNAVAILABLE") || errorMsg.includes("high demand")) {
          errorMsg = "AI model is currently experiencing high demand (503 Service Unavailable). Please try again in a moment.";
        } else if (errorMsg.includes("429") || errorMsg.includes("quota")) {
          errorMsg = "AI API quota or rate limit exceeded (429).";
        } else if (errorMsg.includes("HomeAssistantError:")) {
          errorMsg = errorMsg.replace("HomeAssistantError:", "").trim();
        }
        this._error = errorMsg;
        this._loading = false;
        this._updateContent();
      }
    }

    _updateContent() {
      if (!this.shadowRoot || !this._hass || !this._config) return;

      const errorBox = this.shadowRoot.getElementById("errorBox");
      const answerBox = this.shadowRoot.getElementById("answerBox");
      const askBtn = this.shadowRoot.getElementById("askBtn");
      if (!answerBox) return;

      // Render Error Banner if active
      if (errorBox) {
        if (this._error) {
          errorBox.innerHTML = `
            <div class="garmin-error-banner">
              <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
              <div class="garmin-error-text"><strong>AI Notice:</strong> ${this._error}</div>
              <button class="garmin-error-close" id="closeErrorBtn">✕</button>
            </div>
          `;
          const closeBtn = errorBox.querySelector("#closeErrorBtn");
          if (closeBtn) {
            closeBtn.addEventListener("click", () => {
              this._error = null;
              errorBox.innerHTML = "";
            });
          }
        } else {
          errorBox.innerHTML = "";
        }
      }

      if (this._loading) {
        if (askBtn) askBtn.disabled = true;
        answerBox.innerHTML = `
          <div class="garmin-loading-spinner">
            <div class="garmin-spinner"></div>
            <span>Analyzing your Garmin health history & formulating response...</span>
          </div>
        `;
        return;
      }

      if (askBtn) askBtn.disabled = false;

      // Check if direct response is available
      if (this._directAnswer && this._directAnswer.answer) {
        const fullAnswer = this._directAnswer.answer;
        const question = this._directAnswer.question || "";
        answerBox.innerHTML = `
          ${question ? `<div class="garmin-q-banner"><div><strong>Q:</strong> ${question}</div></div>` : ""}
          <div class="garmin-answer-text">${renderMarkdown(fullAnswer)}</div>
        `;
        return;
      }

      const answerState = this._hass.states ? this._hass.states[this._config.answer_entity] : undefined;
      if (!answerState) {
        answerBox.innerHTML = `<div class="garmin-empty-state">Entity ${this._config.answer_entity} not found.</div>`;
        return;
      }

      const fullAnswer = answerState.attributes?.full_answer || (answerState.state !== "unavailable" && answerState.state !== "unknown" ? answerState.state : "");
      const question = answerState.attributes?.question || "";
      const timestamp = answerState.attributes?.timestamp || "";

      if (!fullAnswer || fullAnswer === "No question asked yet" || fullAnswer === "unavailable") {
        answerBox.innerHTML = `
          <div class="garmin-empty-state">
            Type a question above and click "Ask" to consult your AI Health Coach grounded in your Garmin metrics.
          </div>
        `;
        return;
      }

      let timeFormatted = "";
      if (timestamp) {
        try {
          const d = new Date(timestamp);
          timeFormatted = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + ", " + d.toLocaleDateString();
        } catch (_) {
          timeFormatted = timestamp;
        }
      }

      const renderedAnswer = renderMarkdown(fullAnswer);

      answerBox.innerHTML = `
        ${question ? `
          <div class="garmin-q-banner">
            <div><strong>Q:</strong> ${question}</div>
            ${timeFormatted ? `<div class="garmin-meta-time">${timeFormatted}</div>` : ""}
          </div>
        ` : ""}
        <div class="garmin-answer-text">${renderedAnswer}</div>
      `;
    }
  }

  /**
   * 2. Garmin AI Health Report Card
   */
  class GarminHAIReportCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._viewMode = "long"; // "long" | "short" | "dynamic"
      this._loading = false;
      this._error = null;
      this._initialized = false;
      this._config = {
        title: "Garmin AI Health Report",
        report_entity: "sensor.garmin_ai_health_report_long",
        short_report_entity: "sensor.garmin_ai_health_report_short",
        selected_report_entity: "sensor.garmin_ai_selected_report",
        generate_button_entity: "button.garmin_ai_generate_report",
        last_update_entity: "sensor.garmin_ai_last_update",
        default_view: "long",
      };
    }

    setConfig(config) {
      this._config = Object.assign(
        {
          title: "Garmin AI Health Report",
          report_entity: "sensor.garmin_ai_health_report_long",
          short_report_entity: "sensor.garmin_ai_health_report_short",
          selected_report_entity: "sensor.garmin_ai_selected_report",
          generate_button_entity: "button.garmin_ai_generate_report",
          last_update_entity: "sensor.garmin_ai_last_update",
          default_view: "long",
        },
        config || {}
      );
      this._viewMode = this._config.default_view || "long";
      if (!this._initialized) {
        this._render();
        this._initialized = true;
      }
      this._updateContent();
    }

    set hass(hass) {
      this._hass = hass;
      try {
        this._updateContent();
      } catch (err) {
        console.error("Error in GarminHAIReportCard set hass:", err);
      }
    }

    static getStubConfig() {
      return {
        type: "custom:garmin-ha-ai-report-card",
        title: "Garmin AI Health Report",
        report_entity: "sensor.garmin_ai_health_report_long",
        short_report_entity: "sensor.garmin_ai_health_report_short",
        selected_report_entity: "sensor.garmin_ai_selected_report",
        generate_button_entity: "button.garmin_ai_generate_report",
        last_update_entity: "sensor.garmin_ai_last_update",
      };
    }

    getCardSize() {
      return 6;
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>${BASE_STYLES}</style>
        <ha-card>
          <div class="garmin-card-header">
            <div class="garmin-card-title">
              <ha-icon icon="mdi:file-document-outline"></ha-icon>
              <span>${this._config.title}</span>
            </div>
            <button class="garmin-btn garmin-btn-secondary" id="refreshBtn">
              <ha-icon icon="mdi:refresh"></ha-icon>
              <span>Regenerate</span>
            </button>
          </div>
          <div id="reportErrorBox"></div>
          <div class="garmin-tab-bar">
            <button class="garmin-tab-btn ${this._viewMode === "long" ? "active" : ""}" data-mode="long">Full Report</button>
            <button class="garmin-tab-btn ${this._viewMode === "short" ? "active" : ""}" data-mode="short">Daily Summary</button>
            <button class="garmin-tab-btn ${this._viewMode === "dynamic" ? "active" : ""}" data-mode="dynamic">Dynamic View</button>
          </div>
          <div class="garmin-content-box" id="reportBox">
            <div class="garmin-empty-state">Loading report...</div>
          </div>
        </ha-card>
      `;

      const refreshBtn = this.shadowRoot.getElementById("refreshBtn");
      if (refreshBtn) {
        refreshBtn.addEventListener("click", () => this._refreshReport());
      }

      const tabs = this.shadowRoot.querySelectorAll(".garmin-tab-btn");
      tabs.forEach((tab) => {
        tab.addEventListener("click", (e) => {
          this._viewMode = e.currentTarget.dataset.mode || "long";
          tabs.forEach((t) => t.classList.toggle("active", t === e.currentTarget));
          this._updateContent();
        });
      });
    }

    async _refreshReport() {
      if (!this._hass) return;
      this._loading = true;
      this._error = null;
      this._updateContent();

      try {
        await this._hass.callService("garmin_ha_ai", "generate_report", {});
        this._error = null;
      } catch (err) {
        console.error("Garmin AI Generate Report Error:", err);
        let errorMsg = err?.message || String(err);
        if (errorMsg.includes("503") || errorMsg.includes("UNAVAILABLE") || errorMsg.includes("high demand")) {
          errorMsg = "AI model is currently experiencing high demand (503 Service Unavailable). Please try again in a moment.";
        } else if (errorMsg.includes("429") || errorMsg.includes("quota")) {
          errorMsg = "AI API quota or rate limit exceeded (429).";
        }
        this._error = errorMsg;
      } finally {
        setTimeout(() => {
          this._loading = false;
          this._updateContent();
        }, 1500);
      }
    }

    _updateContent() {
      if (!this.shadowRoot || !this._hass || !this._config) return;

      const reportBox = this.shadowRoot.getElementById("reportBox");
      const errorBox = this.shadowRoot.getElementById("reportErrorBox");
      if (!reportBox) return;

      // Render Error Banner
      if (errorBox) {
        if (this._error) {
          errorBox.innerHTML = `
            <div class="garmin-error-banner">
              <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
              <div class="garmin-error-text"><strong>AI Notice:</strong> ${this._error}</div>
              <button class="garmin-error-close" id="closeReportErrorBtn">✕</button>
            </div>
          `;
          const closeBtn = errorBox.querySelector("#closeReportErrorBtn");
          if (closeBtn) {
            closeBtn.addEventListener("click", () => {
              this._error = null;
              errorBox.innerHTML = "";
            });
          }
        } else {
          errorBox.innerHTML = "";
        }
      }

      if (this._loading) {
        reportBox.innerHTML = `
          <div class="garmin-loading-spinner">
            <div class="garmin-spinner"></div>
            <span>Generating fresh AI Health Report...</span>
          </div>
        `;
        return;
      }

      let contentText = "";
      let lastUpdated = "";

      if (this._config.last_update_entity && this._hass.states && this._hass.states[this._config.last_update_entity]) {
        const updateState = this._hass.states[this._config.last_update_entity];
        if (updateState.state && updateState.state !== "unavailable" && updateState.state !== "unknown") {
          try {
            const d = new Date(updateState.state);
            lastUpdated = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + ", " + d.toLocaleDateString();
          } catch (_) {
            lastUpdated = updateState.state;
          }
        }
      }

      if (this._viewMode === "short") {
        const shortState = this._hass.states ? this._hass.states[this._config.short_report_entity] : undefined;
        contentText = shortState && shortState.state !== "unavailable" && shortState.state !== "unknown" ? shortState.state : "";
      } else if (this._viewMode === "dynamic") {
        const dynState = this._hass.states ? this._hass.states[this._config.selected_report_entity] : undefined;
        contentText = dynState?.attributes?.report_text || (dynState?.state !== "unavailable" && dynState?.state !== "unknown" ? dynState.state : "");
      } else {
        const longState = this._hass.states ? this._hass.states[this._config.report_entity] : undefined;
        contentText = longState?.attributes?.full_report || longState?.attributes?.short_summary || "";
      }

      if (!contentText || contentText === "No report generated yet" || contentText === "unavailable") {
        reportBox.innerHTML = `
          <div class="garmin-empty-state">
            No health report generated yet. Click "Regenerate" to generate a personalized briefing.
          </div>
        `;
        return;
      }

      reportBox.innerHTML = `
        ${lastUpdated ? `<div class="garmin-meta-time" style="margin-bottom: 8px;"><strong>Updated:</strong> ${lastUpdated}</div>` : ""}
        <div class="garmin-report-body">${renderMarkdown(contentText)}</div>
      `;
    }
  }

  /**
   * 3. Garmin AI Health Overview Card (All-In-One Glance + Q&A + Report)
   */
  class GarminHAIOverviewCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._activeTab = "qa"; // "qa" | "report"
      this._qaLoading = false;
      this._qaError = null;
      this._directAnswer = null;
      this._initialized = false;
      this._config = {
        title: "Garmin AI Health Coach",
        steps_entity: "sensor.garmin_steps",
        sleep_entity: "sensor.garmin_sleep_score",
        battery_entity: "sensor.garmin_body_battery",
        stress_entity: "sensor.garmin_stress_level",
        hr_entity: "sensor.garmin_resting_heart_rate",
        short_report_entity: "sensor.garmin_ai_health_report_short",
        long_report_entity: "sensor.garmin_ai_health_report_long",
        answer_entity: "sensor.garmin_ai_last_answer",
      };
    }

    setConfig(config) {
      this._config = Object.assign(
        {
          title: "Garmin AI Health Coach",
          steps_entity: "sensor.garmin_steps",
          sleep_entity: "sensor.garmin_sleep_score",
          battery_entity: "sensor.garmin_body_battery",
          stress_entity: "sensor.garmin_stress_level",
          hr_entity: "sensor.garmin_resting_heart_rate",
          short_report_entity: "sensor.garmin_ai_health_report_short",
          long_report_entity: "sensor.garmin_ai_health_report_long",
          answer_entity: "sensor.garmin_ai_last_answer",
        },
        config || {}
      );
      if (!this._initialized) {
        this._render();
        this._initialized = true;
      }
      this._updateContent();
    }

    set hass(hass) {
      this._hass = hass;
      try {
        this._updateContent();
      } catch (err) {
        console.error("Error in GarminHAIOverviewCard set hass:", err);
      }
    }

    static getStubConfig() {
      return {
        type: "custom:garmin-ha-ai-overview-card",
        title: "Garmin AI Health Coach",
      };
    }

    getCardSize() {
      return 6;
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>${BASE_STYLES}</style>
        <ha-card>
          <div class="garmin-card-header">
            <div class="garmin-card-title">
              <ha-icon icon="mdi:heart-pulse"></ha-icon>
              <span>${this._config.title}</span>
            </div>
          </div>
          <div class="garmin-glance-bar" id="glanceBar"></div>
          <div class="garmin-focus-banner" id="focusBanner"></div>
          <div id="overviewErrorBox"></div>
          <div class="garmin-tab-bar">
            <button class="garmin-tab-btn active" data-tab="qa">💬 Ask Coach</button>
            <button class="garmin-tab-btn" data-tab="report">📋 Full Daily Report</button>
          </div>
          <div id="tabContainer">
            <div id="qaSection">
              <div class="garmin-input-container">
                <textarea class="garmin-textarea" placeholder="Ask your coach anything about today's readiness..." rows="2"></textarea>
                <button class="garmin-btn" id="askBtn">
                  <ha-icon icon="mdi:send"></ha-icon>
                  <span>Ask</span>
                </button>
              </div>
              <div class="garmin-content-box" id="overviewAnswerBox"></div>
            </div>
            <div id="reportSection" style="display: none;">
              <div class="garmin-content-box" id="overviewReportBox"></div>
            </div>
          </div>
        </ha-card>
      `;

      const askBtn = this.shadowRoot.getElementById("askBtn");
      const textarea = this.shadowRoot.querySelector(".garmin-textarea");
      if (askBtn && textarea) {
        askBtn.addEventListener("click", () => this._submitQuestion());
        textarea.addEventListener("keydown", (e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
            e.preventDefault();
            this._submitQuestion();
          }
        });
      }

      const tabs = this.shadowRoot.querySelectorAll(".garmin-tab-btn");
      tabs.forEach((tab) => {
        tab.addEventListener("click", (e) => {
          this._activeTab = e.currentTarget.dataset.tab;
          tabs.forEach((t) => t.classList.toggle("active", t === e.currentTarget));
          const qaSec = this.shadowRoot.getElementById("qaSection");
          const repSec = this.shadowRoot.getElementById("reportSection");
          if (qaSec && repSec) {
            qaSec.style.display = this._activeTab === "qa" ? "block" : "none";
            repSec.style.display = this._activeTab === "report" ? "block" : "none";
          }
        });
      });
    }

    async _submitQuestion() {
      const textarea = this.shadowRoot ? this.shadowRoot.querySelector(".garmin-textarea") : null;
      const question = (textarea?.value || "").trim();
      if (!question || !this._hass) return;

      this._qaLoading = true;
      this._qaError = null;
      this._updateContent();

      try {
        const response = await this._hass.callService(
          "garmin_ha_ai",
          "ask_question",
          { question: question },
          undefined,
          true,
          true
        );
        if (textarea) textarea.value = "";
        this._qaLoading = false;
        this._qaError = null;
        if (response && response.response && response.response.answer) {
          this._directAnswer = response.response;
        }
        this._updateContent();
      } catch (err) {
        console.error("Ask error in Overview Card:", err);
        let errorMsg = err?.message || String(err);
        if (errorMsg.includes("503") || errorMsg.includes("UNAVAILABLE") || errorMsg.includes("high demand")) {
          errorMsg = "AI model is currently experiencing high demand (503 Service Unavailable). Please try again in a moment.";
        } else if (errorMsg.includes("429") || errorMsg.includes("quota")) {
          errorMsg = "AI API quota or rate limit exceeded (429).";
        }
        this._qaError = errorMsg;
        this._qaLoading = false;
        this._updateContent();
      }
    }

    _updateContent() {
      if (!this.shadowRoot || !this._hass || !this._config) return;

      const glanceBar = this.shadowRoot.getElementById("glanceBar");
      const focusBanner = this.shadowRoot.getElementById("focusBanner");
      const errorBox = this.shadowRoot.getElementById("overviewErrorBox");
      const answerBox = this.shadowRoot.getElementById("overviewAnswerBox");
      const reportBox = this.shadowRoot.getElementById("overviewReportBox");

      // Update Error Banner
      if (errorBox) {
        if (this._qaError) {
          errorBox.innerHTML = `
            <div class="garmin-error-banner">
              <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
              <div class="garmin-error-text"><strong>AI Notice:</strong> ${this._qaError}</div>
              <button class="garmin-error-close" id="closeOverviewErrorBtn">✕</button>
            </div>
          `;
          const closeBtn = errorBox.querySelector("#closeOverviewErrorBtn");
          if (closeBtn) {
            closeBtn.addEventListener("click", () => {
              this._qaError = null;
              errorBox.innerHTML = "";
            });
          }
        } else {
          errorBox.innerHTML = "";
        }
      }

      // Update Glance Metrics
      if (glanceBar) {
        const getVal = (entityId, fallback = "--") => {
          if (!this._hass || !this._hass.states) return fallback;
          const s = this._hass.states[entityId];
          return s && s.state !== "unavailable" && s.state !== "unknown" ? s.state : fallback;
        };

        glanceBar.innerHTML = `
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Sleep</div>
            <div class="garmin-metric-val">${getVal(this._config.sleep_entity)}%</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Battery</div>
            <div class="garmin-metric-val">${getVal(this._config.battery_entity)}%</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Stress</div>
            <div class="garmin-metric-val">${getVal(this._config.stress_entity)}</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Rest HR</div>
            <div class="garmin-metric-val">${getVal(this._config.hr_entity)}</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Steps</div>
            <div class="garmin-metric-val">${getVal(this._config.steps_entity)}</div>
          </div>
        `;
      }

      // Update Focus Banner
      if (focusBanner) {
        const shortState = this._hass.states ? this._hass.states[this._config.short_report_entity] : undefined;
        const focusText = shortState && shortState.state !== "unavailable" && shortState.state !== "unknown" ? shortState.state : "Ready for today's workout and recovery guidance.";
        focusBanner.innerHTML = `<strong>💡 Today's Focus:</strong> ${focusText}`;
      }

      // Update Q&A Answer View
      if (answerBox) {
        if (this._qaLoading) {
          answerBox.innerHTML = `
            <div class="garmin-loading-spinner">
              <div class="garmin-spinner"></div>
              <span>Analyzing health history & asking AI coach...</span>
            </div>
          `;
        } else if (this._directAnswer && this._directAnswer.answer) {
          const fullAnswer = this._directAnswer.answer;
          const question = this._directAnswer.question || "";
          answerBox.innerHTML = `
            ${question ? `<div class="garmin-q-banner"><strong>Q:</strong> ${question}</div>` : ""}
            <div>${renderMarkdown(fullAnswer)}</div>
          `;
        } else {
          const ansState = this._hass.states ? this._hass.states[this._config.answer_entity] : undefined;
          const fullAnswer = ansState?.attributes?.full_answer || (ansState?.state !== "unavailable" && ansState?.state !== "unknown" ? ansState?.state : "");
          const question = ansState?.attributes?.question || "";
          if (!fullAnswer || fullAnswer === "No question asked yet" || fullAnswer === "unavailable") {
            answerBox.innerHTML = `<div class="garmin-empty-state">Type a coaching question above.</div>`;
          } else {
            answerBox.innerHTML = `
              ${question ? `<div class="garmin-q-banner"><strong>Q:</strong> ${question}</div>` : ""}
              <div>${renderMarkdown(fullAnswer)}</div>
            `;
          }
        }
      }

      // Update Report View
      if (reportBox) {
        const repState = this._hass.states ? this._hass.states[this._config.long_report_entity] : undefined;
        const fullRep = repState?.attributes?.full_report || repState?.attributes?.short_summary || (repState?.state !== "unavailable" && repState?.state !== "unknown" ? repState?.state : "");
        if (!fullRep || fullRep === "No report generated yet" || fullRep === "unavailable") {
          reportBox.innerHTML = `<div class="garmin-empty-state">No full report generated yet.</div>`;
        } else {
          reportBox.innerHTML = `<div>${renderMarkdown(fullRep)}</div>`;
        }
      }
    }
  }

  // Register Custom Elements with the browser
  if (!customElements.get("garmin-ha-ai-qa-card")) {
    customElements.define("garmin-ha-ai-qa-card", GarminHAIQAQuestionCard);
  }
  if (!customElements.get("garmin-ha-ai-report-card")) {
    customElements.define("garmin-ha-ai-report-card", GarminHAIReportCard);
  }
  if (!customElements.get("garmin-ha-ai-overview-card")) {
    customElements.define("garmin-ha-ai-overview-card", GarminHAIOverviewCard);
  }

  // Register Cards with Home Assistant Lovelace Card Picker (window.customCards)
  window.customCards = window.customCards || [];

  const cardsToRegister = [
    {
      type: "garmin-ha-ai-qa-card",
      name: "Garmin AI Coach Q&A",
      description: "Interactive Q&A text field, ask button, and live formatted coach answer view.",
      preview: true,
      documentationURL: "https://github.com/j333c/garmin-ha-ai",
    },
    {
      type: "garmin-ha-ai-report-card",
      name: "Garmin AI Health Report",
      description: "Detailed AI health and recovery report with on-demand refresh and formatted Markdown view.",
      preview: true,
      documentationURL: "https://github.com/j333c/garmin-ha-ai",
    },
    {
      type: "garmin-ha-ai-overview-card",
      name: "Garmin AI Health Overview",
      description: "Complete Garmin recovery glance metrics, daily coaching focus, interactive Q&A, and full reports.",
      preview: true,
      documentationURL: "https://github.com/j333c/garmin-ha-ai",
    },
  ];

  for (const card of cardsToRegister) {
    if (!window.customCards.some((c) => c.type === card.type)) {
      window.customCards.push(card);
    }
  }

  console.info(
    "%c GARMIN-HA-AI %c Custom Lovelace Cards Loaded ",
    "color: white; background: #03a9f4; font-weight: 700; border-radius: 3px 0 0 3px;",
    "color: #03a9f4; background: rgba(3, 169, 244, 0.1); font-weight: 700; border-radius: 0 3px 3px 0;"
  );
})();
