"""
CodeGraph AI - Code Analyzer Engine
Parses Python (AST) and JS/PHP (conservative regex), extracting files, symbols,
internal dependencies, external packages, function call graphs, and security findings.
"""

import ast
import re
import os
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from backend.app.security_scanner import scan_file_content

IGNORED_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    "dist", "build", "vendor", ".pytest_cache", ".idea", ".vscode",
    "target", "out", ".mypy_cache"
}

MAX_FILE_BYTES = 1024 * 1024  # 1 MB max file size for analysis
MAX_TOTAL_FILES = 500


class SymbolExtractor(ast.NodeVisitor):
    """Extracts classes, functions, and function call relationships from Python AST."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: List[Dict[str, Any]] = []
        self.calls: List[Dict[str, Any]] = []
        self._current_function: Optional[str] = None
        self._current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_name = node.name
        symbol_id = f"sym:{self.file_path}::{class_name}"
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]

        self.symbols.append({
            "id": symbol_id,
            "name": class_name,
            "type": "class",
            "file": self.file_path,
            "line": node.lineno,
            "bases": bases,
            "methods_count": len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
        })

        prev_class = self._current_class
        self._current_class = class_name
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node, is_async=True)

    def _handle_func(self, node: ast.AST, is_async: bool):
        func_name = getattr(node, "name")
        full_name = f"{self._current_class}.{func_name}" if self._current_class else func_name
        symbol_id = f"sym:{self.file_path}::{full_name}"

        self.symbols.append({
            "id": symbol_id,
            "name": full_name,
            "type": "method" if self._current_class else "function",
            "file": self.file_path,
            "line": getattr(node, "lineno", 1),
            "is_async": is_async,
            "args_count": len(getattr(node, "args").args),
            "class_name": self._current_class
        })

        prev_func = self._current_function
        self._current_function = full_name
        self.generic_visit(node)
        self._current_function = prev_func

    def visit_Call(self, node: ast.Call):
        if self._current_function:
            callee_name = ""
            if isinstance(node.func, ast.Name):
                callee_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee_name = node.func.attr

            if callee_name and not callee_name.startswith("__"):
                self.calls.append({
                    "caller_file": self.file_path,
                    "caller_func": self._current_function,
                    "caller_id": f"sym:{self.file_path}::{self._current_function}",
                    "callee_name": callee_name,
                    "line": getattr(node, "lineno", 1)
                })

        self.generic_visit(node)


class CodebaseAnalyzer:
    """Discovers, parses, and resolves architecture relationships across supported source files."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.files: List[Dict[str, Any]] = []
        self.symbols: List[Dict[str, Any]] = []
        self.internal_dependencies: List[Dict[str, Any]] = []  # from_file -> to_file
        self.external_dependencies: List[Dict[str, Any]] = []  # file -> package
        self.function_calls: List[Dict[str, Any]] = []         # caller_id -> callee_id
        self.findings: List[Dict[str, Any]] = []
        self._file_set: Set[str] = set()
        self._module_to_file: Dict[str, str] = {}
        self._symbols_by_name: Dict[str, List[Dict[str, Any]]] = {}

    def analyze(self) -> Dict[str, Any]:
        """Main analysis pipeline."""
        self._discover_files()
        self._parse_files()
        self._resolve_symbol_calls()
        
        # Calculate summary statistics
        total_loc = sum(f["loc"] for f in self.files)
        total_functions = sum(1 for s in self.symbols if s["type"] in ("function", "method"))
        total_classes = sum(1 for s in self.symbols if s["type"] == "class")
        unique_packages = len({p["package"] for p in self.external_dependencies})

        return {
            "files": self.files,
            "symbols": self.symbols,
            "internal_dependencies": self.internal_dependencies,
            "external_dependencies": self.external_dependencies,
            "function_calls": self.function_calls,
            "findings": self.findings,
            "stats": {
                "files_scanned": len(self.files),
                "lines_of_code": total_loc,
                "functions_count": total_functions,
                "classes_count": total_classes,
                "packages_count": unique_packages,
                "findings_count": len(self.findings)
            }
        }

    def _discover_files(self):
        """Walk root_dir skipping ignored directories and oversized/binary files."""
        for root, dirs, filenames in os.walk(self.root_dir):
            # Prune ignored directories in place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in (".py", ".js", ".php"):
                    full_path = Path(root) / fname
                    try:
                        if full_path.stat().st_size > MAX_FILE_BYTES:
                            continue
                        rel_path = full_path.relative_to(self.root_dir).as_posix()
                        self._file_set.add(rel_path)

                        # Map module names for python import resolution
                        if ext == ".py":
                            mod_name = rel_path.replace("/", ".").removesuffix(".py")
                            if mod_name.endswith(".__init__"):
                                mod_name = mod_name.removesuffix(".__init__")
                            self._module_to_file[mod_name] = rel_path
                            # Base name mapping e.g. "utils" -> "utils.py"
                            base_no_ext = Path(rel_path).stem
                            if base_no_ext not in self._module_to_file:
                                self._module_to_file[base_no_ext] = rel_path

                        if len(self._file_set) >= MAX_TOTAL_FILES:
                            return
                    except (OSError, PermissionError):
                        continue

    def _parse_files(self):
        """Parse each discovered file."""
        for rel_path in sorted(self._file_set):
            full_path = self.root_dir / rel_path
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.splitlines()
            loc = len(lines)
            ext = Path(rel_path).suffix.lower()
            lang = "python" if ext == ".py" else ("javascript" if ext == ".js" else "php")
            file_id = f"file:{rel_path}"

            self.files.append({
                "id": file_id,
                "path": rel_path,
                "name": Path(rel_path).name,
                "language": lang,
                "loc": loc
            })

            # Run security scanner on file
            findings = scan_file_content(rel_path, content, lang)
            self.findings.extend(findings)

            if lang == "python":
                self._parse_python(rel_path, content, file_id)
            elif lang == "javascript":
                self._parse_javascript(rel_path, content, file_id)
            elif lang == "php":
                self._parse_php(rel_path, content, file_id)

    def _parse_python(self, rel_path: str, content: str, file_id: str):
        """Parse Python source file with AST."""
        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError:
            return  # Safely continue on syntax error

        # Extract symbols and function calls
        extractor = SymbolExtractor(rel_path)
        extractor.visit(tree)
        for sym in extractor.symbols:
            self.symbols.append(sym)
            self._symbols_by_name.setdefault(sym["name"], []).append(sym)
            if "." in sym["name"]:
                short_name = sym["name"].split(".")[-1]
                self._symbols_by_name.setdefault(short_name, []).append(sym)

        # Store raw calls for second-pass resolution
        self.function_calls.extend(extractor.calls)

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._resolve_python_import(rel_path, alias.name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                # Handle relative imports (dots)
                if node.level > 0:
                    current_parts = Path(rel_path).parent.as_posix().split("/")
                    if current_parts == ["."]:
                        current_parts = []
                    up = node.level - 1
                    base_parts = current_parts[:-up] if up > 0 else current_parts
                    if module_name:
                        base_parts.append(module_name)
                    resolved_mod = ".".join([p for p in base_parts if p])
                    self._resolve_python_import(rel_path, resolved_mod)
                else:
                    self._resolve_python_import(rel_path, module_name)

    def _resolve_python_import(self, from_file: str, module_name: str):
        """Resolve import statement to internal file or external package."""
        if not module_name:
            return

        # Check internal project mapping
        target_file = self._module_to_file.get(module_name)
        if not target_file:
            # Check prefix e.g. "backend.app.database" -> "backend/app/database.py"
            cand_path = module_name.replace(".", "/") + ".py"
            if cand_path in self._file_set:
                target_file = cand_path
            elif (module_name.replace(".", "/") + "/__init__.py") in self._file_set:
                target_file = module_name.replace(".", "/") + "/__init__.py"

        if target_file and target_file != from_file:
            # Internal dependency
            dep = {"from": f"file:{from_file}", "to": f"file:{target_file}", "target_file": target_file}
            if dep not in self.internal_dependencies:
                self.internal_dependencies.append(dep)
        else:
            # External dependency (top-level package)
            pkg = module_name.split(".")[0]
            if pkg and pkg not in ("__future__", "builtins"):
                entry = {"file": from_file, "package": pkg}
                if entry not in self.external_dependencies:
                    self.external_dependencies.append(entry)

    def _parse_javascript(self, rel_path: str, content: str, file_id: str):
        """Conservative regex extraction for JavaScript."""
        lines = content.splitlines()

        # Functions: function name(...) or const name = (...) =>
        func_patterns = [
            re.compile(r'\bfunction\s+([a-zA-Z0-9_$]+)\s*\('),
            re.compile(r'\b(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>'),
            re.compile(r'\b(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*function\b')
        ]
        class_pattern = re.compile(r'\bclass\s+([a-zA-Z0-9_$]+)')
        import_pattern = re.compile(r'\bimport\s+.*?from\s+["\']([^"\']+)["\']')
        require_pattern = re.compile(r'\brequire\s*\(\s*["\']([^"\']+)["\']\s*\)')

        for idx, line in enumerate(lines, start=1):
            # Classes
            cm = class_pattern.search(line)
            if cm:
                cname = cm.group(1)
                sym = {
                    "id": f"sym:{rel_path}::{cname}",
                    "name": cname,
                    "type": "class",
                    "file": rel_path,
                    "line": idx,
                    "methods_count": 0
                }
                self.symbols.append(sym)
                self._symbols_by_name.setdefault(cname, []).append(sym)

            # Functions
            for fp in func_patterns:
                fm = fp.search(line)
                if fm:
                    fname = fm.group(1)
                    sym = {
                        "id": f"sym:{rel_path}::{fname}",
                        "name": fname,
                        "type": "function",
                        "file": rel_path,
                        "line": idx,
                        "is_async": "async" in line,
                        "args_count": 0
                    }
                    self.symbols.append(sym)
                    self._symbols_by_name.setdefault(fname, []).append(sym)
                    break

            # Imports
            im = import_pattern.search(line) or require_pattern.search(line)
            if im:
                target = im.group(1)
                if target.startswith("."):
                    # Relative import
                    clean_target = (Path(rel_path).parent / target).as_posix()
                    matched = None
                    for cand in (clean_target + ".js", clean_target + "/index.js", clean_target):
                        if cand in self._file_set:
                            matched = cand
                            break
                    if matched and matched != rel_path:
                        dep = {"from": f"file:{rel_path}", "to": f"file:{matched}", "target_file": matched}
                        if dep not in self.internal_dependencies:
                            self.internal_dependencies.append(dep)
                else:
                    pkg = target.split("/")[0]
                    entry = {"file": rel_path, "package": pkg}
                    if entry not in self.external_dependencies:
                        self.external_dependencies.append(entry)

    def _parse_php(self, rel_path: str, content: str, file_id: str):
        """Conservative regex extraction for PHP."""
        lines = content.splitlines()
        func_pattern = re.compile(r'\bfunction\s+([a-zA-Z0-9_]+)\s*\(')
        class_pattern = re.compile(r'\bclass\s+([a-zA-Z0-9_]+)')
        include_pattern = re.compile(r'\b(?:include|require|include_once|require_once)\s*\(?\s*["\']([^"\']+)["\']')

        for idx, line in enumerate(lines, start=1):
            cm = class_pattern.search(line)
            if cm:
                cname = cm.group(1)
                sym = {
                    "id": f"sym:{rel_path}::{cname}",
                    "name": cname,
                    "type": "class",
                    "file": rel_path,
                    "line": idx
                }
                self.symbols.append(sym)
                self._symbols_by_name.setdefault(cname, []).append(sym)

            fm = func_pattern.search(line)
            if fm:
                fname = fm.group(1)
                sym = {
                    "id": f"sym:{rel_path}::{fname}",
                    "name": fname,
                    "type": "function",
                    "file": rel_path,
                    "line": idx
                }
                self.symbols.append(sym)
                self._symbols_by_name.setdefault(fname, []).append(sym)

            inc = include_pattern.search(line)
            if inc:
                target = inc.group(1)
                target_posix = target.replace("\\", "/")
                # Check match against project files
                for f in self._file_set:
                    if f.endswith(target_posix) and f != rel_path:
                        dep = {"from": f"file:{rel_path}", "to": f"file:{f}", "target_file": f}
                        if dep not in self.internal_dependencies:
                            self.internal_dependencies.append(dep)

    def _resolve_symbol_calls(self):
        """Match caller function to callee symbol node without hallucinating."""
        resolved_calls = []
        for call in self.function_calls:
            callee_name = call["callee_name"]
            # Look up symbols with this name
            candidates = self._symbols_by_name.get(callee_name, [])
            if len(candidates) == 1:
                # Unambiguous target
                target = candidates[0]
                resolved_calls.append({
                    "caller_id": call["caller_id"],
                    "callee_id": target["id"],
                    "callee_name": callee_name,
                    "line": call["line"]
                })
            elif len(candidates) > 1:
                # Disambiguate by caller's own file first
                same_file = [c for c in candidates if c["file"] == call["caller_file"]]
                if len(same_file) == 1:
                    resolved_calls.append({
                        "caller_id": call["caller_id"],
                        "callee_id": same_file[0]["id"],
                        "callee_name": callee_name,
                        "line": call["line"]
                    })
        self.function_calls = resolved_calls
