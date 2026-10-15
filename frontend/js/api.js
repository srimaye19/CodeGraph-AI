/**
 * CodeGraph AI - API Client
 * Centralized Fetch API abstraction with standardized JSON parsing and error handling.
 */

const API = {
  baseUrl: "/api",

  async getHealth() {
    const res = await fetch(`${this.baseUrl}/health`);
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },

  async getProjects() {
    const res = await fetch(`${this.baseUrl}/projects`);
    if (!res.ok) throw new Error("Failed to load projects");
    return res.json();
  },

  async getProjectSummary(pid) {
    const res = await fetch(`${this.baseUrl}/projects/${pid}/summary`);
    if (!res.ok) throw new Error("Failed to load project summary");
    return res.json();
  },

  async getProjectGraph(pid, types = null) {
    let url = `${this.baseUrl}/projects/${pid}/graph`;
    if (types && types.length > 0) {
      url += `?types=${encodeURIComponent(types.join(","))}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load graph data");
    return res.json();
  },

  async getProjectFindings(pid, severity = null, ruleId = null, page = 1, limit = 50) {
    const params = new URLSearchParams({ page, limit });
    if (severity) params.append("severity", severity);
    if (ruleId) params.append("rule_id", ruleId);

    const res = await fetch(`${this.baseUrl}/projects/${pid}/findings?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to load findings");
    return res.json();
  },

  async getProjectFiles(pid) {
    const res = await fetch(`${this.baseUrl}/projects/${pid}/files`);
    if (!res.ok) throw new Error("Failed to load project files");
    return res.json();
  },

  async getFileDetails(pid, fileId) {
    const res = await fetch(`${this.baseUrl}/projects/${pid}/files/${encodeURIComponent(fileId)}`);
    if (!res.ok) throw new Error("Failed to load file details");
    return res.json();
  },

  async generateAIReview(pid) {
    const res = await fetch(`${this.baseUrl}/projects/${pid}/ai`, {
      method: "POST"
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Failed to generate AI review");
    }
    return res.json();
  },

  async scanLocalPath(path, projectName = null) {
    const res = await fetch(`${this.baseUrl}/scan/path`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, project_name: projectName })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Local path scan failed");
    }
    return res.json();
  },

  async scanUploadZip(file, projectName = null) {
    const formData = new FormData();
    formData.append("file", file);
    if (projectName) {
      formData.append("project_name", projectName);
    }
    const res = await fetch(`${this.baseUrl}/scan/upload`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Archive upload scan failed");
    }
    return res.json();
  },

  async deleteProject(pid) {
    const res = await fetch(`${this.baseUrl}/projects/${pid}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Failed to delete project");
    return res.json();
  },

  getExportUrl(pid) {
    return `${this.baseUrl}/projects/${pid}/export`;
  }
};
