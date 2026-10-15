"""
CodeGraph AI - Security Scanner Module
Performs AST-based (Python) and pattern-based (JS, PHP) static security analysis.
Identifies security risks without executing scanned code.
"""

import ast
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


class SecurityRule:
    """Definition of a security rule."""
    def __init__(
        self,
        rule_id: str,
        name: str,
        severity: str,
        cwe_id: str,
        description: str,
        recommendation: str
    ):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity  # HIGH, MEDIUM, LOW
        self.cwe_id = cwe_id
        self.description = description
        self.recommendation = recommendation


RULES = {
    "SEC001": SecurityRule(
        "SEC001", "Dynamic Code Execution", "HIGH", "CWE-95",
        "Potential unsafe dynamic code execution using eval() or exec().",
        "Avoid dynamic evaluation of code. Use structured parsers or safe dispatch tables instead."
    ),
    "SEC002": SecurityRule(
        "SEC002", "SQL Injection Risk", "HIGH", "CWE-89",
        "Potential SQL injection from dynamically formatted or concatenated query strings.",
        "Use parameterized queries (prepared statements) or an ORM with parameter binding."
    ),
    "SEC003": SecurityRule(
        "SEC003", "Raw Request in Database Query", "HIGH", "CWE-89",
        "Direct concatenation of request input into database query execution.",
        "Sanitize and validate all user inputs; always bind parameters rather than building raw SQL."
    ),
    "SEC004": SecurityRule(
        "SEC004", "Unsafe Shell Command Execution", "HIGH", "CWE-78",
        "Potentially unsafe shell command execution via shell=True or system calls.",
        "Pass arguments as a list with shell=False, or use safe domain-specific libraries."
    ),
    "SEC005": SecurityRule(
        "SEC005", "Hardcoded Secret or Credential", "MEDIUM", "CWE-798",
        "Possible hardcoded credentials, API keys, or private secrets found in source.",
        "Move sensitive credentials into environment variables or a secure secret manager."
    ),
    "SEC006": SecurityRule(
        "SEC006", "Unsafe Deserialization", "HIGH", "CWE-502",
        "Unsafe deserialization pattern detected (pickle, yaml.load without SafeLoader, unserialize).",
        "Use safe serialization formats like JSON, or yaml.safe_load() rather than arbitrary object deserialization."
    ),
    "SEC007": SecurityRule(
        "SEC007", "Weak Cryptographic Hash", "LOW", "CWE-328",
        "Weak cryptographic hashing algorithm detected (MD5 or SHA-1).",
        "Upgrade to SHA-256, SHA-3, or password-hashing algorithms like Argon2id or bcrypt."
    ),
    "SEC008": SecurityRule(
        "SEC008", "Debug Mode Enabled", "LOW", "CWE-489",
        "Application debug mode or verbose error display appears to be enabled.",
        "Disable debug mode in production environments to prevent information disclosure."
    ),
    "SEC009": SecurityRule(
        "SEC009", "Potential XSS Sink", "MEDIUM", "CWE-79",
        "Potential Cross-Site Scripting (XSS) sink using innerHTML, document.write, or unescaped output.",
        "Use textContent, innerText, or context-aware template escaping libraries."
    ),
    "SEC010": SecurityRule(
        "SEC010", "TLS Verification Disabled", "HIGH", "CWE-295",
        "TLS/SSL certificate validation is explicitly disabled (verify=False or equivalent).",
        "Always enable TLS verification in production to prevent Man-in-the-Middle (MitM) attacks."
    )
}


class PythonASTSecurityVisitor(ast.NodeVisitor):
    """AST Visitor detecting security anti-patterns in Python code."""

    def __init__(self, relative_path: str, source_lines: List[str]):
        self.path = relative_path
        self.source_lines = source_lines
        self.findings: List[Dict[str, Any]] = []

    def _add_finding(self, rule_id: str, line_no: int, snippet: str, confidence: str = "HIGH", custom_msg: Optional[str] = None):
        rule = RULES.get(rule_id)
        if not rule:
            return
        self.findings.append({
            "rule_id": rule.rule_id,
            "severity": rule.severity,
            "message": custom_msg or rule.description,
            "file": self.path,
            "line": line_no,
            "snippet": snippet.strip(),
            "recommendation": rule.recommendation,
            "confidence": confidence,
            "cwe_id": rule.cwe_id
        })

    def _get_snippet(self, line_no: int) -> str:
        if 1 <= line_no <= len(self.source_lines):
            return self.source_lines[line_no - 1]
        return ""

    def visit_Call(self, node: ast.Call):
        func_name = ""
        line = getattr(node, "lineno", 1)
        snippet = self._get_snippet(line)

        # Detect function call name
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            # e.g., os.system, subprocess.call, yaml.load
            prefix = ""
            if isinstance(node.func.value, ast.Name):
                prefix = node.func.value.id + "."
            full_call = prefix + func_name

            # SEC001: eval / exec
            if full_call in ("builtins.eval", "builtins.exec"):
                self._add_finding("SEC001", line, snippet, confidence="HIGH")

            # SEC004: subprocess / os.system
            if full_call in ("os.system", "os.popen"):
                self._add_finding("SEC004", line, snippet, confidence="HIGH",
                                  custom_msg=f"Call to unsafe command function {full_call}.")
            elif prefix.startswith("subprocess."):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self._add_finding("SEC004", line, snippet, confidence="HIGH",
                                          custom_msg="subprocess called with shell=True.")

            # SEC006: Unsafe deserialization
            if full_call in ("pickle.loads", "pickle.load", "_pickle.loads", "_pickle.load"):
                self._add_finding("SEC006", line, snippet, confidence="HIGH",
                                  custom_msg=f"Unsafe deserialization using {full_call}.")
            elif full_call in ("yaml.load", "yaml.unsafe_load"):
                has_safe_loader = False
                for kw in node.keywords:
                    if kw.arg == "Loader":
                        if isinstance(kw.value, ast.Attribute) and kw.value.attr in ("SafeLoader", "CSafeLoader"):
                            has_safe_loader = True
                if not has_safe_loader and full_call != "yaml.safe_load":
                    self._add_finding("SEC006", line, snippet, confidence="HIGH",
                                      custom_msg="yaml.load called without SafeLoader.")

            # SEC007: Weak hash (MD5, SHA1)
            if full_call in ("hashlib.md5", "hashlib.sha1"):
                self._add_finding("SEC007", line, snippet, confidence="HIGH",
                                  custom_msg=f"Weak cryptographic hash {full_call}() used.")
            elif full_call == "hashlib.new" and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and str(first_arg.value).lower() in ("md5", "sha1"):
                    self._add_finding("SEC007", line, snippet, confidence="HIGH",
                                      custom_msg=f"Weak cryptographic hash algorithm '{first_arg.value}' used.")

            # SEC010: TLS verify=False
            for kw in node.keywords:
                if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    self._add_finding("SEC010", line, snippet, confidence="HIGH",
                                      custom_msg="TLS certificate verification disabled (verify=False).")

            # SEC008: debug=True in app.run or similar
            if func_name == "run":
                for kw in node.keywords:
                    if kw.arg == "debug" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self._add_finding("SEC008", line, snippet, confidence="HIGH",
                                          custom_msg="Application run with debug=True.")

            # SEC002 & SEC003: SQL execution checks
            if func_name in ("execute", "executemany", "raw_query"):
                if node.args:
                    query_arg = node.args[0]
                    # Formatted string: f"SELECT ... {var}"
                    if isinstance(query_arg, ast.JoinedStr):
                        sql_text = ""
                        for part in query_arg.values:
                            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                                sql_text += part.value
                        if any(k in sql_text.upper() for k in ("SELECT", "INSERT", "UPDATE", "DELETE", "WHERE")):
                            # Check if request parameter is in formatted values
                            is_raw_req = any("request" in ast.dump(v).lower() for v in query_arg.values)
                            if is_raw_req:
                                self._add_finding("SEC003", line, snippet, confidence="HIGH",
                                                  custom_msg="Database query directly incorporates raw request input.")
                            else:
                                self._add_finding("SEC002", line, snippet, confidence="HIGH",
                                                  custom_msg="Dynamic f-string formatting in SQL query execution.")
                    # Binary concatenation: "SELECT ... " + var
                    elif isinstance(query_arg, ast.BinOp) and isinstance(query_arg.op, (ast.Add, ast.Mod)):
                        dump_str = ast.dump(query_arg)
                        if any(k in snippet.upper() for k in ("SELECT", "INSERT", "UPDATE", "DELETE", "WHERE")):
                            if "request" in dump_str.lower():
                                self._add_finding("SEC003", line, snippet, confidence="HIGH",
                                                  custom_msg="Database query directly concatenates request input.")
                            else:
                                self._add_finding("SEC002", line, snippet, confidence="HIGH",
                                                  custom_msg="Dynamic string concatenation/formatting in SQL query execution.")

        # Standalone function names: eval, exec
        if func_name in ("eval", "exec"):
            self._add_finding("SEC001", line, snippet, confidence="HIGH")

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        line = getattr(node, "lineno", 1)
        snippet = self._get_snippet(line)

        # Check for DEBUG = True
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.upper()
                if var_name in ("DEBUG", "APP_DEBUG") and isinstance(node.value, ast.Constant) and node.value.value is True:
                    self._add_finding("SEC008", line, snippet, confidence="MEDIUM",
                                      custom_msg=f"{target.id} set to True in code.")

                # SEC005: Hardcoded credentials
                if any(sec in var_name for sec in ("PASSWORD", "SECRET", "API_KEY", "ACCESS_TOKEN", "PRIVATE_KEY")):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        # Filter out empty, placeholder, or obvious env lookups
                        placeholders = ("your-", "placeholder", "xxx", "dummy", "<your-")
                        if len(val) >= 6 and not any(p in val.lower() for p in placeholders):
                            self._add_finding("SEC005", line, snippet, confidence="MEDIUM",
                                              custom_msg=f"Potential hardcoded secret assigned to '{target.id}'.")

        self.generic_visit(node)


class RegexSecurityScanner:
    """Pattern-based security scanner for JS, PHP, and general text fallbacks."""

    PATTERNS = [
        # SEC001
        ("SEC001", re.compile(r'\b(eval\s*\(|exec\s*\(|window\.eval\s*\()'), "Potential dynamic code execution."),
        # SEC002
        ("SEC002", re.compile(r'(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+.*(\+|concat|`\s*\${)', re.IGNORECASE),
         "Dynamic SQL query concatenation detected."),
        # SEC003
        ("SEC003", re.compile(r'(SELECT|INSERT|UPDATE|DELETE).*\b(req\.(body|query|params)|\$_GET|\$_POST|\$_REQUEST)', re.IGNORECASE),
         "Raw request input embedded in SQL query."),
        # SEC004
        ("SEC004", re.compile(r'\b(child_process\.exec\s*\(|shell_exec\s*\(|system\s*\(|passthru\s*\(|exec\s*\()'),
         "Shell command execution invocation."),
        # SEC005
        ("SEC005", re.compile(r'(api_key|secret_key|password|jwt_secret)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{12,})["\']', re.IGNORECASE),
         "Potential hardcoded secret or API key."),
        # SEC006
        ("SEC006", re.compile(r'\bunserialize\s*\('), "Unsafe PHP object deserialization."),
        # SEC007
        ("SEC007", re.compile(r'\b(crypto\.createHash\s*\(\s*["\'](md5|sha1)["\']|md5\s*\(|sha1\s*\()', re.IGNORECASE),
         "Weak cryptographic hash usage (MD5/SHA1)."),
        # SEC008
        ("SEC008", re.compile(r'\b(display_errors\s*=\s*(1|On)|app\.set\(\s*["\']debug["\']\s*,\s*true\))', re.IGNORECASE),
         "Debug or verbose error display enabled."),
        # SEC009
        ("SEC009", re.compile(r'(\.innerHTML\s*=|document\.write\s*\(|dangerouslySetInnerHTML)', re.IGNORECASE),
         "Potential Cross-Site Scripting (XSS) sink."),
        # SEC010
        ("SEC010", re.compile(r'(rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["\']?0|CURLOPT_SSL_VERIFYPEER\s*,\s*(false|0))', re.IGNORECASE),
         "TLS verification disabled.")
    ]

    @classmethod
    def scan_lines(cls, relative_path: str, source_lines: List[str], language: str) -> List[Dict[str, Any]]:
        findings = []
        in_multiline_comment = False

        for idx, raw_line in enumerate(source_lines, start=1):
            line = raw_line.strip()

            # Handle multiline comments
            if "/*" in line:
                in_multiline_comment = True
            if in_multiline_comment:
                if "*/" in line:
                    in_multiline_comment = False
                continue

            # Skip single-line comments
            if line.startswith(("//", "#", "/*", "*")):
                continue

            for rule_id, pattern, desc in cls.PATTERNS:
                if pattern.search(line):
                    rule = RULES.get(rule_id)
                    if rule:
                        # Exclude false positives for test/example secrets
                        if rule_id == "SEC005" and any(x in line.lower() for x in ("placeholder", "example", "xxx", "test")):
                            continue
                        findings.append({
                            "rule_id": rule.rule_id,
                            "severity": rule.severity,
                            "message": desc,
                            "file": relative_path,
                            "line": idx,
                            "snippet": line,
                            "recommendation": rule.recommendation,
                            "confidence": "MEDIUM",
                            "cwe_id": rule.cwe_id
                        })
        return findings


def scan_file_content(relative_path: str, content: str, language: str) -> List[Dict[str, Any]]:
    """
    Run security analysis on file contents using AST for Python, and regex for JS/PHP.
    Returns a list of structured finding dictionaries.
    """
    lines = content.splitlines()
    findings: List[Dict[str, Any]] = []

    if language == "python":
        try:
            tree = ast.parse(content, filename=relative_path)
            visitor = PythonASTSecurityVisitor(relative_path, lines)
            visitor.visit(tree)
            findings.extend(visitor.findings)
        except SyntaxError:
            # If syntax error in python file, fallback to regex scanning
            findings.extend(RegexSecurityScanner.scan_lines(relative_path, lines, language))
    else:
        findings.extend(RegexSecurityScanner.scan_lines(relative_path, lines, language))

    return findings
