# CodeGraph AI 🚀
### AI-Powered Code Architecture Mapping and Security Analysis Using Neo4j

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-Aura%20Free%20%7C%205.x-008cc1.svg)](https://neo4j.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 22 Passed](https://img.shields.io/badge/Tests-22%20Passed-brightgreen.svg)]()

**CodeGraph AI** is an open-source developer platform that parses codebases into an interactive **Knowledge Graph** backed by **Neo4j**. It maps file dependencies, functions, classes, and call graphs while executing static security analysis to detect vulnerabilities (CWE-89, CWE-95, CWE-78, CWE-502, CWE-798, etc.) and identifying architectural bottlenecks such as circular imports and coupling hotspots.

---

## 📋 Table of Contents
- [Problem Statement & Objectives](#-problem-statement--objectives)
- [Key Features](#-key-features)
- [Supported Programming Languages](#-supported-programming-languages)
- [Architecture & Technology Stack](#️-architecture--technology-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Windows Installation & Setup](#-windows-installation--setup)
- [Configuration (.env.example)](#-configuration-envexample)
- [Running the Application](#-running-the-application)
- [Neo4j Aura Cloud Integration](#-neo4j-aura-cloud-integration)
- [Dashboard & Interactive API Docs](#-dashboard--interactive-api-docs)
- [Scanning Codebases & Demo Project](#-scanning-codebases--demo-project)
- [Security Findings & Architecture Analysis](#-security-findings--architecture-analysis)
- [Automated Testing](#-automated-testing)
- [REST API Endpoints](#-rest-api-endpoints)
- [Limitations, Troubleshooting & Future Enhancements](#-limitations-troubleshooting--future-enhancements)
- [License & Contributing](#-license--contributing)

---

## 🎯 Problem Statement & Objectives

### Problem Statement
Modern software projects rapidly accumulate architectural complexity. As repositories grow:
- **Opaque Dependencies:** Developers lose visibility into how modules interact, resulting in hidden circular imports and high-coupling hotspots.
- **Security Vulnerabilities:** Critical security risks (such as dynamic `eval` calls, raw SQL concatenations, command injection, and hardcoded credentials) slip through code reviews when reviewers lack structural context.
- **Slow Onboarding & Audit Friction:** Onboarding new engineers or preparing architecture compliance audits requires days of manual code reading.

### Objectives
1. **Structural Transparency:** Transform static source files into a rich, queryable knowledge graph.
2. **Deterministic Security Auditing:** Identify high-risk patterns via AST and lexical scanning without executing target code.
3. **Graph-Powered Insights:** Compute in-degree/out-degree hotspots and circular dependency cycles using graph traversal algorithms.
4. **Frictionless Developer Experience:** Provide one-click Windows startup scripts, an offline in-memory fallback, and full Neo4j Aura cloud database support.

---

## 🌟 Key Features

- 🕸️ **Interactive Knowledge Graph:** Visualizes source files, symbols, external packages, and security findings using `vis-network` with physics simulation and dynamic filtering by node type.
- 🛡️ **Static Security Scanner (SEC001 - SEC010):** AST-driven detection of code execution, SQL injections, shell execution, hardcoded keys, unsafe deserialization, weak hashes, debug flags, XSS sinks, and disabled TLS verification.
- 🔄 **Circular Dependency Detection:** Detects circular import loops across project modules to prevent runtime import deadlocks.
- 📊 **Coupling Hotspots Analysis:** Ranks files by in-degree (depended on by many) and out-degree (depends on many) to pinpoint high blast-radius files.
- 🤖 **Dual-Mode AI Architecture Review:**
  - Built-in **deterministic rule-based offline report engine** that produces comprehensive refactoring suggestions with zero external API dependencies.
  - Optional LLM integration with Google Gemini (`gemini-1.5-flash`) or OpenAI (`gpt-4o-mini`) configured via `.env`.
- ☁️ **Dual-Mode Persistence (Neo4j Aura Cloud & In-Memory Fallback):** Connects to Neo4j Aura Free or local Neo4j 5 over Bolt, with an automatic, thread-safe in-memory graph repository for offline development.
- 🔒 **Defensive Engineering:** ZIP Slip protection, path traversal defenses, upload size limits (25MB default), and parameterized Cypher queries.

---

## 💻 Supported Programming Languages

| Language | Extension | Analysis Depth | Extracted Elements |
|---|---|---|---|
| **Python** | `.py` | Abstract Syntax Tree (`ast`) | Classes, base classes, functions, async functions, methods, call graphs, internal imports, relative imports, external packages, security findings. |
| **JavaScript** | `.js` | Pattern-based regex | Functions, arrow functions, ES6 classes, `import`/`require` dependencies, external packages, security findings. |
| **PHP** | `.php` | Pattern-based regex | Classes, functions, methods, `include`/`require` dependencies, security findings. |

---

## 🛠️ Architecture & Technology Stack

```
   ┌─────────────────────────────────────────────────────────┐
   │             Browser Frontend (Vanilla SPA)              │
   │      vis-network Graph • Dashboard • Findings Panel     │
   └───────────────────────────▲─────────────────────────────┘
                               │ HTTP / REST APIs
   ┌───────────────────────────▼─────────────────────────────┐
   │                 FastAPI Backend Service                 │
   │  ┌──────────────────────┐     ┌──────────────────────┐  │
   │  │  Codebase Analyzer   │     │   Security Scanner   │  │
   │  │ (Python AST / Regex) │     │ (SEC001 - SEC010)    │  │
   │  └──────────┬───────────┘     └──────────┬───────────┘  │
   │             │                            │              │
   │             ▼                            ▼              │
   │  ┌───────────────────────────────────────────────────┐  │
   │  │            Repository Abstraction Layer           │  │
   │  │  - Neo4jGraphRepository (Live Bolt Driver)        │  │
   │  │  - InMemoryGraphRepository (Offline Fallback)     │  │
   │  └──────────┬────────────────────────────┬───────────┘  │
   └─────────────┼────────────────────────────┼──────────────┘
                 │ Bolt / neo4j+s://          │ In-Memory
                 ▼                            ▼
   ┌──────────────────────────┐  ┌──────────────────────────┐
   │     Neo4j Aura Free      │  │    Local Graph Engine    │
   │  (Cloud Graph Database)  │  │   (Development / Tests)  │
   └──────────────────────────┘  └──────────────────────────┘
```

| Component | Technology | Description |
|---|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn | High-performance asynchronous REST API backend. |
| **Data Validation** | Pydantic V2, Pydantic-Settings | Request/response schema contracts and environment configuration. |
| **Database** | Neo4j Aura Free / Neo4j 5.x | Graph database using the official `neo4j` Python driver. |
| **Analysis Engine** | Python Standard Library (`ast`, `re`) | Zero-execution static analysis and symbol extraction. |
| **Frontend** | HTML5, Modern CSS3, JavaScript (ES6) | Responsive dark-theme SPA with no heavy node framework dependencies. |
| **Graph Visualization** | `vis-network` (v9.1.9) | Hardware-accelerated canvas graph renderer with physics simulation. |
| **Testing** | Pytest 8.x / 9.x | 22 comprehensive automated tests. |
| **Automation** | Windows Batch (`.bat`), Shell (`.sh`) | Single-click environment creation and startup scripts. |

---

## 📁 Project Directory Structure

```
codegraph-ai/
├── README.md                     # Comprehensive project documentation
├── LICENSE                       # MIT License
├── .gitignore                    # Git exclusions (.env, .venv, caches, etc.)
├── .env.example                  # Environment configuration template
├── requirements.txt              # Root pip requirements pointer
├── docker-compose.yml            # Local Neo4j container configuration
├── run.bat                       # Local Windows startup batch script
├── run-cloud.bat                 # Neo4j Aura Cloud Windows startup batch script
├── run.sh                        # Linux / macOS / WSL startup script
├── pytest.ini                    # Pytest configuration file
├── create_sample_zip.py          # Helper to generate vulnerable demo zip
│
├── backend/
│   ├── requirements.txt          # Production and test dependencies
│   ├── __init__.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI application & REST endpoint routing
│   │   ├── config.py             # Pydantic Settings & environment loader
│   │   ├── analyzer.py           # AST & pattern code analyzer
│   │   ├── security_scanner.py   # Security rules catalog & AST visitors
│   │   ├── graph.py              # Neo4j Cypher driver & in-memory fallback
│   │   ├── ai.py                 # Offline rule-based & LLM review generator
│   │   ├── schemas.py            # Pydantic request/response models
│   │   └── exceptions.py         # Custom application exception handlers
│   └── tests/
│       ├── __init__.py
│       ├── test_analyzer.py      # AST extraction, imports & discovery tests
│       ├── test_security_scanner.py # Rules SEC001-SEC010 & negative tests
│       ├── test_api.py           # REST endpoints & archive traversal tests
│       └── test_graph_helpers.py # Graph abstractions & Cypher mocking
│
├── frontend/
│   ├── index.html                # Dark developer dashboard SPA
│   ├── css/
│   │   └── styles.css            # Responsive dark developer styles
│   └── js/
│       ├── api.js                # REST API client
│       ├── graph.js              # vis-network graph rendering & filters
│       ├── dashboard.js          # Overview metrics & insights tables
│       ├── findings.js           # Security findings viewer & filters
│       └── app.js                # State coordination & navigation
│
├── samples/
│   └── demo_project/             # Multi-module sample project for testing
│       ├── app.py                # Main entry point with demo calls & findings
│       ├── database.py           # Simulated DB queries with SQLi & secrets
│       ├── utils.py              # Security token service with weak hash
│       └── requirements.txt      # Demo project dependencies
│
└── docs/
    ├── ARCHITECTURE.md           # System design & Cypher algorithms
    ├── API.md                    # REST API endpoint documentation
    ├── SECURITY.md               # Security rules catalog & remediations
    ├── SETUP_WINDOWS.md          # Comprehensive Windows guide
    └── NEO4J_SETUP.md            # Neo4j Aura cloud & Cypher queries guide
```

---

## 🪟 Windows Installation & Setup

### Prerequisites
- **Python 3.12 or higher** installed from [python.org](https://www.python.org/downloads/) (ensure **"Add python.exe to PATH"** was checked during installation).
- Modern web browser (Chrome, Edge, or Firefox).

### Automated Setup (Recommended)
Simply double-click `run.bat` or run in Command Prompt / PowerShell:
```cmd
run.bat
```
The script will automatically:
1. Verify Python availability.
2. Create the virtual environment in `backend\.venv` if missing.
3. Activate the virtual environment.
4. Install all dependencies from `backend\requirements.txt`.
5. Copy `.env.example` to `.env` if `.env` does not exist.
6. Start the Uvicorn web server at `http://127.0.0.1:8000/`.

---

## ⚙️ Configuration (.env.example)

CodeGraph AI reads its configuration from `.env` in the project root. A safe template is provided in `.env.example`:

```env
# Neo4j Database Configuration
NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password-here
NEO4J_DATABASE=neo4j

# Optional AI Review Configuration
# Provider: 'none' (default, uses rule-based offline engine), 'gemini', or 'openai'
AI_PROVIDER=none
AI_API_KEY=
AI_MODEL=gemini-1.5-flash

# Scanner & Server Limits
MAX_UPLOAD_MB=25
MAX_FILES_PER_SCAN=500
HOST=127.0.0.1
PORT=8000
DEBUG=false
```

> **Note:** If `NEO4J_URI` or `NEO4J_PASSWORD` contains placeholder values or is omitted, CodeGraph AI automatically activates its high-performance **in-memory graph fallback**, allowing full functionality without requiring a database.

---

## 🚀 Running the Application

### 1. Local Startup (Default / In-Memory Mode)
```cmd
run.bat
```
Launches CodeGraph AI locally. If Neo4j is not configured, it transparently uses the in-memory graph repository.

### 2. Neo4j Aura Cloud Startup
```cmd
run-cloud.bat
```
Verifies cloud credentials in `.env`, guides setup if missing, and connects directly to Neo4j Aura Free over encrypted TLS (`neo4j+s://`).

### 3. Manual Startup
```cmd
# Activate virtual environment
backend\.venv\Scripts\activate

# Set python path and start uvicorn
set PYTHONPATH=%CD%
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## ☁️ Neo4j Aura Cloud Integration

CodeGraph AI is engineered to integrate natively with **Neo4j Aura Free**:

1. Sign up for free at [console.neo4j.io](https://console.neo4j.io/).
2. Click **"New Instance"** and choose **"AuraDB Free"**.
3. **Save your generated password immediately** and download the credentials file.
4. Copy the connection URI (e.g., `neo4j+s://xxxxxxxx.databases.neo4j.io`).
5. Update your `.env` file:
   ```env
   NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=<your-saved-password>
   NEO4J_DATABASE=neo4j
   ```
6. Run `run-cloud.bat`. The frontend status badge will illuminate green with **"Neo4j Connected"**.

---

## 🌐 Dashboard & Interactive API Docs

Once the server is running:
- **Web Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Alternative API Docs:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔍 Scanning Codebases & Demo Project

### Scanning the Bundled Demo Project
A multi-module demo application with realistic dependencies and known security vulnerabilities is included in `samples/demo_project`:
1. Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
2. Click **"Scan Project"** in the top navigation bar.
3. Click the shortcut button **"Use Bundled Demo Project"** (or type `samples/demo_project`).
4. Click **"Start Scan"**.
5. The application extracts files, symbols, dependencies, and findings, rendering 30+ graph nodes and pinpointing 6 vulnerabilities immediately.

### Scanning via ZIP Upload
1. Click **"Scan Project"** and select the **"Upload ZIP File"** tab.
2. Select or drag any source code `.zip` archive (up to 25MB).
3. The server validates the archive against ZIP Slip and relative directory traversal attacks, extracts it into a secure temporary location, runs the analysis, persists the knowledge graph, and cleans up the temporary files.

### Scanning Any Local Workstation Directory
1. In the **"Scan Local Directory"** tab, input any valid directory path (e.g., `C:\Projects\my-app`).
2. The scanner validates the path and analyzes the codebase in place without modifying any source files.

---

## 🔒 Security Findings & Architecture Analysis

CodeGraph AI runs a static security rule engine with AST-level parsing to eliminate comment and docstring false positives:

| Rule ID | Name | Severity | CWE | Description |
|---|---|---|---|---|
| **SEC001** | Dynamic Code Execution | **HIGH** | CWE-95 | Unsafe dynamic code execution using `eval()` or `exec()`. |
| **SEC002** | SQL Injection Risk | **HIGH** | CWE-89 | Unsafe SQL query formatting via string concatenation, `%` formatting, or f-strings. |
| **SEC003** | Raw Request in DB Query | **HIGH** | CWE-89 | Direct embedding of HTTP request parameters into database calls. |
| **SEC004** | Unsafe Shell Command | **HIGH** | CWE-78 | Command execution with `shell=True` or raw system calls (`os.system`). |
| **SEC005** | Hardcoded Secret | **MEDIUM** | CWE-798 | Hardcoded API keys, private tokens, or database passwords in source code. |
| **SEC006** | Unsafe Deserialization | **HIGH** | CWE-502 | Deserialization of untrusted data (`pickle`, `yaml.load` without SafeLoader). |
| **SEC007** | Weak Hash Algorithm | **LOW** | CWE-328 | Outdated cryptographic hashing algorithms (`MD5`, `SHA-1`). |
| **SEC008** | Debug Mode Enabled | **LOW** | CWE-489 | Framework debug flags (`DEBUG = True`) left active. |
| **SEC009** | Potential XSS Sink | **MEDIUM** | CWE-79 | Unescaped DOM manipulation (`innerHTML`, `document.write`). |
| **SEC010** | Disabled TLS Verification | **HIGH** | CWE-295 | Explicit disabling of TLS certificate verification (`verify=False`). |

*(Detailed remediations and vulnerable patterns are documented in [docs/SECURITY.md](docs/SECURITY.md).)*

---

## 🧪 Automated Testing

The project includes an automated test suite executed with `pytest`:

```cmd
# Run tests using the virtual environment
backend\.venv\Scripts\python.exe -m pytest -v
```

### Verified Test Breakdown (22 Passed)
- **`backend/tests/test_analyzer.py`** (6 tests): Python AST extraction, class inheritance, function call mapping, relative imports, ignored directory exclusion, and multi-language discovery.
- **`backend/tests/test_security_scanner.py`** (9 tests): Positive and negative test cases for rules SEC001–SEC010, ensuring zero false-positives on docstrings and comments.
- **`backend/tests/test_api.py`** (5 tests): Health check endpoint, ZIP upload validation, ZIP Slip path traversal rejection, local path scanning, and project listing.
- **`backend/tests/test_graph_helpers.py`** (2 tests): Graph data transformations, node styling rules, and in-memory Cypher abstractions.

---

## 📡 REST API Endpoints

All endpoints return structured JSON with uniform error handling:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health status and Neo4j connectivity check (credentials masked). |
| `POST` | `/api/scan/upload` | Upload and analyze a `.zip` file with path-traversal validation. |
| `POST` | `/api/scan/path` | Scan a local server/workstation directory. |
| `GET` | `/api/projects` | List all scanned projects with metadata and findings counts. |
| `GET` | `/api/projects/{pid}/summary` | Architecture metrics, coupling hotspots, and circular imports. |
| `GET` | `/api/projects/{pid}/graph` | `vis-network` nodes and edges with optional type filtering. |
| `GET` | `/api/projects/{pid}/findings` | Paginated security findings with severity and rule filters. |
| `GET` | `/api/projects/{pid}/files` | List of all scanned source files in the project. |
| `GET` | `/api/projects/{pid}/files/{file_id:path}` | Detailed metadata, symbols, and findings for a specific file. |
| `POST` | `/api/projects/{pid}/ai` | Generate rule-based or LLM architectural review report. |
| `GET` | `/api/projects/{pid}/export` | Download complete project analysis and findings as a JSON file. |
| `DELETE` | `/api/projects/{pid}` | Delete project and detach all associated graph nodes. |

---

## ⚠️ Limitations, Troubleshooting & Future Enhancements

### Known Limitations
1. **Dynamic Python Metaprogramming:** Highly dynamic code (e.g., `getattr(module, var)()` or `__import__()`) cannot be resolved statically via AST.
2. **Language Coverage Depth:** Python AST analysis is exhaustive; JavaScript and PHP analysis is currently pattern-based (regex).
3. **Single Tenant Graph:** By default, projects share the configured Neo4j database and are scoped via `project_id` node properties.

### Troubleshooting
- **`Python was not found in your system PATH`**: Re-run the Python installer and check **"Add Python to PATH"**.
- **`Neo4j ServiceUnavailable / Connection Error`**:
  - Verify your Aura instance is in the **"Running"** state in the Aura Console (Aura instances pause automatically after prolonged inactivity).
  - Check that the URI begins with `neo4j+s://` for encrypted cloud connections.
  - Test offline first: if `.env` is unconfigured, the app runs smoothly with the in-memory fallback.
- **`Archive exceeds maximum allowable file count`**: Large archives with more than 500 files or exceeding 25MB are blocked by default. You can adjust `MAX_UPLOAD_MB` and `MAX_FILES_PER_SCAN` in `.env`.

### Future Enhancements
- [ ] Tree-sitter integration for native C++, Java, and TypeScript AST parsing.
- [ ] Automated Pull Request scanning GitHub Action (`codegraph-action`).
- [ ] Interactive Cypher query console embedded directly in the frontend dashboard.
- [ ] Export to SARIF (Static Analysis Results Interchange Format) for GitHub Code Scanning integration.

---

## 📜 License & Contributing

### License
This project is licensed under the [MIT License](LICENSE).

### Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Ensure all 22 tests pass (`pytest`).
5. Push to the branch (`git push origin feature/amazing-feature`).
6. Open a Pull Request.
