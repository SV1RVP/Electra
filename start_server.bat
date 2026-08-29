@echo off
title Electra - UPS Status Central Monitor
cd /d "%~dp0"
echo ===================================================
echo     ELECTRA - UPS STATUS CENTRAL MONITOR
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment .venv...
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    echo [INFO] Virtual environment not found, using system Python...
    set "PYTHON_EXE=python"
)

echo Starting Electra Web Server on http://localhost:8088 ...
echo Press Ctrl+C to stop.
echo.
"%PYTHON_EXE%" app.py
pause
