@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Electra - Windows Installer
cd /d "%~dp0"

echo.
echo ======================================================================
echo           Electra - UPS STATUS CENTRAL MONITOR - INSTALLER
echo    Creator: Alexandros - Ermis Tsourapas (SV1RVP)
echo    License: GNU AGPL-3.0
echo ======================================================================
echo.

:: 1. Detect Python
echo [1/4] Checking Python installation...
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

python3 -V >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python3"
    goto :PYTHON_FOUND
)

echo [ERROR] Python is not installed or not in PATH!
echo Please install Python 3.9+ from https://www.python.org/
pause
exit /b 1

:PYTHON_FOUND
echo [OK] Using Python: %PYTHON_EXE%
%PYTHON_EXE% -V

:: 2. Setup Virtual Environment
echo.
echo [2/4] Setting up Virtual Environment (.venv)...
if not exist ".venv" (
    %PYTHON_EXE% -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Existing virtual environment found.
)

:: 3. Install Dependencies
echo.
echo [3/4] Installing Python requirements...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.

:: 4. Verify Start Script & Autostart
echo.
echo [4/4] Verifying startup scripts...

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
echo.
set /p AUTO_CHOICE="Do you want to enable Electra Autostart on Windows boot? (Y/N): "
if /i "%AUTO_CHOICE%"=="Y" (
    echo @echo off > "%STARTUP_DIR%\electra_ups_monitor.bat"
    echo cd /d "%CD%" >> "%STARTUP_DIR%\electra_ups_monitor.bat"
    echo start "" /min ".venv\Scripts\python.exe" app.py >> "%STARTUP_DIR%\electra_ups_monitor.bat"
    echo [OK] Autostart enabled in Windows Startup folder (electra_ups_monitor.bat).
)

echo.
echo ======================================================================
echo          [SUCCESS] Electra INSTALLED SUCCESSFULLY!
echo ======================================================================
echo.
echo Run 'start_server.bat' to start Electra.
echo Web UI Dashboard: http://localhost:8088
echo.

set /p RUN_NOW="Launch Electra now? (Y/N): "
if /i "%RUN_NOW%"=="Y" (
    start start_server.bat
)
exit /b 0
