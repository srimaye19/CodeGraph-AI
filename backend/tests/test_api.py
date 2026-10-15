"""
Integration tests for FastAPI endpoints:
Health, ZIP upload, Path scanning, Graph retrieval, Findings, and AI reviews.
"""

import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    """GET /api/health returns status ok and structured neo4j health."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "neo4j" in data
    assert "connected" in data["neo4j"]
    assert "configured" in data["neo4j"]


def test_scan_path_valid(client, tmp_path):
    """POST /api/scan/path scans a local directory successfully."""
    # Create sample files
    f1 = tmp_path / "hello.py"
    f1.write_text("def greet(): return 'hello'", encoding="utf-8")

    resp = client.post("/api/scan/path", json={"path": str(tmp_path), "project_name": "Test Local"})
    assert resp.status_code == 200
    data = resp.json()
    assert "project_id" in data
    assert data["stats"]["files_scanned"] == 1
    assert data["stats"]["functions_count"] == 1

    pid = data["project_id"]

    # Test GET summary
    s_resp = client.get(f"/api/projects/{pid}/summary")
    assert s_resp.status_code == 200
    assert s_resp.json()["file_counts"] == 1

    # Test GET graph
    g_resp = client.get(f"/api/projects/{pid}/graph")
    assert g_resp.status_code == 200
    assert g_resp.json()["total_nodes"] >= 1

    # Test AI Review
    ai_resp = client.post(f"/api/projects/{pid}/ai")
    assert ai_resp.status_code == 200
    assert "architecture_overview" in ai_resp.json()

    # Test Export
    exp_resp = client.get(f"/api/projects/{pid}/export")
    assert exp_resp.status_code == 200
    assert "summary" in exp_resp.json()

    # Test Delete
    del_resp = client.delete(f"/api/projects/{pid}")
    assert del_resp.status_code == 200


def test_scan_path_invalid_and_forbidden(client):
    """POST /api/scan/path rejects non-existent paths and root system paths."""
    # Non-existent
    bad_resp = client.post("/api/scan/path", json={"path": "C:/NonExistentPath12345"})
    assert bad_resp.status_code in (400, 500)

    # Root system forbidden
    root_resp = client.post("/api/scan/path", json={"path": "/"})
    assert root_resp.status_code in (400, 500)


def test_scan_upload_valid_zip(client):
    """POST /api/scan/upload accepts and extracts valid ZIP archive."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("module.py", "def test_func():\n    return 42\n")
    zip_buffer.seek(0)

    resp = client.post(
        "/api/scan/upload",
        files={"file": ("project.zip", zip_buffer.getvalue(), "application/zip")},
        data={"project_name": "Zip Test"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "project_id" in data
    assert data["stats"]["files_scanned"] == 1


def test_scan_upload_traversal_zip_rejected(client):
    """POST /api/scan/upload rejects ZIP archives containing directory traversal ('..')."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("../traversal.py", "malicious_code = True")
    zip_buffer.seek(0)

    resp = client.post(
        "/api/scan/upload",
        files={"file": ("exploit.zip", zip_buffer.getvalue(), "application/zip")}
    )
    assert resp.status_code == 400
    assert "traversal" in resp.text.lower()
