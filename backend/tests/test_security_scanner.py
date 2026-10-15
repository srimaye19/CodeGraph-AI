"""
Unit tests for Security Scanner (Rules SEC001 through SEC010).
Tests both positive matches and negative/safe cases to ensure false-positive reduction.
"""

import pytest
from backend.app.security_scanner import scan_file_content


def test_sec001_eval_exec():
    """SEC001: Detect eval and exec calls; ignore safe code."""
    vulnerable_py = """
def run_dynamic(user_input):
    return eval(user_input)

def execute_snippet(code):
    exec(code)
"""
    findings = scan_file_content("vuln.py", vulnerable_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert rule_ids.count("SEC001") == 2

    # Negative test: comment mentioning eval
    safe_py = """
# This function does not use eval() or exec()
def safe_calc():
    return 1 + 1
"""
    safe_findings = scan_file_content("safe.py", safe_py, "python")
    assert "SEC001" not in [f["rule_id"] for f in safe_findings]


def test_sec002_and_sec003_sql_injection():
    """SEC002 & SEC003: Detect formatted queries and raw request input."""
    vuln_py = """
def query_user(user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

def search_query(request):
    cursor.execute("SELECT * FROM items WHERE name = " + request.args['query'])
"""
    findings = scan_file_content("db.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC002" in rule_ids or "SEC003" in rule_ids

    # Negative test: Parameterized query
    safe_py = """
def safe_query(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
"""
    safe_findings = scan_file_content("safe_db.py", safe_py, "python")
    assert "SEC002" not in [f["rule_id"] for f in safe_findings]
    assert "SEC003" not in [f["rule_id"] for f in safe_findings]


def test_sec004_unsafe_shell():
    """SEC004: Detect shell=True and os.system."""
    vuln_py = """
import os
import subprocess

def run_cmd(cmd):
    os.system(cmd)
    subprocess.call(cmd, shell=True)
"""
    findings = scan_file_content("cmd.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC004" in rule_ids

    # Negative test: subprocess with shell=False / list of args
    safe_py = """
import subprocess
def safe_cmd():
    subprocess.run(["ls", "-la"], shell=False)
"""
    safe_findings = scan_file_content("safe_cmd.py", safe_py, "python")
    assert "SEC004" not in [f["rule_id"] for f in safe_findings]


def test_sec005_hardcoded_credentials():
    """SEC005: Detect hardcoded API keys and secrets."""
    vuln_py = """
API_KEY = "sk-live-9876543210abcdef12345"
DB_PASSWORD = "SuperSecretDbPassword123!"
"""
    findings = scan_file_content("config.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC005" in rule_ids

    # Negative test: environment variable loading or placeholder
    safe_py = """
import os
API_KEY = os.getenv("API_KEY", "")
PASSWORD = "your-password-here"
"""
    safe_findings = scan_file_content("safe_config.py", safe_py, "python")
    assert "SEC005" not in [f["rule_id"] for f in safe_findings]


def test_sec006_unsafe_deserialization():
    """SEC006: Detect pickle.loads and yaml.load without SafeLoader."""
    vuln_py = """
import pickle
import yaml

def load_data(blob):
    obj = pickle.loads(blob)
    cfg = yaml.load(blob)
    return obj
"""
    findings = scan_file_content("loader.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC006" in rule_ids

    # Negative test: yaml.safe_load
    safe_py = """
import yaml
def load_safe(blob):
    return yaml.safe_load(blob)
"""
    safe_findings = scan_file_content("safe_loader.py", safe_py, "python")
    assert "SEC006" not in [f["rule_id"] for f in safe_findings]


def test_sec007_weak_cryptographic_hash():
    """SEC007: Detect MD5 and SHA-1 usage."""
    vuln_py = """
import hashlib
def hash_val(val):
    return hashlib.md5(val).hexdigest()

def hash_sha1(val):
    return hashlib.sha1(val).hexdigest()
"""
    findings = scan_file_content("hasher.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC007" in rule_ids

    # Negative test: SHA-256
    safe_py = """
import hashlib
def safe_hash(val):
    return hashlib.sha256(val).hexdigest()
"""
    safe_findings = scan_file_content("safe_hasher.py", safe_py, "python")
    assert "SEC007" not in [f["rule_id"] for f in safe_findings]


def test_sec008_debug_mode():
    """SEC008: Detect DEBUG = True or app.run(debug=True)."""
    vuln_py = """
DEBUG = True
def start(app):
    app.run(debug=True)
"""
    findings = scan_file_content("server.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC008" in rule_ids

    safe_py = "DEBUG = False"
    safe_findings = scan_file_content("safe_server.py", safe_py, "python")
    assert "SEC008" not in [f["rule_id"] for f in safe_findings]


def test_sec009_xss_sink_js():
    """SEC009: Detect innerHTML and document.write in JavaScript."""
    vuln_js = """
function renderUser(name) {
    document.getElementById('profile').innerHTML = "<b>" + name + "</b>";
    document.write(name);
}
"""
    findings = scan_file_content("app.js", vuln_js, "javascript")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC009" in rule_ids

    safe_js = """
function renderUserSafe(name) {
    document.getElementById('profile').textContent = name;
}
"""
    safe_findings = scan_file_content("safe.js", safe_js, "javascript")
    assert "SEC009" not in [f["rule_id"] for f in safe_findings]


def test_sec010_tls_verification_disabled():
    """SEC010: Detect verify=False in HTTP calls."""
    vuln_py = """
import requests
def fetch_insecure():
    return requests.get("https://internal.service", verify=False)
"""
    findings = scan_file_content("client.py", vuln_py, "python")
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC010" in rule_ids

    safe_py = """
import requests
def fetch_secure():
    return requests.get("https://internal.service", verify=True)
"""
    safe_findings = scan_file_content("safe_client.py", safe_py, "python")
    assert "SEC010" not in [f["rule_id"] for f in safe_findings]
