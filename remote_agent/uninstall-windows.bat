@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Remote UPS Agent - Windows Uninstaller
cd /d "%~dp0"

echo.
echo ======================================================================
echo           REMOTE UPS AGENT - WINDOWS UNINSTALLER
echo ======================================================================
echo.

set /p CONFIRM="This will stop the agent and remove startup scripts. Proceed? (y/n): "
if /i "!CONFIRM!" neq "y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo [1/3] Stopping running agent processes...
taskkill /F /FI "WINDOWTITLE eq Remote UPS Agent*" /T >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$here = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.'); Get-CimInstance Win32_Process | Where-Object { ($_.ExecutablePath -and $_.ExecutablePath -like \"$here*\") -or ($_.CommandLine -and ($_.CommandLine -like '*ups_agent.py*' -or $_.CommandLine -like \"*$here*\")) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
timeout /t 1 /nobreak >nul
echo [OK] Processes stopped.

echo.
echo [2/3] Removing startup entries...
set "STARTUP_USER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_USER%\remote_ups_agent.bat" (
    del /f /q "%STARTUP_USER%\remote_ups_agent.bat" >nul 2>&1
    echo [OK] Removed from Windows Startup folder.
)

echo.
echo [3/3] Virtual environment (.venv)...
if exist ".venv" (
    set /p DEL_VENV="Delete .venv? (y/n): "
    if /i "!DEL_VENV!"=="y" (
        rmdir /s /q ".venv" >nul 2>&1
        if exist ".venv" powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item -Path '.venv' -Recurse -Force -ErrorAction SilentlyContinue" >nul 2>&1
        echo [OK] .venv removed.
    )
)

echo.
echo ======================================================================
echo                 UNINSTALLATION COMPLETED!
echo ======================================================================
echo.
pause
exit /b 0
