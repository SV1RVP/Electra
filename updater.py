"""
Electra - UPS Status Central Monitor - Auto-Updater & Upgrade Engine
Author: Alexandros - Ermis Tsourapas (SV1RVP)
License: GNU AGPLv3
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
import urllib.request
import urllib.error
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

logger = logging.getLogger("Electra.Updater")

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "version.json"

# Remote repository release metadata endpoints (GitLab / GitHub fallback)
GITLAB_RAW_MAIN_URL = "https://gitlab.com/SV1RVP/electra-ups-monitor/-/raw/main/version.json"
GITLAB_RAW_MASTER_URL = "https://gitlab.com/SV1RVP/electra-ups-monitor/-/raw/master/version.json"
GITLAB_ZIP_MAIN_URL = "https://gitlab.com/SV1RVP/electra-ups-monitor/-/archive/main/electra-ups-monitor-main.zip"
GITLAB_ZIP_MASTER_URL = "https://gitlab.com/SV1RVP/electra-ups-monitor/-/archive/master/electra-ups-monitor-master.zip"

GITHUB_VERSION_URL = "https://raw.githubusercontent.com/SV1RVP/electra-ups-monitor/main/version.json"
GITHUB_ZIP_URL = "https://github.com/SV1RVP/electra-ups-monitor/archive/refs/heads/main.zip"

# Protected user files that are NEVER overwritten or deleted during update
PRESERVED_USER_FILES = {
    "config.json",
    "profiles.json",
    "learning.json",
    "telemetry.db",
    "telemetry.db-shm",
    "telemetry.db-wal",
    "ups_history.db",
    "ups_history.db-shm",
    "ups_history.db-wal",
    "app.log",
    "cert.pem",
    "key.pem",
    ".venv"
}


def get_local_version() -> Dict[str, Any]:
    """Reads local version.json metadata."""
    try:
        if VERSION_FILE.exists():
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading local version.json: {e}")
    return {
        "app_name": "Electra",
        "name": "Electra - UPS Status Central Monitor",
        "subtitle": "UPS Status Central Monitor",
        "version": "1.3.0",
        "author": "Alexandros - Ermis Tsourapas (SV1RVP)",
        "license": "GNU Affero General Public License v3.0 (AGPL-3.0)"
    }


def parse_semver(version_str: str) -> Tuple[int, ...]:
    """Parses semantic version string like '1.2.0' or 'v1.2.0' into tuple of integers."""
    try:
        clean = str(version_str).strip().lstrip("v")
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0, 0, 0)


def get_remote_version() -> Optional[Dict[str, Any]]:
    """Fetches the latest version metadata from remote repository."""
    urls = [GITLAB_RAW_MAIN_URL, GITLAB_RAW_MASTER_URL, GITHUB_VERSION_URL]
    for url in urls:
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Electra-Updater/1.2"})
            if resp.status_code == 200:
                data = resp.json()
                if "version" in data:
                    return data
        except Exception as e:
            logger.debug(f"Could not fetch version from {url}: {e}")
    return None


def check_for_updates() -> Dict[str, Any]:
    """Compares local version with latest remote version."""
    local = get_local_version()
    remote = get_remote_version()

    is_git = (BASE_DIR / ".git").exists()

    if not remote:
        return {
            "status": "warning",
            "update_available": False,
            "local_version": local.get("version", "1.2.0"),
            "remote_version": None,
            "is_git": is_git,
            "message": "Δεν ήταν δυνατή η σύνδεση με το GitLab για έλεγχο νέας έκδοσης.",
        }

    local_ver_str = local.get("version", "1.2.0")
    remote_ver_str = remote.get("version", "1.2.0")

    local_semver = parse_semver(local_ver_str)
    remote_semver = parse_semver(remote_ver_str)

    update_available = remote_semver > local_semver

    return {
        "status": "success",
        "update_available": update_available,
        "local_version": local_ver_str,
        "remote_version": remote_ver_str,
        "release_date": remote.get("release_date", ""),
        "changelog": remote.get("changelog", []),
        "download_url": remote.get("download_url", GITLAB_ZIP_MAIN_URL),
        "repository": remote.get("repository", "https://gitlab.com/SV1RVP/electra-ups-monitor"),
        "is_git": is_git,
        "message": f"Νέα έκδοση διαθέσιμη: v{remote_ver_str}" if update_available else "Χρησιμοποιείτε την πιο πρόσφατη έκδοση.",
    }


def download_file(url: str, dest_path: Path) -> bool:
    """Downloads a remote file with User-Agent header."""
    req = urllib.request.Request(url, headers={"User-Agent": "Electra-Updater/1.2"})
    with urllib.request.urlopen(req, timeout=30) as response:
        if response.status == 200:
            with open(dest_path, "wb") as out_file:
                shutil.copyfileobj(response, out_file)
            return True
    return False


def _safe_extract_and_copy(zip_path: Path):
    """
    Safely extracts archive and copies new files over BASE_DIR,
    STRICTLY PRESERVING existing user configuration, databases, and logs.
    """
    temp_dir = BASE_DIR / "_temp_update"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    subdirs = [temp_dir / d for d in os.listdir(temp_dir) if (temp_dir / d).is_dir()]
    src_dir = subdirs[0] if subdirs else temp_dir

    for item in os.listdir(src_dir):
        # Never overwrite existing user configuration or databases!
        if item in PRESERVED_USER_FILES:
            if (BASE_DIR / item).exists():
                logger.info(f"[Updater] Preserving existing user file: {item}")
                continue

        s = src_dir / item
        d = BASE_DIR / item
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    # Cleanup temp archives
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    if zip_path.exists():
        os.remove(zip_path)


def create_windows_update_helper(zip_path: Path) -> Path:
    """Generates the Windows helper script to safely apply update and restart Electra."""
    helper_path = BASE_DIR / "update_helper.bat"
    script = f"""@echo off
setlocal enabledelayedexpansion
title Electra - Windows Auto-Updater
cd /d "{BASE_DIR}"

echo ============================================================
echo         ELECTRA - UPDATING APPLICATION FILES
echo ============================================================
echo Waiting for active server processes to close...
timeout /t 3 /nobreak > nul

echo [1/3] Extracting update archive...
if exist "_temp_update" rmdir /s /q "_temp_update"
powershell -Command "Expand-Archive -Path '{zip_path.name}' -DestinationPath '_temp_update' -Force"

set "EXT_DIR="
for /d %%d in ("_temp_update\\*") do (
    set "EXT_DIR=%%d"
)

if defined EXT_DIR (
    echo [2/3] Applying updated files...
    :: Copy files while preserving existing config/db files
    powershell -NoProfile -Command "
    $src = '!EXT_DIR!';
    $dst = '{BASE_DIR}';
    $preserve = @('config.json', 'profiles.json', 'learning.json', 'telemetry.db', 'telemetry.db-shm', 'telemetry.db-wal', 'ups_history.db', 'ups_history.db-shm', 'ups_history.db-wal', 'app.log', '.venv');
    Get-ChildItem -Path $src -Recurse | ForEach-Object {{
        $rel = $_.FullName.Substring($src.Length + 1);
        $target = Join-Path $dst $rel;
        if (-not (Test-Path $target) -or ($preserve -notcontains $_.Name)) {{
            if ($_.PSIsContainer) {{
                if (-not (Test-Path $target)) {{ New-Item -ItemType Directory -Path $target -Force | Out-Null }}
            }} else {{
                Copy-Item -Path $_.FullName -Destination $target -Force
            }}
        }}
    }}
    "
) else (
    echo [ERROR] Could not find extracted folder.
    pause
    exit /b 1
)

echo [3/3] Updating Python packages...
if exist ".venv\\Scripts\\python.exe" (
    .venv\\Scripts\\python.exe -m pip install -r requirements.txt --quiet --no-warn-script-location
)

echo Cleaning up temporary update archives...
del /f /q "{zip_path.name}" 2>nul
rmdir /s /q "_temp_update" 2>nul

echo.
echo ============================================================
echo   [SUCCESS] Electra update completed!
echo   Restarting server...
echo ============================================================
start "" "start_server.bat"

(goto) 2>nul & del "%~f0" & exit
"""
    with open(helper_path, "w", encoding="utf-8") as f:
        f.write(script)
    return helper_path


def run_update() -> Tuple[bool, str]:
    """
    Downloads latest release from GitLab, safely replaces files without touching user configs/databases,
    and automatically restarts Electra server / systemd service.
    """
    system = platform.system()
    zip_path = BASE_DIR / "update.zip"

    logger.info("=== Starting Electra Auto-Update ===")

    # 1. Download ZIP
    downloaded = False
    urls_to_try = [GITLAB_ZIP_MAIN_URL, GITLAB_ZIP_MASTER_URL, GITHUB_ZIP_URL]
    for url in urls_to_try:
        try:
            logger.info(f"Downloading update from {url} ...")
            if download_file(url, zip_path):
                downloaded = True
                break
        except Exception as e:
            logger.debug(f"Download failed from {url}: {e}")
            continue

    if not downloaded or not zip_path.exists():
        return False, "Αποτυχία λήψης του πακέτου ενημέρωσης από το GitLab."

    # 2. Apply and Restart
    if system == "Windows":
        create_windows_update_helper(zip_path)

        def delayed_windows_restart():
            time.sleep(1)
            subprocess.Popen(["cmd.exe", "/c", "start", "", "update_helper.bat"], cwd=str(BASE_DIR), shell=True)
            time.sleep(1)
            os._exit(0)

        threading.Thread(target=delayed_windows_restart, daemon=True).start()
        return True, "Η ενημέρωση λήφθηκε επιτυχώς! Η εφαρμογή επανεκκινεί..."

    else:
        # Linux
        try:
            _safe_extract_and_copy(zip_path)

            def delayed_linux_restart():
                time.sleep(1)
                try:
                    subprocess.Popen(["sudo", "systemctl", "restart", "electra.service"])
                except Exception:
                    pass
                time.sleep(1)
                os._exit(0)

            threading.Thread(target=delayed_linux_restart, daemon=True).start()
            return True, "Η ενημέρωση εγκαταστάθηκε επιτυχώς! Η υπηρεσία επανεκκινεί..."

        except Exception as e:
            return False, f"Σφάλμα κατά την εγκατάσταση της ενημέρωσης: {e}"
