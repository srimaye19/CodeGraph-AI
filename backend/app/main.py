"""
CodeGraph AI - FastAPI Main Application
Exposes REST APIs for health checks, project scanning, graph retrieval,
security findings, architecture metrics, and AI reviews.
"""

import os
import shutil
import tempfile
import zipfile
import uuid
import time
import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import settings
from backend.app.schemas import (
    HealthResponse, Neo4jHealth, ScanPathRequest, ScanResponse, ScanStats,
    ProjectListItem, ProjectSummary, GraphResponse, FindingsResponse,
    FileItem, FileDetailResponse, AIReviewResponse
)
from backend.app.exceptions import (
    CodeGraphException, InvalidUploadError, PathTraversalError,
    ProjectNotFoundError, DatabaseConnectionError, ScanError
)
from backend.app.analyzer import CodebaseAnalyzer
from backend.app.graph import get_graph_repository
from backend.app.ai import get_ai_reviewer


app = FastAPI(
    title="CodeGraph AI API",
    description="AI-Powered Code Architecture Mapping and Security Analysis Using Neo4j",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for structured JSON responses
@app.exception_handler(CodeGraphException)
async def codegraph_exception_handler(request, exc: CodeGraphException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details, "status_code": exc.status_code}
    )


# ------------------------------------------------------------------------------
# Health Endpoint
# ------------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def get_health():
    """Check API and Neo4j database health status."""
    repo = get_graph_repository()
    db_status = repo.check_connection()

    # Mask credentials from URI if present
    safe_uri = db_status.get("uri", "")
    if "@" in safe_uri:
        prefix, host = safe_uri.split("@", 1)
        scheme = prefix.split("://")[0] if "://" in prefix else "neo4j"
        safe_uri = f"{scheme}://***:***@{host}"

    return HealthResponse(
        status="ok",
        app="CodeGraph AI",
        version="1.0.0",
        neo4j=Neo4jHealth(
            connected=db_status.get("connected", False),
            configured=db_status.get("configured", False),
            uri=safe_uri,
            message=db_status.get("message", "")
        ),
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


# ------------------------------------------------------------------------------
# Project Scanning Endpoints
# ------------------------------------------------------------------------------

def _validate_safe_zip(zip_file: zipfile.ZipFile, max_files: int, max_extracted_mb: int):
    """Ensure archive contains no path traversal ('..'), absolute paths, or excessive sizes."""
    total_size = 0
    infolist = zip_file.infolist()

    if len(infolist) > max_files:
        raise InvalidUploadError(
            f"Archive exceeds maximum allowable file count ({len(infolist)} > {max_files})."
        )

    for member in infolist:
        name = member.filename
        # Check directory traversal
        if ".." in name or name.startswith("/") or name.startswith("\\"):
            raise PathTraversalError(f"Unsafe path detected in archive: {name}")

        total_size += member.file_size
        if total_size > max_extracted_mb * 1024 * 1024:
            raise InvalidUploadError(
                f"Archive uncompressed size exceeds limit of {max_extracted_mb} MB."
            )


@app.post("/api/scan/upload", response_model=ScanResponse, tags=["Scanning"])
async def scan_uploaded_zip(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None)
):
    """
    Accept and scan an uploaded project ZIP file with complete path-traversal validation.
    """
    if not file.filename.lower().endswith(".zip"):
        raise InvalidUploadError("Only .zip archives are supported.")

    start_time = time.perf_counter()
    temp_dir = tempfile.mkdtemp(prefix="codegraph_upload_")
    zip_path = os.path.join(temp_dir, "upload.zip")

    try:
        # Save uploaded bytes with size validation
        size = 0
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        with open(zip_path, "wb") as f_out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise InvalidUploadError(f"Uploaded file exceeds {settings.MAX_UPLOAD_MB} MB limit.")
                f_out.write(chunk)

        # Validate ZIP
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                _validate_safe_zip(z, settings.MAX_FILES_PER_SCAN, settings.MAX_UPLOAD_MB * 2)
                extract_path = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_path, exist_ok=True)
                z.extractall(extract_path)
        except zipfile.BadZipFile:
            raise InvalidUploadError("Corrupt or invalid ZIP archive.")

        # Run analysis
        analyzer = CodebaseAnalyzer(Path(extract_path))
        result = analyzer.analyze()

        # Project metadata
        p_name = project_name or Path(file.filename).stem or "Uploaded Project"
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

        # Persist to Graph DB
        repo = get_graph_repository()
        repo.save_project_analysis(project_id, p_name, result)

        duration = (time.perf_counter() - start_time) * 1000
        stats = ScanStats(
            files_scanned=result["stats"]["files_scanned"],
            lines_of_code=result["stats"]["lines_of_code"],
            functions_count=result["stats"]["functions_count"],
            classes_count=result["stats"]["classes_count"],
            packages_count=result["stats"]["packages_count"],
            findings_count=result["stats"]["findings_count"],
            duration_ms=round(duration, 2)
        )

        return ScanResponse(
            project_id=project_id,
            project_name=p_name,
            scan_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            stats=stats,
            message="Archive validated, analyzed, and stored in knowledge graph successfully."
        )

    finally:
        # Resource cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/scan/path", response_model=ScanResponse, tags=["Scanning"])
def scan_local_path(request: ScanPathRequest):
    """
    Scan a local codebase directory on the server/local workstation.
    """
    target_path = Path(request.path).resolve()

    if not target_path.exists():
        raise ScanError(f"Specified path does not exist: {target_path}", details={"path": str(target_path)})
    if not target_path.is_dir():
        raise ScanError(f"Specified path is not a directory: {target_path}", details={"path": str(target_path)})

    # Protection against dangerous root-level directory scans
    forbidden_roots = {"/", "\\", "C:\\", "C:", "C:/", "/etc", "/var", "/usr", "/bin", "/Windows"}
    if str(target_path).rstrip("/\\") in forbidden_roots or len(target_path.parts) <= 1:
        raise PathTraversalError("Scanning the root system directory is forbidden for security reasons.")

    start_time = time.perf_counter()
    analyzer = CodebaseAnalyzer(target_path)
    result = analyzer.analyze()

    p_name = request.project_name or target_path.name or "Local Project"
    project_id = f"proj_{uuid.uuid4().hex[:12]}"

    repo = get_graph_repository()
    repo.save_project_analysis(project_id, p_name, result)

    duration = (time.perf_counter() - start_time) * 1000
    stats = ScanStats(
        files_scanned=result["stats"]["files_scanned"],
        lines_of_code=result["stats"]["lines_of_code"],
        functions_count=result["stats"]["functions_count"],
        classes_count=result["stats"]["classes_count"],
        packages_count=result["stats"]["packages_count"],
        findings_count=result["stats"]["findings_count"],
        duration_ms=round(duration, 2)
    )

    return ScanResponse(
        project_id=project_id,
        project_name=p_name,
        scan_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        stats=stats,
        message="Local directory scanned and persisted to graph successfully."
    )


# ------------------------------------------------------------------------------
# Project Data & Graph Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/projects", response_model=List[ProjectListItem], tags=["Projects"])
def list_projects():
    """Retrieve all previously scanned projects."""
    repo = get_graph_repository()
    projs = repo.get_projects()
    out = []
    for p in projs:
        out.append(ProjectListItem(
            id=p["id"],
            name=p.get("name") or "Unnamed",
            scan_timestamp=p.get("scanned_at") or "",
            files_count=p.get("files_count", 0),
            findings_count=p.get("findings_count", 0)
        ))
    return out


@app.get("/api/projects/{pid}/graph", response_model=GraphResponse, tags=["Projects"])
def get_graph_data(pid: str, types: Optional[str] = Query(None, description="Comma-separated node types")):
    """Retrieve nodes and edges for vis-network graph rendering."""
    repo = get_graph_repository()
    type_list = [t.strip().lower() for t in types.split(",")] if types else None
    graph = repo.get_project_graph(pid, node_types=type_list)
    return GraphResponse(
        nodes=graph["nodes"],
        edges=graph["edges"],
        total_nodes=graph["total_nodes"],
        total_edges=graph["total_edges"]
    )


@app.get("/api/projects/{pid}/summary", response_model=ProjectSummary, tags=["Projects"])
def get_project_summary(pid: str):
    """Retrieve project architecture statistics, hotspots, and circular dependency checks."""
    repo = get_graph_repository()
    summary = repo.get_project_summary(pid)
    if not summary:
        raise ProjectNotFoundError(pid)
    return ProjectSummary(**summary)


@app.get("/api/projects/{pid}/findings", response_model=FindingsResponse, tags=["Projects"])
def get_project_findings(
    pid: str,
    severity: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Retrieve security findings with optional severity or rule filtering."""
    repo = get_graph_repository()
    result = repo.get_project_findings(pid, severity=severity, rule_id=rule_id, page=page, limit=limit)
    return FindingsResponse(
        findings=result["findings"],
        total=result["total"],
        page=result["page"],
        limit=result["limit"]
    )


@app.get("/api/projects/{pid}/files", response_model=List[FileItem], tags=["Projects"])
def get_project_files(pid: str):
    """Retrieve all scanned source files in the project."""
    repo = get_graph_repository()
    files = repo.get_project_files(pid)
    return [FileItem(**f) for f in files]


@app.get("/api/projects/{pid}/files/{file_id:path}", response_model=FileDetailResponse, tags=["Projects"])
def get_file_details(pid: str, file_id: str):
    """Retrieve safe metadata, symbols, and findings for a specific file."""
    repo = get_graph_repository()
    detail = repo.get_file_details(pid, file_id)
    if not detail:
        raise HTTPException(status_code=404, detail="File metadata not found in this project.")
    return FileDetailResponse(**detail)


@app.post("/api/projects/{pid}/ai", response_model=AIReviewResponse, tags=["AI Review"])
def generate_ai_review(pid: str):
    """Generate architecture and security review using configured AI provider or offline fallback."""
    repo = get_graph_repository()
    summary = repo.get_project_summary(pid)
    if not summary:
        raise ProjectNotFoundError(pid)

    findings_res = repo.get_project_findings(pid, limit=100)
    findings = findings_res.get("findings", [])

    ai_reviewer = get_ai_reviewer()
    review = ai_reviewer.generate_review(summary, findings)
    return AIReviewResponse(**review)


@app.get("/api/projects/{pid}/export", tags=["Projects"])
def export_project_json(pid: str):
    """Export the complete scan report and graph summary as JSON."""
    repo = get_graph_repository()
    summary = repo.get_project_summary(pid)
    if not summary:
        raise ProjectNotFoundError(pid)

    findings = repo.get_project_findings(pid, limit=1000)
    files = repo.get_project_files(pid)
    graph = repo.get_project_graph(pid)

    return JSONResponse(
        content={
            "project_id": pid,
            "export_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "summary": summary,
            "findings": findings["findings"],
            "files": files,
            "graph": {
                "total_nodes": graph["total_nodes"],
                "total_edges": graph["total_edges"]
            }
        },
        headers={"Content-Disposition": f"attachment; filename=codegraph_report_{pid}.json"}
    )


@app.delete("/api/projects/{pid}", tags=["Projects"])
def delete_project(pid: str):
    """Delete a project and its associated graph nodes safely."""
    repo = get_graph_repository()
    summary = repo.get_project_summary(pid)
    if not summary:
        raise ProjectNotFoundError(pid)

    repo.delete_project(pid)
    return {"message": f"Project '{pid}' deleted successfully.", "project_id": pid}


# ------------------------------------------------------------------------------
# Frontend Static Files & SPA Route
# ------------------------------------------------------------------------------

frontend_dir = settings.frontend_dir

if frontend_dir.is_dir():
    # Mount css and js
    css_dir = frontend_dir / "css"
    js_dir = frontend_dir / "js"
    if css_dir.is_dir():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.is_dir():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

    @app.get("/", include_in_schema=False)
    def serve_frontend_index():
        index_file = frontend_dir / "index.html"
        if index_file.is_file():
            return FileResponse(str(index_file))
        return JSONResponse({"message": "CodeGraph AI API is running. Frontend index.html not found."})
