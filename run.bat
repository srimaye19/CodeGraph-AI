@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo                     CodeGraph AI - Local Startup (Windows)
echo ===============================================================================

:: 1. Verify Python Installation
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.12 or higher from https://python.org and add it to PATH.
    pause
    exit /b 1
)

:: 2. Set root working directory
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

:: 3. Setup Virtual Environment
if not exist "backend\.venv" (
    echo [INFO] Creating Python virtual environment in backend\.venv ...
    python -m venv backend\.venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 4. Activate Virtual Environment
echo [INFO] Activating virtual environment...
call "backend\.venv\Scripts\activate.bat"

:: 5. Install / Update Dependencies
echo [INFO] Checking and installing dependencies from backend\requirements.txt ...
python -m pip install -r backend\requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Dependency installation finished with warnings or errors.
)

:: 6. Check Environment Configuration
if not exist ".env" (
    echo.
    echo [NOTICE] '.env' configuration file was not found.
    echo Copying '.env.example' to '.env'...
    copy ".env.example" ".env" >nul
    echo.
    echo [ACTION REQUIRED] Please edit '.env' and enter your Neo4j credentials:
    echo   - NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
    echo   - NEO4J_USER=neo4j
    echo   - NEO4J_PASSWORD=your-actual-password
    echo (Note: CodeGraph AI will run in offline in-memory fallback mode until configured.)
    echo.
)

:: 7. Start Uvicorn Server
echo ===============================================================================
echo Starting CodeGraph AI Server...
echo Web Application:  http://127.0.0.1:8000/
echo Interactive Docs: http://127.0.0.1:8000/docs
echo Press CTRL+C to stop the server.
echo ===============================================================================

set PYTHONPATH=%PROJECT_ROOT%
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] The server exited with an error code.
    pause
)
