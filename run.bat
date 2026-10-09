@echo off
setlocal enabledelayedexpansion
title PII Firewall Launcher

echo ===================================================
echo Starting PII Firewall for AI Agents
echo ===================================================

set "SCRIPT_DIR=%~dp0"
cd /d "!SCRIPT_DIR!"

echo Starting FastAPI Backend Gateway (Port 8000)...
start "PII Firewall - Backend" cmd /k "cd /d ""!SCRIPT_DIR!"" && ""!SCRIPT_DIR!venv\Scripts\python.exe"" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

echo Starting React Dashboard Frontend (Port 5173)...
start "PII Firewall - Frontend" cmd /k "cd /d ""!SCRIPT_DIR!frontend"" && npm run dev"

echo.
echo ===================================================
echo Services successfully launched in background windows!
echo - Dashboard UI: http://localhost:5173
echo - Backend API:  http://localhost:8000
echo - API Docs:     http://localhost:8000/docs
echo ===================================================
echo You can close this launcher window anytime.
pause
