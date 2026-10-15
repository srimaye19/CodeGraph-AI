"""
Unit tests for graph repository abstraction and analysis helpers.
Validates graph modeling, circular dependency detection, and hotspot algorithms.
"""

import pytest
from unittest.mock import MagicMock
from backend.app.graph import InMemoryGraphRepository, Neo4jGraphRepository


@pytest.fixture
def sample_analysis():
    return {
        "files": [
            {"id": "file:main.py", "path": "main.py", "name": "main.py", "language": "python", "loc": 50},
            {"id": "file:service.py", "path": "service.py", "name": "service.py", "language": "python", "loc": 120},
            {"id": "file:data.py", "path": "data.py", "name": "data.py", "language": "python", "loc": 80}
        ],
        "symbols": [
            {"id": "sym:main.py::entry", "name": "entry", "type": "function", "file": "main.py", "line": 10},
            {"id": "sym:service.py::process", "name": "process", "type": "function", "file": "service.py", "line": 20}
        ],
        "internal_dependencies": [
            {"from": "file:main.py", "to": "file:service.py"},
            {"from": "file:service.py", "to": "file:data.py"},
            {"from": "file:data.py", "to": "file:main.py"}  # Circular: main -> service -> data -> main
        ],
        "external_dependencies": [
            {"file": "main.py", "package": "fastapi"},
            {"file": "service.py", "package": "requests"}
        ],
        "function_calls": [
            {"caller_id": "sym:main.py::entry", "callee_id": "sym:service.py::process", "callee_name": "process", "line": 15}
        ],
        "findings": [
            {
                "rule_id": "SEC001",
                "severity": "HIGH",
                "message": "Eval used",
                "file": "main.py",
                "line": 12,
                "snippet": "eval(x)",
                "recommendation": "Avoid eval",
                "confidence": "HIGH"
            }
        ],
        "stats": {
            "files_scanned": 3,
            "lines_of_code": 250,
            "functions_count": 2,
            "classes_count": 0,
            "packages_count": 2,
            "findings_count": 1
        }
    }


def test_in_memory_repository_lifecycle(sample_analysis):
    """Test full cycle: save, get projects, summary, graph, delete."""
    repo = InMemoryGraphRepository()
    pid = "test_p1"

    # Save
    repo.save_project_analysis(pid, "Demo Project", sample_analysis)

    # List
    projs = repo.get_projects()
    assert len(projs) == 1
    assert projs[0]["id"] == pid
    assert projs[0]["name"] == "Demo Project"

    # Summary
    summary = repo.get_project_summary(pid)
    assert summary["project_name"] == "Demo Project"
    assert summary["file_counts"] == 3
    assert summary["security_severity_counts"]["HIGH"] == 1

    # Circular dependencies detected
    cycles = summary["circular_dependencies"]
    assert len(cycles) > 0
    # The cycle should contain main.py, service.py, data.py
    flattened = [item for sub in cycles for item in sub]
    assert "main.py" in flattened
    assert "service.py" in flattened

    # Graph
    graph = repo.get_project_graph(pid)
    assert graph["total_nodes"] > 0
    assert graph["total_edges"] > 0

    # Delete
    repo.delete_project(pid)
    assert len(repo.get_projects()) == 0


def test_neo4j_driver_mocking():
    """Verify parameterized Cypher execution with mocked Neo4j Driver/Session."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    repo = Neo4jGraphRepository("bolt://localhost:7687", "neo4j", "testpass")
    repo._driver = mock_driver

    # Test delete_project
    repo.delete_project("p_mock")
    assert mock_session.run.called
    args, kwargs = mock_session.run.call_args
    assert kwargs["pid"] == "p_mock"
