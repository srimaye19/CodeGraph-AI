#!/usr/bin/env bash
# ==============================================================================
# CodeGraph AI - Unix / macOS / WSL Startup Script
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "==============================================================================="
echo "                        CodeGraph AI Startup"
echo "==============================================================================="

# 1. Verify Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.12+."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d "backend/.venv" ]; then
    echo "[INFO] Creating virtual environment in backend/.venv..."
    python3 -m venv backend/.venv
fi

echo "[INFO] Activating virtual environment..."
source backend/.venv/bin/activate

# 3. Dependencies
echo "[INFO] Installing dependencies..."
python -m pip install -r backend/requirements.txt --quiet

# 4. Config check
if [ ! -f ".env" ]; then
    echo "[INFO] Creating .env from .env.example..."
    cp .env.example .env
    echo "[ACTION REQUIRED] Update .env with your Neo4j credentials."
fi

# 5. Launch
echo "==============================================================================="
echo "Starting CodeGraph AI Server..."
echo "Web Application: http://127.0.0.1:8000/"
echo "Interactive Docs: http://127.0.0.1:8000/docs"
echo "==============================================================================="

export PYTHONPATH="$PROJECT_ROOT"
exec python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
