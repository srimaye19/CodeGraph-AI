# CodeGraph AI — REST API Documentation

Base URL: `http://127.0.0.1:8000/api`  
Swagger UI: `http://127.0.0.1:8000/docs`  
ReDoc UI: `http://127.0.0.1:8000/redoc`

---

## Standard Error Schema
All error responses adhere to the following schema:
```json
{
  "error": "Descriptive error message",
  "details": {},
  "status_code": 400
}
```

---

## Endpoints

### 1. Health Check
`GET /api/health`
- **Description:** Verifies API health and Neo4j connectivity.
- **Response (200 OK):**
```json
{
  "status": "ok",
  "app": "CodeGraph AI",
  "version": "1.0.0",
  "neo4j": {
    "connected": true,
    "configured": true,
    "uri": "neo4j+s://***:***@xxxx.databases.neo4j.io",
    "message": "Connected to Neo4j successfully."
  },
  "timestamp": "2026-10-14T16:00:00Z"
}
```

---

### 2. Scan Local Project Directory
`POST /api/scan/path`
- **Request Body (JSON):**
```json
{
  "path": "samples/demo_project",
  "project_name": "Demo Codebase"
}
```
- **Response (200 OK):**
```json
{
  "project_id": "proj_a1b2c3d4e5f6",
  "project_name": "Demo Codebase",
  "scan_timestamp": "2026-10-14T16:00:00Z",
  "stats": {
    "files_scanned": 3,
    "lines_of_code": 120,
    "functions_count": 15,
    "classes_count": 3,
    "packages_count": 6,
    "findings_count": 6,
    "duration_ms": 142.5
  },
  "message": "Local directory scanned and persisted to graph successfully."
}
```

---

### 3. Scan Uploaded Project Archive
`POST /api/scan/upload`
- **Form Data:**
  - `file`: Binary ZIP file (max 25MB).
  - `project_name`: (Optional) String name.
- **Protections:** Rejects path traversal (`..`), absolute paths, and zip bombs.

---

### 4. List Scanned Projects
`GET /api/projects`
- **Response (200 OK):**
```json
[
  {
    "id": "proj_a1b2c3d4e5f6",
    "name": "Demo Codebase",
    "scan_timestamp": "2026-10-14T16:00:00Z",
    "files_count": 3,
    "findings_count": 6
  }
]
```

---

### 5. Get Project Knowledge Graph
`GET /api/projects/{pid}/graph?types=file,symbol,package,finding`
- **Query Parameters:**
  - `types`: (Optional) Comma-separated filter of node types.
- **Response (200 OK):** vis-network formatted nodes and edges.
```json
{
  "nodes": [
    {
      "id": "proj_123::file:app.py",
      "label": "app.py",
      "type": "file",
      "title": "<b>File:</b> app.py<br><b>LOC:</b> 45",
      "group": "file",
      "color": { "background": "#1f6feb", "border": "#58a6ff" },
      "shape": "box"
    }
  ],
  "edges": [
    {
      "id": "edge_1",
      "from": "proj_123::file:app.py",
      "to": "proj_123::file:database.py",
      "label": "DEPENDS_ON",
      "type": "DEPENDS_ON",
      "arrows": "to"
    }
  ],
  "total_nodes": 24,
  "total_edges": 18
}
```

---

### 6. Get Architecture Summary & Hotspots
`GET /api/projects/{pid}/summary`
- **Response (200 OK):** Includes file counts, symbol counts, packages, severity counts, dependency hotspots, circular dependency paths, and largest files.

---

### 7. Get Security Findings
`GET /api/projects/{pid}/findings?severity=HIGH&page=1&limit=50`
- **Query Parameters:**
  - `severity`: (Optional) `HIGH`, `MEDIUM`, or `LOW`.
  - `rule_id`: (Optional) e.g., `SEC001`.
  - `page`: Page number (default: 1).
  - `limit`: Items per page (default: 50).

---

### 8. Generate AI Architecture Review
`POST /api/projects/{pid}/ai`
- **Response (200 OK):**
```json
{
  "project_id": "proj_123",
  "provider_used": "rule-based-engine",
  "is_fallback": true,
  "architecture_overview": "...",
  "key_dependencies": ["..."],
  "security_concerns": ["..."],
  "recommendations": [
    {
      "title": "Remediate SEC004 in app.py",
      "category": "Security Hardening",
      "severity": "HIGH",
      "details": "..."
    }
  ],
  "refactoring_priorities": ["..."],
  "circular_import_observations": "...",
  "limitations_and_uncertainty": "...",
  "raw_markdown": "# CodeGraph AI Architecture & Security Review\n..."
}
```

---

### 9. Export Project JSON
`GET /api/projects/{pid}/export`
- **Response:** Downloads complete scan report including graph summary, findings, and metadata.

---

### 10. Delete Project
`DELETE /api/projects/{pid}`
- **Response (200 OK):** Safely deletes all project nodes and relationships from Neo4j.
