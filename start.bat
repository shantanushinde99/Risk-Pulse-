@echo off
title RiskPulse Launcher

echo ===========================================
echo    Starting RiskPulse Servers
echo ===========================================
echo.

echo Starting Backend API (FastAPI) in a new window...
start "RiskPulse Backend" cmd /k "cd /d "%~dp0backend" && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo Starting Frontend Dashboard (Next.js) in a new window...
start "RiskPulse Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Both servers are starting up! 
echo Keep the new command windows open to view logs.
echo.
echo Dashboard will be available at: http://localhost:3000
echo Backend API docs at: http://localhost:8000/docs
echo.
pause
