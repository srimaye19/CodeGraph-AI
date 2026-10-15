/**
 * CodeGraph AI - Application Controller
 * Handles global state, tab routing, project selection, modals, and notifications.
 */

const App = {
  currentProjectId: null,
  projects: [],
  activeTab: "overview",

  async init() {
    // Initialize graph visualizer canvas
    GraphVisualizer.init("graph-canvas");

    // Setup UI event listeners
    this.setupEventListeners();

    // Check health & Neo4j status
    await this.checkHealth();
    setInterval(() => this.checkHealth(), 15000);

    // Load available projects
    await this.loadProjects();
  },

  setupEventListeners() {
    // Sidebar tabs
    document.querySelectorAll(".nav-item").forEach(item => {
      item.addEventListener("click", () => {
        const tab = item.getAttribute("data-tab");
        if (tab) this.switchTab(tab);
      });
    });

    // Project selector
    const projSelect = document.getElementById("project-selector");
    if (projSelect) {
      projSelect.addEventListener("change", (e) => {
        const pid = e.target.value;
        if (pid) this.switchProject(pid);
      });
    }

    // Graph controls
    document.querySelectorAll(".filter-chip input").forEach(input => {
      input.addEventListener("change", () => GraphVisualizer.applyFilters());
    });

    const searchInput = document.getElementById("graph-search-input");
    if (searchInput) {
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") GraphVisualizer.focusNode(searchInput.value);
      });
    }

    // Findings filters
    const sevFilter = document.getElementById("findings-severity-filter");
    if (sevFilter) {
      sevFilter.addEventListener("change", () => Findings.filterAndRender());
    }
    const findSearch = document.getElementById("findings-search-input");
    if (findSearch) {
      findSearch.addEventListener("input", () => Findings.filterAndRender());
    }

    // Scan Modal Tabs
    document.querySelectorAll(".modal-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".modal-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const mode = tab.getAttribute("data-mode");
        document.getElementById("modal-tab-zip").style.display = mode === "zip" ? "block" : "none";
        document.getElementById("modal-tab-path").style.display = mode === "path" ? "block" : "none";
      });
    });

    // Drag and Drop ZIP
    const dropzone = document.getElementById("zip-dropzone");
    const fileInput = document.getElementById("zip-file-input");
    if (dropzone && fileInput) {
      dropzone.addEventListener("click", () => fileInput.click());
      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--accent-blue)";
      });
      dropzone.addEventListener("dragleave", () => {
        dropzone.style.borderColor = "var(--border-strong)";
      });
      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--border-strong)";
        if (e.dataTransfer.files.length > 0) {
          fileInput.files = e.dataTransfer.files;
          document.getElementById("zip-file-name").textContent = e.dataTransfer.files[0].name;
        }
      });
      fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
          document.getElementById("zip-file-name").textContent = fileInput.files[0].name;
        }
      });
    }
  },

  async checkHealth() {
    try {
      const data = await API.getHealth();
      const dot = document.getElementById("neo4j-status-dot");
      const text = document.getElementById("neo4j-status-text");
      const badge = document.getElementById("neo4j-status-badge");

      if (data.neo4j.connected) {
        dot.className = "status-dot connected";
        text.textContent = "Neo4j Connected";
        badge.title = `URI: ${data.neo4j.uri}\nStatus: Live Aura/Bolt connection active`;
      } else {
        dot.className = "status-dot disconnected";
        text.textContent = "Neo4j Offline (In-Memory)";
        badge.title = `${data.neo4j.message}\nOperating with high-fidelity in-memory knowledge graph.`;
      }
    } catch (e) {
      const dot = document.getElementById("neo4j-status-dot");
      const text = document.getElementById("neo4j-status-text");
      if (dot) dot.className = "status-dot disconnected";
      if (text) text.textContent = "Server Offline";
    }
  },

  async loadProjects() {
    try {
      this.projects = await API.getProjects();
      const select = document.getElementById("project-selector");
      if (!select) return;

      select.innerHTML = "";
      if (this.projects.length === 0) {
        select.innerHTML = `<option value="">No projects scanned</option>`;
        this.showNoProjectsState();
        return;
      }

      this.projects.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.files_count} files)`;
        select.appendChild(opt);
      });

      // Select first project or maintain existing
      const targetPid = (this.currentProjectId && this.projects.some(p => p.id === this.currentProjectId))
        ? this.currentProjectId
        : this.projects[0].id;

      select.value = targetPid;
      await this.switchProject(targetPid);

    } catch (err) {
      this.showToast("Failed to load project list: " + err.message, "error");
    }
  },

  async switchProject(pid) {
    this.currentProjectId = pid;
    const select = document.getElementById("project-selector");
    if (select) select.value = pid;

    try {
      // 1. Load Summary
      const summary = await API.getProjectSummary(pid);
      Dashboard.renderOverview(summary);
      Dashboard.renderArchitectureInsights(summary);

      // 2. Load Graph
      const graphData = await API.getProjectGraph(pid);
      GraphVisualizer.setData(graphData.nodes, graphData.edges);

      // 3. Load Files
      const files = await API.getProjectFiles(pid);
      Dashboard.renderFilesTable(files);

      // 4. Load Findings
      const findingsRes = await API.getProjectFindings(pid, null, null, 1, 100);
      Findings.render(findingsRes.findings);

      // 5. Update History
      Dashboard.renderScanHistory(this.projects, pid);

      // Clear AI review pane for new project
      const aiContainer = document.getElementById("ai-review-content");
      if (aiContainer) {
        aiContainer.innerHTML = `
          <div style="text-align: center; padding: 48px; color: var(--text-muted);">
            Click <b>"Generate AI Architecture Review"</b> above to run comprehensive evaluation for ${Dashboard.escape(summary.project_name)}.
          </div>
        `;
      }

    } catch (err) {
      this.showToast("Failed to load project data: " + err.message, "error");
    }
  },

  switchTab(tabId) {
    this.activeTab = tabId;
    document.querySelectorAll(".nav-item").forEach(item => {
      item.classList.toggle("active", item.getAttribute("data-tab") === tabId);
    });
    document.querySelectorAll(".tab-pane").forEach(pane => {
      pane.classList.toggle("active", pane.id === `tab-${tabId}`);
    });

    if (tabId === "graph") {
      setTimeout(() => GraphVisualizer.fit(), 100);
    }
  },

  openScanModal() {
    document.getElementById("scan-modal").classList.add("open");
  },

  closeScanModal() {
    document.getElementById("scan-modal").classList.remove("open");
  },

  fillDemoPath() {
    const pathInput = document.getElementById("local-path-input");
    if (pathInput) {
      pathInput.value = "samples/demo_project";
    }
  },

  async submitPathScan() {
    const pathInput = document.getElementById("local-path-input");
    const nameInput = document.getElementById("local-name-input");
    const pathVal = pathInput?.value?.trim();
    const nameVal = nameInput?.value?.trim() || null;

    if (!pathVal) {
      this.showToast("Please enter a local directory path", "error");
      return;
    }

    this.setScanLoading(true, "Scanning local directory architecture and security...");
    try {
      const res = await API.scanLocalPath(pathVal, nameVal);
      this.showToast(`Scan complete: ${res.stats.files_scanned} files, ${res.stats.findings_count} findings!`, "success");
      this.closeScanModal();
      await this.loadProjects();
      await this.switchProject(res.project_id);
    } catch (err) {
      this.showToast(err.message, "error");
    } finally {
      this.setScanLoading(false);
    }
  },

  async submitZipScan() {
    const fileInput = document.getElementById("zip-file-input");
    const nameInput = document.getElementById("zip-name-input");
    if (!fileInput.files || fileInput.files.length === 0) {
      this.showToast("Please choose a .zip file to upload", "error");
      return;
    }

    const file = fileInput.files[0];
    const nameVal = nameInput?.value?.trim() || null;

    this.setScanLoading(true, "Uploading, validating, and analyzing ZIP archive...");
    try {
      const res = await API.scanUploadZip(file, nameVal);
      this.showToast(`Upload analyzed: ${res.stats.files_scanned} files scanned!`, "success");
      this.closeScanModal();
      await this.loadProjects();
      await this.switchProject(res.project_id);
    } catch (err) {
      this.showToast(err.message, "error");
    } finally {
      this.setScanLoading(false);
    }
  },

  setScanLoading(isLoading, message = "") {
    const loadingElem = document.getElementById("scan-loading-indicator");
    const msgElem = document.getElementById("scan-loading-msg");
    const submitBtns = document.querySelectorAll(".scan-submit-btn");

    if (loadingElem) loadingElem.style.display = isLoading ? "flex" : "none";
    if (msgElem) msgElem.textContent = message;
    submitBtns.forEach(btn => btn.disabled = isLoading);
  },

  async triggerAIReview() {
    if (!this.currentProjectId) {
      this.showToast("Please select or scan a project first", "error");
      return;
    }

    const container = document.getElementById("ai-review-content");
    const btn = document.getElementById("btn-generate-ai");
    if (btn) btn.disabled = true;

    if (container) {
      container.innerHTML = `
        <div style="text-align: center; padding: 48px;">
          <div style="font-size: 24px; margin-bottom: 12px;">⏳</div>
          <p style="color: var(--text-primary); font-weight: 600;">Synthesizing Codebase Knowledge Graph & Findings...</p>
          <p style="font-size: 12px; color: var(--text-secondary); margin-top: 6px;">
            Evaluating structural coupling, circular imports, and vulnerability mitigations.
          </p>
        </div>
      `;
    }

    try {
      const review = await API.generateAIReview(this.currentProjectId);
      this.renderAIReview(review);
      this.showToast("AI Review generated successfully!", "success");
    } catch (err) {
      this.showToast(err.message, "error");
      if (container) {
        container.innerHTML = `<div style="padding: 24px; color: var(--accent-red);">Error generating review: ${Dashboard.escape(err.message)}</div>`;
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  renderAIReview(review) {
    const container = document.getElementById("ai-review-content");
    if (!container) return;

    // Convert Markdown to HTML
    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <span class="sev-pill low" style="font-size: 12px; padding: 4px 10px;">
          Engine: <b>${Dashboard.escape(review.provider_used)}</b>
        </span>
        <span style="font-size: 12px; color: var(--text-muted);">
          Deterministic Rule-Based Synthesis & Auditing
        </span>
      </div>
      <div class="ai-report-container">
        ${this.simpleMarkdownToHtml(review.raw_markdown)}
      </div>
    `;
  },

  simpleMarkdownToHtml(md) {
    if (!md) return "";
    let html = md
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\*\*(.*?)\*\*/gim, '<b>$1</b>')
      .replace(/\*(.*?)\*/gim, '<i>$1</i>')
      .replace(/---/gim, '<hr>')
      .replace(/^\- (.*$)/gim, '<li>$1</li>');

    // Wrap list items in <ul>
    html = html.replace(/(<li>[\s\S]*?<\/li>)/gim, '<ul>$1</ul>');
    html = html.replace(/\n\n/gim, '<p></p>');
    return html;
  },

  async inspectFile(fileId) {
    try {
      const fileData = await API.getFileDetails(this.currentProjectId, fileId);
      const inspector = document.getElementById("file-details-modal-content");
      if (!inspector) return;

      inspector.innerHTML = `
        <h3 style="font-size: 16px; color: var(--accent-blue); margin-bottom: 12px; font-family: var(--font-mono);">
          ${Dashboard.escape(fileData.path)}
        </h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; font-size: 13px;">
          <div>Language: <b>${Dashboard.escape(fileData.language)}</b></div>
          <div>Lines of Code: <b>${fileData.loc}</b></div>
          <div>Functions/Methods: <b>${fileData.functions.length}</b></div>
          <div>Classes: <b>${fileData.classes.length}</b></div>
        </div>

        <div style="margin-bottom: 14px;">
          <h4 style="font-size: 13px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Internal File Dependencies:</h4>
          ${fileData.dependencies.length > 0 
            ? fileData.dependencies.map(d => `<span class="sev-pill low" style="margin: 2px;">${Dashboard.escape(d)}</span>`).join(" ") 
            : '<span style="color: var(--text-muted); font-size: 12px;">None (Standalone)</span>'}
        </div>

        <div style="margin-bottom: 14px;">
          <h4 style="font-size: 13px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">External Packages:</h4>
          ${fileData.packages.length > 0 
            ? fileData.packages.map(p => `<span class="sev-pill" style="margin: 2px; color: var(--accent-purple); border-color: var(--accent-purple);">${Dashboard.escape(p)}</span>`).join(" ") 
            : '<span style="color: var(--text-muted); font-size: 12px;">No third-party packages</span>'}
        </div>

        <div>
          <h4 style="font-size: 13px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Security Findings:</h4>
          ${fileData.findings.length > 0
            ? fileData.findings.map(fd => `
                <div style="padding: 8px 12px; background-color: var(--bg-tertiary); border-radius: var(--radius-sm); margin-bottom: 6px; font-size: 12px;">
                  <b style="color: var(--accent-red);">${Dashboard.escape(fd.rule_id)}</b> Line ${fd.line}: ${Dashboard.escape(fd.message)}
                </div>
              `).join("")
            : '<span style="color: var(--accent-green); font-size: 12px;">✓ Clean file (no security issues detected)</span>'}
        </div>
      `;

      document.getElementById("file-details-modal").classList.add("open");

    } catch (e) {
      this.showToast("Could not retrieve file details: " + e.message, "error");
    }
  },

  closeFileModal() {
    document.getElementById("file-details-modal").classList.remove("open");
  },

  async confirmDeleteProject(pid, name) {
    if (confirm(`Are you sure you want to delete project '${name}' and its knowledge graph?`)) {
      try {
        await API.deleteProject(pid);
        this.showToast(`Project '${name}' deleted successfully`, "success");
        await this.loadProjects();
      } catch (e) {
        this.showToast("Failed to delete project: " + e.message, "error");
      }
    }
  },

  showNoProjectsState() {
    document.getElementById("stat-files").textContent = "0";
    document.getElementById("stat-symbols").textContent = "0";
    document.getElementById("stat-packages").textContent = "0";
    document.getElementById("stat-high-findings").textContent = "0";
    document.getElementById("stat-med-findings").textContent = "0";
    document.getElementById("stat-low-findings").textContent = "0";
  },

  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icon = type === "success" ? "✓" : (type === "error" ? "⚠" : "ℹ");
    toast.innerHTML = `<span>${icon}</span> <span>${Dashboard.escape(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  }
};

// Start application on DOM ready
document.addEventListener("DOMContentLoaded", () => App.init());
