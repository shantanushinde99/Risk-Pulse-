@echo off
title RiskPulse Data Ingestion

echo ====================================================
echo    Starting Moss Data Ingestion (RiskPulse)
echo ====================================================
echo.
echo This script will read 1,000 transactions from PaySim
echo and upload them to your new Moss Project.
echo.
echo Please wait, this may take a moment...
echo.

cd /d "%~dp0backend\scripts"
"..\..\..\.venv\Scripts\python.exe" ingest_moss.py

echo.
echo ====================================================
echo Ingestion Complete! You can now close this window.
echo ====================================================
pause
