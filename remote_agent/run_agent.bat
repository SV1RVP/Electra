@echo off
title Remote UPS Agent
cd /d "%~dp0"
echo Starting Remote UPS Telemetry Agent...

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=py"
)

"%PYTHON_EXE%" ups_agent.py
pause
