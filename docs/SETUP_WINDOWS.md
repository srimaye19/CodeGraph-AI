# CodeGraph AI — Windows Setup Guide

This guide provides step-by-step instructions for running CodeGraph AI on **Windows 10/11** using Command Prompt (CMD) or PowerShell.

---

## 1. Prerequisites

1. **Python 3.12+**:
   - Download from [python.org](https://www.python.org/downloads/).
   - **Crucial:** Check the box that says **"Add python.exe to PATH"** during installation.
   - Verify in CMD:
     ```cmd
     python --version
     ```
2. **Web Browser**: Chrome, Edge, or Firefox.

---

## 2. Quick Start (Automated Script)

1. Open Windows Command Prompt (`cmd.exe`).
2. Navigate to the project root directory:
   ```cmd
   cd path\to\codegraph-ai
   ```
3. Run the automated startup batch file:
   ```cmd
   run.bat
   ```
4. `run.bat` will automatically:
   - Verify Python.
   - Create `backend\.venv` if it does not already exist.
   - Activate the virtual environment.
   - Install required dependencies.
   - Copy `.env.example` to `.env` if `.env` does not exist.
   - Launch Uvicorn at `http://127.0.0.1:8000/`.

---

## 3. Manual Step-by-Step Setup

If you prefer running the commands manually:

### Step 1: Create and Activate Virtual Environment
```cmd
cd path\to\codegraph-ai
python -m venv backend\.venv
backend\.venv\Scripts\activate
```

### Step 2: Install Python Dependencies
```cmd
pip install -r backend\requirements.txt
```

### Step 3: Configure Environment
Copy the example configuration:
```cmd
copy .env.example .env
```
Edit `.env` in Notepad or VS Code to set your Neo4j credentials:
```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-actual-password
```
*(If you do not have Neo4j configured yet, CodeGraph AI will seamlessly use its built-in in-memory knowledge graph.)*

### Step 4: Run Automated Tests
Verify that all unit tests pass:
```cmd
pytest
```
Expected output:
```
============================== 22 passed in 6.26s ==============================
```

### Step 5: Start Uvicorn Server
```cmd
set PYTHONPATH=%CD%
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 4. Accessing the Application

- **Web Dashboard:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. Scanning the Bundled Demo Project

1. Open `http://127.0.0.1:8000/` in your browser.
2. Click the green **"Scan Project"** button in the header.
3. Click the **"Use Bundled Demo Project"** shortcut button (this populates `samples/demo_project`).
4. Click **"Start Scan"**.
5. Within seconds, the dashboard will update with:
   - 3 files discovered (`app.py`, `database.py`, `utils.py`).
   - Defined symbols (functions & classes).
   - Interactive Dependency Knowledge Graph.
   - 6 static security findings.
   - Architecture Insights & circular import checks.

---

## 6. Windows Troubleshooting

- **"Python is not recognized"**: Ensure Python is added to your Windows environment variables PATH.
- **PowerShell Script Execution Policy**: If using PowerShell and `activate.ps1` gives an execution policy error, run:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```
- **Port 8000 already in use**: If port 8000 is occupied by another service, start on port 8080:
  ```cmd
  python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload
  ```
