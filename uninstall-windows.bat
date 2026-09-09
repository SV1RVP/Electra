@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Electra - Windows Uninstaller
cd /d "%~dp0"

echo.
echo ======================================================================
echo           Electra - UPS STATUS CENTRAL MONITOR - UNINSTALLER
echo    Creator: Alexandros - Ermis Tsourapas (SV1RVP)
echo ======================================================================
echo.

:: 1. Terminate running processes
echo [1/4] Stopping all running Electra / UPS Status monitor processes...

:: Method A: Kill processes listening on port 8088 (FastAPI server)
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":8088 "') do (
    taskkill /F /PID %%p >nul 2>&1
)

:: Method B: Kill Python processes running app.py
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and ($_.CommandLine -like '*app.py*' -or $_.CommandLine -like '*Electra*' -or $_.CommandLine -like '*UPS Status*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

ping 127.0.0.1 -n 2 >nul
echo [OK] All running monitor processes terminated.
echo.

:: 2. Remove Startup entries and shortcuts
echo [2/4] Removing Windows Startup entries...
set "STARTUP_USER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_ALL=%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup"

if exist "%STARTUP_USER%\electra_ups_monitor.bat" del /f /q "%STARTUP_USER%\electra_ups_monitor.bat" >nul 2>&1
if exist "%STARTUP_USER%\electra_ups_monitor.lnk" del /f /q "%STARTUP_USER%\electra_ups_monitor.lnk" >nul 2>&1
if exist "%STARTUP_USER%\ups_status_monitor.bat" del /f /q "%STARTUP_USER%\ups_status_monitor.bat" >nul 2>&1
if exist "%STARTUP_USER%\UPSStatus.bat" del /f /q "%STARTUP_USER%\UPSStatus.bat" >nul 2>&1
if exist "%STARTUP_USER%\ups_status_monitor.lnk" del /f /q "%STARTUP_USER%\ups_status_monitor.lnk" >nul 2>&1
if exist "%STARTUP_USER%\UPSStatus.lnk" del /f /q "%STARTUP_USER%\UPSStatus.lnk" >nul 2>&1

if exist "%STARTUP_ALL%\electra_ups_monitor.bat" del /f /q "%STARTUP_ALL%\electra_ups_monitor.bat" >nul 2>&1
if exist "%STARTUP_ALL%\ups_status_monitor.bat" del /f /q "%STARTUP_ALL%\ups_status_monitor.bat" >nul 2>&1
if exist "%STARTUP_ALL%\UPSStatus.bat" del /f /q "%STARTUP_ALL%\UPSStatus.bat" >nul 2>&1

echo [OK] All Windows Startup entries removed.
echo.

:: 3. Remove Desktop shortcut
echo [3/4] Removing Desktop shortcuts...
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
if exist "%DESKTOP_DIR%\Electra.lnk" del /f /q "%DESKTOP_DIR%\Electra.lnk" >nul 2>&1
if exist "%DESKTOP_DIR%\UPS Status Monitor.lnk" del /f /q "%DESKTOP_DIR%\UPS Status Monitor.lnk" >nul 2>&1
echo [OK] Desktop shortcuts cleaned.
echo.

:: 4. Clean temporary runtime files
echo [4/4] Cleaning temporary runtime cache...
if exist "__pycache__" rmdir /s /q "__pycache__" >nul 2>&1
echo [OK] Temporary runtime cache cleared.
echo.

echo ======================================================================
echo           [SUCCESS] Electra UNINSTALLED FROM WINDOWS!
echo ======================================================================
echo Services and autostart shortcuts have been completely removed.
echo.
pause
exit /b 0
