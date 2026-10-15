/**
 * CodeGraph AI - Security Findings Module
 * Renders security alerts, code snippets, remediation guides, and graph locator.
 */

const Findings = {
  allFindings: [],

  render(findings) {
    this.allFindings = findings || [];
    this.filterAndRender();
  },

  filterAndRender() {
    const container = document.getElementById("findings-list-container");
    if (!container) return;

    const severityFilter = document.getElementById("findings-severity-filter")?.value || "ALL";
    const searchQuery = (document.getElementById("findings-search-input")?.value || "").toLowerCase();

    const filtered = this.allFindings.filter(f => {
      const matchSev = severityFilter === "ALL" || f.severity.toUpperCase() === severityFilter;
      const matchQuery = !searchQuery || 
        f.rule_id.toLowerCase().includes(searchQuery) ||
        f.message.toLowerCase().includes(searchQuery) ||
        f.file.toLowerCase().includes(searchQuery);
      return matchSev && matchQuery;
    });

    const countElem = document.getElementById("findings-count-badge");
    if (countElem) {
      countElem.textContent = `${filtered.length} Finding(s)`;
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="padding: 32px; text-align: center; color: var(--text-muted); background-color: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);">
          No security findings match the current filters.
        </div>
      `;
      return;
    }

    container.innerHTML = filtered.map(f => {
      const sevClass = f.severity.toLowerCase();
      return `
        <div class="metric-card" style="padding: 18px; display: flex; flex-direction: column; gap: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="sev-pill ${sevClass}">${f.severity}</span>
              <span style="font-family: var(--font-mono); font-weight: 700; color: var(--text-primary); font-size: 14px;">
                ${this.escape(f.rule_id)}
              </span>
              ${f.cwe_id ? `<span style="font-size: 11px; color: var(--text-muted); background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${this.escape(f.cwe_id)}</span>` : ''}
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 11px; color: var(--text-muted);">Confidence: <b>${this.escape(f.confidence)}</b></span>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="Findings.locateInGraph('${f.id}')">
                View in Graph
              </button>
            </div>
          </div>

          <div style="font-size: 13px; color: var(--text-primary); font-weight: 500;">
            ${this.escape(f.message)}
          </div>

          <div style="font-size: 12px; color: var(--text-secondary); font-family: var(--font-mono);">
            File: <span style="color: var(--accent-blue);">${this.escape(f.file)}</span> : Line ${f.line}
          </div>

          ${f.snippet ? `<div class="code-snippet">${this.escape(f.snippet)}</div>` : ''}

          <div style="background-color: var(--bg-primary); border-left: 3px solid var(--accent-green); padding: 8px 12px; font-size: 12px; color: var(--text-secondary); border-radius: 0 var(--radius-sm) var(--radius-sm) 0;">
            <b style="color: var(--accent-green);">Fix Recommendation:</b> ${this.escape(f.recommendation)}
          </div>
        </div>
      `;
    }).join("");
  },

  locateInGraph(findingId) {
    App.switchTab("graph");
    setTimeout(() => {
      GraphVisualizer.focusNode(findingId);
    }, 200);
  },

  escape(str) {
    if (!str) return "";
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
};
