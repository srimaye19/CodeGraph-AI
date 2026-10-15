@echo off
setlocal enabledelayedexpansion

echo ===============================================================================
echo             CodeGraph AI - Neo4j Aura Cloud Workflow (Windows)
echo ===============================================================================

:: 1. Verify Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.12 or higher and add it to PATH.
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
)

:: 4. Activate Virtual Environment
echo [INFO] Activating virtual environment...
call "backend\.venv\Scripts\activate.bat"

:: 5. Install Dependencies
echo [INFO] Installing required libraries...
python -m pip install -r backend\requirements.txt --quiet

:: 6. Verify .env for Cloud Credentials
if not exist ".env" (
    echo.
    echo [WARNING] No '.env' file detected.
    echo Copying '.env.example' to '.env'...
    copy ".env.example" ".env" >nul
    echo.
    echo ===========================================================================
    echo [ACTION REQUIRED] Neo4j Aura Free Instance Setup:
    echo 1. Open https://console.neo4j.io/ and create a free AuraDB instance.
    echo 2. Open the newly created '.env' file in Notepad or VS Code.
    echo 3. Set NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
    echo 4. Set NEO4J_USER=neo4j
    echo 5. Set NEO4J_PASSWORD=your-saved-aura-password
    echo ===========================================================================
    echo.
)

:: 7. Launch Server
echo ===============================================================================
echo Launching CodeGraph AI connected to Neo4j Cloud...
echo Dashboard URL:     http://127.0.0.1:8000/
echo Swagger API Docs:  http://127.0.0.1:8000/docs
echo Press CTRL+C to stop the server.
echo ===============================================================================

set PYTHONPATH=%PROJECT_ROOT%
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Uvicorn server encountered an unexpected error.
    pause
)
