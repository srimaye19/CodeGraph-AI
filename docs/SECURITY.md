# CodeGraph AI — Security Analysis & Rules Guide

CodeGraph AI incorporates a dedicated static security engine inspecting Python AST nodes and JavaScript/PHP syntactic patterns to identify common security flaws and dangerous sinks.

---

## 1. Scanner Rules Catalog

| Rule ID | Name | Severity | CWE | Description |
|---|---|---|---|---|
| **SEC001** | Dynamic Code Execution | **HIGH** | CWE-95 | Unsafe execution via `eval()`, `exec()`, or `window.eval()`. |
| **SEC002** | SQL Injection Risk | **HIGH** | CWE-89 | Dynamic string formatting or concatenation in database queries. |
| **SEC003** | Raw Request in Query | **HIGH** | CWE-89 | Direct concatenation of HTTP request inputs into SQL execution. |
| **SEC004** | Shell Command Execution | **HIGH** | CWE-78 | Command execution via `shell=True`, `os.system()`, or `shell_exec()`. |
| **SEC005** | Hardcoded Secret/Key | **MEDIUM** | CWE-798 | Hardcoded API keys, private tokens, or passwords in source. |
| **SEC006** | Unsafe Deserialization | **HIGH** | CWE-502 | Deserialization of untrusted data via `pickle` or un-safe YAML loading. |
| **SEC007** | Weak Hash Function | **LOW** | CWE-328 | Usage of cryptographically broken hashes like MD5 or SHA-1. |
| **SEC008** | Debug Mode Enabled | **LOW** | CWE-489 | Framework debug flags or verbose error displays enabled. |
| **SEC009** | Potential XSS Sink | **MEDIUM** | CWE-79 | Unescaped DOM manipulation via `innerHTML` or `document.write()`. |
| **SEC010** | TLS Verification Disabled | **HIGH** | CWE-295 | Explicitly disabling TLS/SSL certificate verification (`verify=False`). |

---

## 2. In-Depth Rule Explanations & Remediation

### SEC001: Dynamic Code Execution (CWE-95)
- **Risk:** Dynamically evaluating untrusted code can result in Remote Code Execution (RCE).
- **Vulnerable:**
  ```python
  result = eval(user_query)
  ```
- **Remediation:**
  Use structured serialization parsers (such as `json.loads`) or safe mathematical expression parsers (`ast.literal_eval`).

### SEC002 & SEC003: SQL Injection (CWE-89)
- **Risk:** Unsanitized user inputs or formatted strings in SQL queries allow attackers to alter query logic, bypass authentication, or exfiltrate databases.
- **Vulnerable:**
  ```python
  cursor.execute(f"SELECT * FROM users WHERE email = '{user_email}'")
  ```
- **Remediation:**
  Use parameterized prepared statements:
  ```python
  cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))
  ```

### SEC004: Unsafe Shell Execution (CWE-78)
- **Risk:** Passing unvalidated arguments to a system shell can permit command injection.
- **Vulnerable:**
  ```python
  subprocess.call(f"ping -c 1 {host}", shell=True)
  ```
- **Remediation:**
  Pass arguments as a discrete list with `shell=False`:
  ```python
  subprocess.run(["ping", "-c", "1", host], shell=False, check=True)
  ```

### SEC006: Unsafe Deserialization (CWE-502)
- **Risk:** Python's `pickle` module can execute arbitrary code during deserialization via `__reduce__`.
- **Vulnerable:**
  ```python
  data = pickle.loads(untrusted_payload)
  config = yaml.load(raw_yaml)
  ```
- **Remediation:**
  Use JSON or safe YAML loaders:
  ```python
  config = yaml.safe_load(raw_yaml)
  ```

### SEC010: TLS Verification Disabled (CWE-295)
- **Risk:** Disabling certificate verification exposes encrypted traffic to Man-in-the-Middle (MitM) eavesdropping and tampering.
- **Vulnerable:**
  ```python
  requests.get("https://internal.service/api", verify=False)
  ```
- **Remediation:**
  Leave verification enabled (`verify=True`), or supply a trusted custom CA bundle (`verify="/path/to/custom-ca.pem"`).

---

## 3. Scanner Limitations & False Positives

1. **Static Heuristics:** CodeGraph AI detects indicators of risk, not definitive proof of exploitability.
2. **Dynamic Languages:** Runtime dynamic behavior, monkey-patching, and reflection cannot be fully verified through static inspection alone.
3. **Execution Safety:** Analyzed code is **never executed**. Scanning a malicious project file is completely safe.
4. **Environment Deployment:** The local path scanning endpoint (`/api/scan/path`) is intended for local developer workstations or authenticated internal networks and should **not** be exposed unauthenticated to the public internet.
