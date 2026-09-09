@echo off
title Electra Remote Agent Updater
cd /d "%~dp0"
echo ========================================================
echo   Electra Remote Agent - Manual Update Launcher
echo ========================================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" update.py
) else (
    python update.py
)
echo.
pause
