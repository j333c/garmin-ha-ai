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
      html = html.replace(/\*\*\*(.*?)\*\*\*/g, "<strong><em>$1</em></strong>");
      html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/__(.*?)__/g, "<strong>$1</strong>");
      html = html.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
      html = html.replace(/_([^_\n]+)_/g, "<em>$1</em>");

      // 7. GitHub-style alerts & blockquotes
      html = html.replace(/^&gt;\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$/gm, function (_, type, text) {
        const cls = type.toLowerCase();
        return `<div class="garmin-alert garmin-alert-${cls}"><strong>${type}:</strong> ${text}</div>`;
      });
      html = html.replace(/^&gt;\s*(.*)$/gm, '<blockquote class="garmin-quote">$1</blockquote>');

      // 8. Markdown Links [text](url)
      html = html.replace(
        /\[([^\]]+)\]\(([^)\s]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer" class="garmin-link">$1</a>'
      );

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
      return `<p class="garmin-p">${String(md)
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\n/g, "<br/>")}</p>`;
    }
  }

  /**
   * Smart entity finder for Home Assistant states.
   * Finds matching entities by keyword/pattern across integration naming variants,
   * returning an existing entity ID or empty string fallback so the entity picker
   * does not show "Unknown entity selected".
   */
  function smartFindEntity(hass, patterns, domain = "sensor") {
    if (!hass || !hass.states) return "";
    const prefix = `${domain}.`;
    const entityIds = Object.keys(hass.states).filter((id) => id.startsWith(prefix));

    for (const pattern of patterns) {
      // 1. Exact match
      if (hass.states[pattern]) return pattern;
      if (hass.states[`${prefix}${pattern}`]) return `${prefix}${pattern}`;

      // 2. Substring search in domain entity IDs
      const match = entityIds.find((id) => {
        const afterDomain = id.slice(prefix.length);
        return afterDomain === pattern || afterDomain.includes(pattern);
      });
      if (match) return match;
    }

    return "";
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
   * Base Card Class providing common lifecycle, styling, error banners, and reactivity.
   */
  class GarminCardBase extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._hass = null;
      this._config = null;
      this._error = null;
      this._initialized = false;
    }

    getCardSize() {
      return 4;
    }

    _getDefaultConfig() {
      return {};
    }

    setConfig(config) {
      if (!config) {
        throw new Error("Invalid card configuration");
      }
      this._config = Object.assign({}, this._getDefaultConfig(), config);
      if (!this._initialized) {
        this._render();
        this._initialized = true;
      } else {
        this._updateTitle();
      }
      this._updateContent();
    }

    set hass(hass) {
      this._hass = hass;
      if (this._initialized) {
        this._updateContent();
      }
    }

    _updateTitle() {
      if (!this.shadowRoot || !this._config) return;
      const titleSpan = this.shadowRoot.querySelector(".garmin-card-title span");
      if (titleSpan && this._config.title) {
        titleSpan.textContent = this._config.title;
      }
    }

    _renderErrorBanner(containerId, errorText, onClose) {
      if (!this.shadowRoot) return;
      const box = this.shadowRoot.getElementById(containerId);
      if (!box) return;

      if (!errorText) {
        box.innerHTML = "";
        return;
      }

      box.innerHTML = `
        <div class="garmin-error-banner">
          <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
          <div class="garmin-error-text"><strong>AI Notice:</strong> ${errorText}</div>
          <button class="garmin-error-close" id="${containerId}_closeBtn">✕</button>
        </div>
      `;

      const closeBtn = box.querySelector(`#${containerId}_closeBtn`);
      if (closeBtn) {
        closeBtn.addEventListener("click", () => {
          box.innerHTML = "";
          if (onClose) onClose();
        });
      }
    }

    _getEntityState(entityId, fallback = "--") {
      if (!this._hass || !this._hass.states || !entityId) return fallback;
      const s = this._hass.states[entityId];
      return s && s.state !== "unavailable" && s.state !== "unknown" ? s.state : fallback;
    }

    _getEntityAttribute(entityId, attrName, fallback = null) {
      if (!this._hass || !this._hass.states || !entityId) return fallback;
      const s = this._hass.states[entityId];
      return s && s.attributes && s.attributes[attrName] !== undefined ? s.attributes[attrName] : fallback;
    }
  }

  /**
   * 1. Garmin AI Q&A Coach Card
   */
  class GarminHAIQAQuestionCard extends GarminCardBase {
    constructor() {
      super();
      this._loading = false;
      this._directAnswer = null;
      this._lastAnswerTimestamp = null;
    }

    _getDefaultConfig() {
      return {
        title: "Garmin AI Coach Q&A",
        question_entity: "",
        button_entity: "",
        answer_entity: "",
      };
    }

    static getConfigElement() {
      return document.createElement("garmin-ha-ai-qa-card-editor");
    }

    static getStubConfig(hass) {
      return {
        title: "Garmin AI Coach Q&A",
        question_entity: smartFindEntity(hass, ["garmin_ai_question", "ai_question", "question"], "text"),
        button_entity: smartFindEntity(hass, ["garmin_ai_ask_question", "ask_question", "ask"], "button"),
        answer_entity: smartFindEntity(hass, ["garmin_ai_last_answer", "ai_last_answer", "last_answer"], "sensor"),
      };
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._config) return;

      try {
        const answerEnt = this._config.answer_entity || smartFindEntity(hass, ["garmin_ai_last_answer", "ai_last_answer", "last_answer"], "sensor");
        const currentTimestamp = this._getEntityAttribute(answerEnt, "timestamp", null);
        if (this._loading && currentTimestamp && currentTimestamp !== this._lastAnswerTimestamp) {
          this._loading = false;
          this._error = null;
          this._directAnswer = null;
        }
        this._lastAnswerTimestamp = currentTimestamp;
        if (this._initialized) {
          this._updateContent();
        }
      } catch (err) {
        console.error("Error in GarminHAIQAQuestionCard set hass:", err);
      }
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>${BASE_STYLES}</style>
        <ha-card>
          <div class="garmin-card-header">
            <div class="garmin-card-title">
              <ha-icon icon="mdi:chat-question"></ha-icon>
              <span>${this._config.title || "Garmin AI Coach Q&A"}</span>
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
      if (!this.shadowRoot || !this._config) return;

      const answerBox = this.shadowRoot.getElementById("answerBox");
      const askBtn = this.shadowRoot.getElementById("askBtn");
      if (!answerBox) return;

      this._renderErrorBanner("errorBox", this._error, () => {
        this._error = null;
      });

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

      if (!this._hass) {
        answerBox.innerHTML = `
          <div class="garmin-empty-state">
            Type a question above and click "Ask" to consult your AI Health Coach.
          </div>
        `;
        return;
      }

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

      const answerEnt = this._config.answer_entity || smartFindEntity(this._hass, ["garmin_ai_last_answer", "ai_last_answer", "last_answer"], "sensor");
      const answerState = answerEnt && this._hass.states ? this._hass.states[answerEnt] : undefined;

      if (!answerState) {
        answerBox.innerHTML = `<div class="garmin-empty-state">Type a question above and click "Ask" to consult your AI Health Coach.</div>`;
        return;
      }

      const fullAnswer =
        answerState.attributes?.full_answer ||
        (answerState.state !== "unavailable" && answerState.state !== "unknown" ? answerState.state : "");
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
          timeFormatted =
            d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + ", " + d.toLocaleDateString();
        } catch (_) {
          timeFormatted = timestamp;
        }
      }

      answerBox.innerHTML = `
        ${
          question
            ? `
          <div class="garmin-q-banner">
            <div><strong>Q:</strong> ${question}</div>
            ${timeFormatted ? `<div class="garmin-meta-time">${timeFormatted}</div>` : ""}
          </div>
        `
            : ""
        }
        <div class="garmin-answer-text">${renderMarkdown(fullAnswer)}</div>
      `;
    }
  }

  /**
   * 2. Garmin AI Health Report Card
   */
  class GarminHAIReportCard extends GarminCardBase {
    constructor() {
      super();
      this._viewMode = "long"; // "long" | "short" | "dynamic"
      this._loading = false;
    }

    getCardSize() {
      return 6;
    }

    _getDefaultConfig() {
      return {
        title: "Garmin AI Health Report",
        report_entity: "",
        short_report_entity: "",
        selected_report_entity: "",
        generate_button_entity: "",
        last_update_entity: "",
        default_view: "long",
      };
    }

    static getConfigElement() {
      return document.createElement("garmin-ha-ai-report-card-editor");
    }

    static getStubConfig(hass) {
      return {
        title: "Garmin AI Health Report",
        report_entity: smartFindEntity(hass, ["garmin_ai_health_report_long", "health_report_long", "report_long"], "sensor"),
        short_report_entity: smartFindEntity(hass, ["garmin_ai_health_report_short", "health_report_short", "report_short"], "sensor"),
        selected_report_entity: smartFindEntity(hass, ["garmin_ai_selected_report", "ai_selected_report", "selected_report"], "sensor"),
        generate_button_entity: smartFindEntity(hass, ["garmin_ai_generate_report", "generate_report", "generate"], "button"),
        last_update_entity: smartFindEntity(hass, ["garmin_ai_last_update", "ai_last_update", "last_update"], "sensor"),
        default_view: "long",
      };
    }

    setConfig(config) {
      super.setConfig(config);
      if (this._config && this._config.default_view) {
        this._viewMode = this._config.default_view;
      }
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>${BASE_STYLES}</style>
        <ha-card>
          <div class="garmin-card-header">
            <div class="garmin-card-title">
              <ha-icon icon="mdi:file-document-outline"></ha-icon>
              <span>${this._config.title || "Garmin AI Health Report"}</span>
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
            <div class="garmin-empty-state">
              No health report generated yet. Click "Regenerate" to generate a personalized briefing.
            </div>
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
      if (!this.shadowRoot || !this._config) return;

      const reportBox = this.shadowRoot.getElementById("reportBox");
      if (!reportBox) return;

      this._renderErrorBanner("reportErrorBox", this._error, () => {
        this._error = null;
      });

      if (this._loading) {
        reportBox.innerHTML = `
          <div class="garmin-loading-spinner">
            <div class="garmin-spinner"></div>
            <span>Generating fresh AI Health Report...</span>
          </div>
        `;
        return;
      }

      if (!this._hass) {
        reportBox.innerHTML = `
          <div class="garmin-empty-state">
            No health report generated yet. Click "Regenerate" to generate a personalized briefing.
          </div>
        `;
        return;
      }

      let contentText = "";
      let lastUpdated = "";

      const updateEnt = this._config.last_update_entity || smartFindEntity(this._hass, ["garmin_ai_last_update", "ai_last_update", "last_update"], "sensor");
      if (updateEnt && this._hass.states && this._hass.states[updateEnt]) {
        const updateState = this._hass.states[updateEnt];
        if (updateState.state && updateState.state !== "unavailable" && updateState.state !== "unknown") {
          try {
            const d = new Date(updateState.state);
            lastUpdated =
              d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + ", " + d.toLocaleDateString();
          } catch (_) {
            lastUpdated = updateState.state;
          }
        }
      }

      if (this._viewMode === "short") {
        const shortEnt = this._config.short_report_entity || smartFindEntity(this._hass, ["garmin_ai_health_report_short", "health_report_short", "report_short"], "sensor");
        const shortState = shortEnt && this._hass.states ? this._hass.states[shortEnt] : undefined;
        contentText =
          shortState && shortState.state !== "unavailable" && shortState.state !== "unknown" ? shortState.state : "";
      } else if (this._viewMode === "dynamic") {
        const dynEnt = this._config.selected_report_entity || smartFindEntity(this._hass, ["garmin_ai_selected_report", "ai_selected_report", "selected_report"], "sensor");
        const dynState = dynEnt && this._hass.states ? this._hass.states[dynEnt] : undefined;
        contentText =
          dynState?.attributes?.report_text ||
          (dynState?.state !== "unavailable" && dynState?.state !== "unknown" ? dynState.state : "");
      } else {
        const longEnt = this._config.report_entity || smartFindEntity(this._hass, ["garmin_ai_health_report_long", "health_report_long", "report_long"], "sensor");
        const longState = longEnt && this._hass.states ? this._hass.states[longEnt] : undefined;
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
  class GarminHAIOverviewCard extends GarminCardBase {
    constructor() {
      super();
      this._activeTab = "qa"; // "qa" | "report"
      this._qaLoading = false;
      this._qaError = null;
      this._directAnswer = null;
    }

    getCardSize() {
      return 6;
    }

    _getDefaultConfig() {
      return {
        title: "Garmin AI Health Coach",
        sleep_entity: "",
        battery_entity: "",
        stress_entity: "",
        hr_entity: "",
        steps_entity: "",
        short_report_entity: "",
        long_report_entity: "",
        answer_entity: "",
      };
    }

    static getConfigElement() {
      return document.createElement("garmin-ha-ai-overview-card-editor");
    }

    static getStubConfig(hass) {
      return {
        title: "Garmin AI Health Coach",
        sleep_entity: smartFindEntity(hass, ["garmin_sleep_score", "sleep_score", "sleep"], "sensor"),
        battery_entity: smartFindEntity(hass, ["garmin_body_battery", "body_battery"], "sensor"),
        stress_entity: smartFindEntity(hass, ["garmin_stress_level", "stress_level", "stress"], "sensor"),
        hr_entity: smartFindEntity(hass, ["garmin_resting_heart_rate", "resting_heart_rate", "resting_hr", "resting_heart"], "sensor"),
        steps_entity: smartFindEntity(hass, ["garmin_steps", "daily_steps", "steps", "total_steps"], "sensor"),
        short_report_entity: smartFindEntity(hass, ["garmin_ai_health_report_short", "health_report_short", "report_short"], "sensor"),
        long_report_entity: smartFindEntity(hass, ["garmin_ai_health_report_long", "health_report_long", "report_long"], "sensor"),
        answer_entity: smartFindEntity(hass, ["garmin_ai_last_answer", "ai_last_answer", "last_answer"], "sensor"),
      };
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>${BASE_STYLES}</style>
        <ha-card>
          <div class="garmin-card-header">
            <div class="garmin-card-title">
              <ha-icon icon="mdi:heart-pulse"></ha-icon>
              <span>${this._config.title || "Garmin AI Health Coach"}</span>
            </div>
          </div>
          <div class="garmin-glance-bar" id="glanceBar">
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Sleep</div><div class="garmin-metric-val">--%</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Battery</div><div class="garmin-metric-val">--%</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Stress</div><div class="garmin-metric-val">--</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Rest HR</div><div class="garmin-metric-val">--</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Steps</div><div class="garmin-metric-val">--</div></div>
          </div>
          <div class="garmin-focus-banner" id="focusBanner"><strong>💡 Today's Focus:</strong> Ready for today's workout and recovery guidance.</div>
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
              <div class="garmin-content-box" id="overviewAnswerBox">
                <div class="garmin-empty-state">Type a coaching question above.</div>
              </div>
            </div>
            <div id="reportSection" style="display: none;">
              <div class="garmin-content-box" id="overviewReportBox">
                <div class="garmin-empty-state">No full report generated yet.</div>
              </div>
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
      if (!this.shadowRoot || !this._config) return;

      const glanceBar = this.shadowRoot.getElementById("glanceBar");
      const focusBanner = this.shadowRoot.getElementById("focusBanner");
      const answerBox = this.shadowRoot.getElementById("overviewAnswerBox");
      const reportBox = this.shadowRoot.getElementById("overviewReportBox");

      this._renderErrorBanner("overviewErrorBox", this._qaError, () => {
        this._qaError = null;
      });

      if (!this._hass) {
        if (glanceBar) {
          glanceBar.innerHTML = `
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Sleep</div><div class="garmin-metric-val">--%</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Battery</div><div class="garmin-metric-val">--%</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Stress</div><div class="garmin-metric-val">--</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Rest HR</div><div class="garmin-metric-val">--</div></div>
            <div class="garmin-metric-pill"><div class="garmin-metric-label">Steps</div><div class="garmin-metric-val">--</div></div>
          `;
        }
        if (focusBanner) {
          focusBanner.innerHTML = `<strong>💡 Today's Focus:</strong> Ready for today's workout and recovery guidance.`;
        }
        if (answerBox) {
          answerBox.innerHTML = `<div class="garmin-empty-state">Type a coaching question above.</div>`;
        }
        if (reportBox) {
          reportBox.innerHTML = `<div class="garmin-empty-state">No full report generated yet.</div>`;
        }
        return;
      }

      // Resolve entity IDs (either configured or auto-detected)
      const sleepEnt = this._config.sleep_entity || smartFindEntity(this._hass, ["garmin_sleep_score", "sleep_score", "sleep"], "sensor");
      const batteryEnt = this._config.battery_entity || smartFindEntity(this._hass, ["garmin_body_battery", "body_battery"], "sensor");
      const stressEnt = this._config.stress_entity || smartFindEntity(this._hass, ["garmin_stress_level", "stress_level", "stress"], "sensor");
      const hrEnt = this._config.hr_entity || smartFindEntity(this._hass, ["garmin_resting_heart_rate", "resting_heart_rate", "resting_hr", "resting_heart"], "sensor");
      const stepsEnt = this._config.steps_entity || smartFindEntity(this._hass, ["garmin_steps", "daily_steps", "steps", "total_steps"], "sensor");
      const shortEnt = this._config.short_report_entity || smartFindEntity(this._hass, ["garmin_ai_health_report_short", "health_report_short", "report_short"], "sensor");
      const longEnt = this._config.long_report_entity || smartFindEntity(this._hass, ["garmin_ai_health_report_long", "health_report_long", "report_long"], "sensor");
      const answerEnt = this._config.answer_entity || smartFindEntity(this._hass, ["garmin_ai_last_answer", "ai_last_answer", "last_answer"], "sensor");

      // Update Glance Metrics
      if (glanceBar) {
        const sleepVal = this._getEntityState(sleepEnt);
        const battVal = this._getEntityState(batteryEnt);
        const stressVal = this._getEntityState(stressEnt);
        const hrVal = this._getEntityState(hrEnt);
        const stepsVal = this._getEntityState(stepsEnt);

        glanceBar.innerHTML = `
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Sleep</div>
            <div class="garmin-metric-val">${sleepVal !== "--" ? `${sleepVal}%` : "--"}</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Battery</div>
            <div class="garmin-metric-val">${battVal !== "--" ? `${battVal}%` : "--"}</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Stress</div>
            <div class="garmin-metric-val">${stressVal}</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Rest HR</div>
            <div class="garmin-metric-val">${hrVal}</div>
          </div>
          <div class="garmin-metric-pill">
            <div class="garmin-metric-label">Steps</div>
            <div class="garmin-metric-val">${stepsVal}</div>
          </div>
        `;
      }

      // Update Focus Banner
      if (focusBanner) {
        const shortState = shortEnt && this._hass.states ? this._hass.states[shortEnt] : undefined;
        const focusText =
          shortState && shortState.state !== "unavailable" && shortState.state !== "unknown"
            ? shortState.state
            : "Ready for today's workout and recovery guidance.";
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
          const ansState = answerEnt && this._hass.states ? this._hass.states[answerEnt] : undefined;
          const fullAnswer =
            ansState?.attributes?.full_answer ||
            (ansState?.state !== "unavailable" && ansState?.state !== "unknown" ? ansState?.state : "");
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
        const repState = longEnt && this._hass.states ? this._hass.states[longEnt] : undefined;
        const fullRep =
          repState?.attributes?.full_report ||
          repState?.attributes?.short_summary ||
          (repState?.state !== "unavailable" && repState?.state !== "unknown" ? repState?.state : "");
        if (!fullRep || fullRep === "No report generated yet" || fullRep === "unavailable") {
          reportBox.innerHTML = `<div class="garmin-empty-state">No full report generated yet.</div>`;
        } else {
          reportBox.innerHTML = `<div>${renderMarkdown(fullRep)}</div>`;
        }
      }
    }
  }

  /**
   * Helper Base Editor for HA visual card configuration forms.
   */
  class GarminCardBaseEditor extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._config = null;
      this._hass = null;
      this._form = null;
    }

    _getSchema() {
      return [];
    }

    _getLabels() {
      return {};
    }

    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      if (this._form) {
        this._form.hass = hass;
      }
    }

    _render() {
      if (!this.shadowRoot) return;

      this.shadowRoot.innerHTML = `
        <style>
          ha-form {
            display: block;
            margin-bottom: 8px;
          }
        </style>
        <ha-form id="form"></ha-form>
      `;

      this._form = this.shadowRoot.getElementById("form");
      if (this._form) {
        this._form.hass = this._hass;
        this._form.data = this._config;
        this._form.schema = this._getSchema();
        const labels = this._getLabels();
        this._form.computeLabel = (schema) => labels[schema.name] || schema.name;

        this._form.addEventListener("value-changed", (ev) => {
          ev.stopPropagation();
          const detail = {
            config: Object.assign({}, this._config, ev.detail.value),
          };
          this.dispatchEvent(
            new CustomEvent("config-changed", {
              detail: detail,
              bubbles: true,
              composed: true,
            })
          );
        });
      }
    }
  }

  class GarminHAIQAQuestionCardEditor extends GarminCardBaseEditor {
    _getSchema() {
      return [
        { name: "title", selector: { text: {} } },
        { name: "question_entity", selector: { entity: { domain: "text" } } },
        { name: "button_entity", selector: { entity: { domain: "button" } } },
        { name: "answer_entity", selector: { entity: { domain: "sensor" } } },
      ];
    }
    _getLabels() {
      return {
        title: "Card Title",
        question_entity: "Question Input Entity",
        button_entity: "Ask Button Entity",
        answer_entity: "Answer Sensor Entity",
      };
    }
  }

  class GarminHAIReportCardEditor extends GarminCardBaseEditor {
    _getSchema() {
      return [
        { name: "title", selector: { text: {} } },
        { name: "report_entity", selector: { entity: { domain: "sensor" } } },
        { name: "short_report_entity", selector: { entity: { domain: "sensor" } } },
        { name: "selected_report_entity", selector: { entity: { domain: "sensor" } } },
        { name: "generate_button_entity", selector: { entity: { domain: "button" } } },
        { name: "last_update_entity", selector: { entity: { domain: "sensor" } } },
        {
          name: "default_view",
          selector: {
            select: {
              options: [
                { value: "long", label: "Full Report" },
                { value: "short", label: "Daily Summary" },
                { value: "dynamic", label: "Dynamic View" },
              ],
            },
          },
        },
      ];
    }
    _getLabels() {
      return {
        title: "Card Title",
        report_entity: "Long Report Sensor",
        short_report_entity: "Short Report Sensor",
        selected_report_entity: "Selected Report Sensor",
        generate_button_entity: "Generate Button Entity",
        last_update_entity: "Last Update Sensor",
        default_view: "Default Active View",
      };
    }
  }

  class GarminHAIOverviewCardEditor extends GarminCardBaseEditor {
    _getSchema() {
      return [
        { name: "title", selector: { text: {} } },
        { name: "sleep_entity", selector: { entity: { domain: "sensor" } } },
        { name: "battery_entity", selector: { entity: { domain: "sensor" } } },
        { name: "stress_entity", selector: { entity: { domain: "sensor" } } },
        { name: "hr_entity", selector: { entity: { domain: "sensor" } } },
        { name: "steps_entity", selector: { entity: { domain: "sensor" } } },
        { name: "short_report_entity", selector: { entity: { domain: "sensor" } } },
        { name: "long_report_entity", selector: { entity: { domain: "sensor" } } },
        { name: "answer_entity", selector: { entity: { domain: "sensor" } } },
      ];
    }
    _getLabels() {
      return {
        title: "Card Title",
        sleep_entity: "Sleep Score Sensor",
        battery_entity: "Body Battery Sensor",
        stress_entity: "Stress Level Sensor",
        hr_entity: "Resting Heart Rate Sensor",
        steps_entity: "Steps Sensor",
        short_report_entity: "Short Report Sensor",
        long_report_entity: "Long Report Sensor",
        answer_entity: "Last Answer Sensor",
      };
    }
  }

  // Register Custom Card Elements with the browser
  if (!customElements.get("garmin-ha-ai-qa-card")) {
    customElements.define("garmin-ha-ai-qa-card", GarminHAIQAQuestionCard);
  }
  if (!customElements.get("garmin-ha-ai-report-card")) {
    customElements.define("garmin-ha-ai-report-card", GarminHAIReportCard);
  }
  if (!customElements.get("garmin-ha-ai-overview-card")) {
    customElements.define("garmin-ha-ai-overview-card", GarminHAIOverviewCard);
  }

  // Register Custom Card Editor Elements with the browser
  if (!customElements.get("garmin-ha-ai-qa-card-editor")) {
    customElements.define("garmin-ha-ai-qa-card-editor", GarminHAIQAQuestionCardEditor);
  }
  if (!customElements.get("garmin-ha-ai-report-card-editor")) {
    customElements.define("garmin-ha-ai-report-card-editor", GarminHAIReportCardEditor);
  }
  if (!customElements.get("garmin-ha-ai-overview-card-editor")) {
    customElements.define("garmin-ha-ai-overview-card-editor", GarminHAIOverviewCardEditor);
  }

  // Register Cards with Home Assistant Lovelace Card Picker (window.customCards)
  window.customCards = window.customCards || [];

  const cardsToRegister = [
    {
      type: "garmin-ha-ai-qa-card",
      name: "Garmin AI Coach Q&A",
      description: "Interactive Q&A text field, ask button, and live formatted coach answer view.",
      documentationURL: "https://github.com/j333c/garmin-ha-ai",
    },
    {
      type: "garmin-ha-ai-report-card",
      name: "Garmin AI Health Report",
      description: "Detailed AI health and recovery report with on-demand refresh and formatted Markdown view.",
      documentationURL: "https://github.com/j333c/garmin-ha-ai",
    },
    {
      type: "garmin-ha-ai-overview-card",
      name: "Garmin AI Health Overview",
      description: "Complete Garmin recovery glance metrics, daily coaching focus, interactive Q&A, and full reports.",
      documentationURL: "https://github.com/j333c/garmin-ha-ai",
    },
  ];

  for (const card of cardsToRegister) {
    const existingIdx = window.customCards.findIndex(
      (c) => c.type === card.type || c.type === `custom:${card.type}`
    );
    if (existingIdx >= 0) {
      window.customCards[existingIdx] = card;
    } else {
      window.customCards.push(card);
    }
  }

  console.info(
    "%c GARMIN-HA-AI %c Custom Lovelace Cards Loaded (v0.5.0-rc1) ",
    "color: white; background: #03a9f4; font-weight: 700; border-radius: 3px 0 0 3px;",
    "color: #03a9f4; background: rgba(3, 169, 244, 0.1); font-weight: 700; border-radius: 0 3px 3px 0;"
  );
})();
