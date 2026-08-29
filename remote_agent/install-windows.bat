@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Remote UPS Agent - Windows Installer
cd /d "%~dp0"

echo.
echo ======================================================================
echo             REMOTE UPS AGENT - WINDOWS INSTALLER
echo ======================================================================
echo.

:: 1. Detect Python
set "PYTHON_EXE="
py -V >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    goto :PYTHON_FOUND
)
python -V >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

echo [ERROR] Python is not installed or not found in PATH!
echo Please install Python 3.10+ from https://www.python.org/
pause
exit /b 1

:PYTHON_FOUND
echo [OK] Detected Python:
%PYTHON_EXE% --version
echo.

:: 2. Virtual Environment
echo Setting up Virtual Environment (.venv)...
if not exist ".venv" (
    %PYTHON_EXE% -m venv .venv
    set "VENV_PYTHON=.venv\Scripts\python.exe"
) else (
    set "VENV_PYTHON=.venv\Scripts\python.exe"
)

:: 3. Requirements
echo Installing dependencies...
"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PYTHON%" -m pip install -r requirements.txt
echo.

:: 4. Autostart option
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set /p AUTO_CHOICE="Do you want to enable Autostart on Windows boot? (Y/N): "
if /i "%AUTO_CHOICE%"=="Y" (
    echo @echo off > "%STARTUP_DIR%\remote_ups_agent.bat"
    echo cd /d "%CD%" >> "%STARTUP_DIR%\remote_ups_agent.bat"
    echo start "" /min ".venv\Scripts\python.exe" ups_agent.py >> "%STARTUP_DIR%\remote_ups_agent.bat"
    echo [OK] Autostart enabled via Windows Startup folder.
)

echo.
echo ======================================================================
echo               REMOTE AGENT INSTALLATION COMPLETED!
echo ======================================================================
echo To start the agent manually, run: run_agent.bat
echo.
pause
