"""
Unit tests for CodebaseAnalyzer and SymbolExtractor.
"""

import pytest
import tempfile
import os
from pathlib import Path
from backend.app.analyzer import CodebaseAnalyzer, SymbolExtractor


@pytest.fixture
def temp_project_dir():
    """Create a temporary multi-file project directory for testing."""
    with tempfile.TemporaryDirectory(prefix="test_proj_") as tmp_dir:
        root = Path(tmp_dir)

        # File 1: app.py
        app_file = root / "app.py"
        app_file.write_text(
            """
import os
import requests
from utils import calculate_sum, HelperService
from database import connect_db

def run_application():
    connect_db()
    total = calculate_sum(10, 20)
    service = HelperService()
    return total

async def async_worker():
    pass
""",
            encoding="utf-8"
        )

        # File 2: utils.py
        utils_file = root / "utils.py"
        utils_file.write_text(
            """
import math

class HelperService:
    def execute(self):
        return True

def calculate_sum(a, b):
    return a + b
""",
            encoding="utf-8"
        )

        # File 3: database.py
        db_file = root / "database.py"
        db_file.write_text(
            """
def connect_db():
    return "connected"
""",
            encoding="utf-8"
        )

        # Ignored directory: node_modules and .venv
        node_dir = root / "node_modules" / "some_pkg"
        node_dir.mkdir(parents=True)
        (node_dir / "index.js").write_text("console.log('ignored');", encoding="utf-8")

        venv_dir = root / ".venv" / "Lib"
        venv_dir.mkdir(parents=True)
        (venv_dir / "lib.py").write_text("x = 1", encoding="utf-8")

        yield root


def test_file_discovery_and_ignored_dirs(temp_project_dir):
    """Verify scanner discovers project files and ignores node_modules and .venv."""
    analyzer = CodebaseAnalyzer(temp_project_dir)
    res = analyzer.analyze()

    file_paths = [f["path"] for f in res["files"]]
    assert "app.py" in file_paths
    assert "utils.py" in file_paths
    assert "database.py" in file_paths

    # Ignored directories must not be present
    assert not any("node_modules" in p for p in file_paths)
    assert not any(".venv" in p for p in file_paths)


def test_function_and_class_extraction(temp_project_dir):
    """Verify extraction of functions, async functions, and classes."""
    analyzer = CodebaseAnalyzer(temp_project_dir)
    res = analyzer.analyze()

    symbols = res["symbols"]
    func_names = [s["name"] for s in symbols if s["type"] in ("function", "method")]
    class_names = [s["name"] for s in symbols if s["type"] == "class"]

    assert "run_application" in func_names
    assert "async_worker" in func_names
    assert "calculate_sum" in func_names
    assert "HelperService.execute" in func_names
    assert "HelperService" in class_names


def test_import_and_dependency_resolution(temp_project_dir):
    """Verify internal dependencies and external packages are correctly categorized."""
    analyzer = CodebaseAnalyzer(temp_project_dir)
    res = analyzer.analyze()

    # Internal file dependencies: app.py depends on utils.py and database.py
    internal_deps = res["internal_dependencies"]
    targets = [d["target_file"] for d in internal_deps if d["from"] == "file:app.py"]
    assert "utils.py" in targets
    assert "database.py" in targets

    # External dependencies: requests, math (os is built-in but captured or external)
    external_pkgs = {p["package"] for p in res["external_dependencies"]}
    assert "requests" in external_pkgs


def test_function_calls_resolution(temp_project_dir):
    """Verify call graph extraction resolves caller to callee."""
    analyzer = CodebaseAnalyzer(temp_project_dir)
    res = analyzer.analyze()

    calls = res["function_calls"]
    callee_names = [c["callee_name"] for c in calls]
    assert "connect_db" in callee_names
    assert "calculate_sum" in callee_names


def test_syntax_error_resilience():
    """Verify that a Python file with invalid syntax is handled without crashing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        bad_file = root / "broken.py"
        bad_file.write_text("def broken_syntax( { ::: invalid python code", encoding="utf-8")

        good_file = root / "valid.py"
        good_file.write_text("def ok(): return 1", encoding="utf-8")

        analyzer = CodebaseAnalyzer(root)
        res = analyzer.analyze()

        # Both files are discovered, valid file is parsed, broken file doesn't crash scanner
        file_paths = [f["path"] for f in res["files"]]
        assert "broken.py" in file_paths
        assert "valid.py" in file_paths


def test_empty_project():
    """Verify behavior on an empty directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        analyzer = CodebaseAnalyzer(Path(tmp_dir))
        res = analyzer.analyze()
        assert res["stats"]["files_scanned"] == 0
        assert res["stats"]["lines_of_code"] == 0
        assert len(res["files"]) == 0
        assert len(res["symbols"]) == 0
