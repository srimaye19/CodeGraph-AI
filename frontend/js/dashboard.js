/**
 * CodeGraph AI - Dashboard Metrics & Architecture Insights
 * Renders statistical cards, hotspot ranking, circular import alerts, and files table.
 */

const Dashboard = {
  renderOverview(summary) {
    if (!summary) return;

    // Stat cards
    document.getElementById("stat-files").textContent = summary.file_counts || 0;
    document.getElementById("stat-symbols").textContent = summary.symbol_counts || 0;
    document.getElementById("stat-packages").textContent = summary.package_counts || 0;

    const sevs = summary.security_severity_counts || { HIGH: 0, MEDIUM: 0, LOW: 0 };
    document.getElementById("stat-high-findings").textContent = sevs.HIGH || 0;
    document.getElementById("stat-med-findings").textContent = sevs.MEDIUM || 0;
    document.getElementById("stat-low-findings").textContent = sevs.LOW || 0;

    // Scan info banner
    const scanTimeElem = document.getElementById("overview-scan-time");
    if (scanTimeElem && summary.scan_timestamp) {
      const dateStr = new Date(summary.scan_timestamp).toLocaleString();
      scanTimeElem.textContent = `Scanned on ${dateStr}`;
    }

    // Hotspot preview in overview
    const hotspotContainer = document.getElementById("overview-hotspots-list");
    if (hotspotContainer) {
      const hotspots = summary.dependency_hotspots || [];
      if (hotspots.length === 0) {
        hotspotContainer.innerHTML = `<p style="font-size: 13px; color: var(--text-muted);">No coupled file dependencies detected.</p>`;
      } else {
        let html = `<ul style="list-style: none; display: flex; flex-direction: column; gap: 8px;">`;
        hotspots.slice(0, 5).forEach(h => {
          html += `
            <li style="display: flex; justify-content: space-between; font-size: 13px; padding: 6px 10px; background-color: var(--bg-tertiary); border-radius: var(--radius-sm);">
              <span style="font-family: var(--font-mono); color: var(--accent-blue);">${this.escape(h.path)}</span>
              <span style="color: var(--text-secondary); font-size: 12px;">In: <b>${h.in_degree}</b> | Out: <b>${h.out_degree}</b></span>
            </li>
          `;
        });
        html += `</ul>`;
        hotspotContainer.innerHTML = html;
      }
    }
  },

  renderArchitectureInsights(summary) {
    if (!summary) return;

    // 1. Dependency Hotspots Table
    const hotspotsTbody = document.getElementById("insights-hotspots-tbody");
    if (hotspotsTbody) {
      const hotspots = summary.dependency_hotspots || [];
      if (hotspots.length === 0) {
        hotspotsTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No dependency hotspots found.</td></tr>`;
      } else {
        let rows = "";
        hotspots.forEach(h => {
          rows += `
            <tr>
              <td style="font-family: var(--font-mono); color: var(--accent-blue); font-weight: 500;">${this.escape(h.path)}</td>
              <td><span class="sev-pill low">${h.in_degree}</span></td>
              <td><span class="sev-pill medium">${h.out_degree}</span></td>
              <td><b>${h.total_deps}</b></td>
            </tr>
          `;
        });
        hotspotsTbody.innerHTML = rows;
      }
    }

    // 2. Circular Dependencies
    const circularContainer = document.getElementById("insights-circular-container");
    if (circularContainer) {
      const cycles = summary.circular_dependencies || [];
      if (cycles.length === 0) {
        circularContainer.innerHTML = `
          <div style="padding: 16px; background-color: rgba(63, 185, 80, 0.1); border: 1px solid rgba(63, 185, 80, 0.3); border-radius: var(--radius-md); color: var(--accent-green); font-size: 13px;">
            <b>✓ No Circular Dependencies Detected:</b> The project dependency architecture forms a clean Directed Acyclic Graph (DAG).
          </div>
        `;
      } else {
        let html = `
          <div style="padding: 16px; background-color: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.3); border-radius: var(--radius-md); display: flex; flex-direction: column; gap: 10px;">
            <div style="color: var(--accent-red); font-size: 14px; font-weight: 700;">
              ⚠ Warning: ${cycles.length} Circular Dependency Chain(s) Detected
            </div>
            <p style="font-size: 12px; color: var(--text-secondary);">
              Circular imports between modules create tight coupling and can cause unexpected runtime import errors.
            </p>
        `;
        cycles.forEach((c, idx) => {
          html += `
            <div style="background-color: var(--bg-primary); border: 1px solid var(--border-subtle); padding: 10px 14px; border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 12px; color: var(--accent-yellow);">
              <b>Cycle ${idx + 1}:</b> ${c.map(p => this.escape(p)).join(" <span style='color: var(--text-muted);'>→</span> ")}
            </div>
          `;
        });
        html += `</div>`;
        circularContainer.innerHTML = html;
      }
    }

    // 3. Top Packages
    const pkgsTbody = document.getElementById("insights-packages-tbody");
    if (pkgsTbody) {
      const pkgs = summary.top_packages || [];
      if (pkgs.length === 0) {
        pkgsTbody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--text-muted);">No external packages recorded.</td></tr>`;
      } else {
        pkgsTbody.innerHTML = pkgs.map(p => `
          <tr>
            <td style="font-family: var(--font-mono); color: var(--accent-purple); font-weight: 600;">${this.escape(p.name)}</td>
            <td><b>${p.usage_count}</b> files</td>
          </tr>
        `).join("");
      }
    }

    // 4. Largest Files
    const largestTbody = document.getElementById("insights-largest-tbody");
    if (largestTbody) {
      const files = summary.largest_files || [];
      largestTbody.innerHTML = files.map(f => `
        <tr>
          <td style="font-family: var(--font-mono); color: var(--text-primary);">${this.escape(f.path)}</td>
          <td><span class="sev-pill low">${this.escape(f.language)}</span></td>
          <td><b>${f.loc}</b> LOC</td>
        </tr>
      `).join("");
    }
  },

  renderFilesTable(files) {
    const tbody = document.getElementById("files-tbody");
    if (!tbody) return;

    if (!files || files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No files found in project.</td></tr>`;
      return;
    }

    tbody.innerHTML = files.map(f => `
      <tr>
        <td style="font-family: var(--font-mono); color: var(--accent-blue); font-weight: 500;">${this.escape(f.path)}</td>
        <td><span class="sev-pill low">${this.escape(f.language)}</span></td>
        <td>${f.loc}</td>
        <td>${f.functions_count}</td>
        <td>
          ${f.findings_count > 0 
            ? `<span class="sev-pill high">${f.findings_count}</span>` 
            : `<span class="sev-pill low">0</span>`}
        </td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="App.inspectFile('${this.escape(f.id)}')">
            Inspect
          </button>
        </td>
      </tr>
    `).join("");
  },

  renderScanHistory(projects, currentPid) {
    const tbody = document.getElementById("history-tbody");
    if (!tbody) return;

    if (!projects || projects.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">No scan history found.</td></tr>`;
      return;
    }

    tbody.innerHTML = projects.map(p => {
      const isCurrent = p.id === currentPid;
      const dateStr = p.scan_timestamp ? new Date(p.scan_timestamp).toLocaleString() : "Unknown";
      return `
        <tr style="${isCurrent ? 'background-color: rgba(88, 166, 255, 0.05);' : ''}">
          <td style="font-weight: 600; color: var(--text-primary);">
            ${this.escape(p.name)} ${isCurrent ? '<span class="sev-pill low" style="margin-left: 6px;">Active</span>' : ''}
          </td>
          <td>${dateStr}</td>
          <td>${p.files_count}</td>
          <td>
            ${p.findings_count > 0 ? `<span class="sev-pill high">${p.findings_count}</span>` : `<span class="sev-pill low">0</span>`}
          </td>
          <td style="display: flex; gap: 8px;">
            ${!isCurrent ? `<button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="App.switchProject('${p.id}')">Select</button>` : ''}
            <a class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px; text-decoration: none;" href="${API.getExportUrl(p.id)}" download>Export</a>
            <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="App.confirmDeleteProject('${p.id}', '${this.escape(p.name)}')">Delete</button>
          </td>
        </tr>
      `;
    }).join("");
  },

  escape(str) {
    if (!str) return "";
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
};
