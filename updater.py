from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

logger = logging.getLogger("Electra.Updater")

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "version.json"

# Remote repository release metadata endpoints (GitLab / GitHub fallback)
GITLAB_VERSION_URL = "https://gitlab.com/SV1RVP/electra-ups-monitor/-/raw/main/version.json"
GITLAB_ZIP_URL = "https://gitlab.com/SV1RVP/electra-ups-monitor/-/archive/main/electra-ups-monitor-main.zip"

GITHUB_VERSION_URL = "https://raw.githubusercontent.com/SV1RVP/electra-ups-monitor/main/version.json"
GITHUB_ZIP_URL = "https://github.com/SV1RVP/electra-ups-monitor/archive/refs/heads/main.zip"


def get_local_version() -> Dict[str, Any]:
    """Reads local version.json metadata."""
    try:
        if VERSION_FILE.exists():
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error reading local version.json: {e}")
    return {"version": "1.1.0", "name": "UPS Status Web Monitor"}


def parse_semver(version_str: str) -> Tuple[int, ...]:
    """Parses semantic version string like '1.1.0' or 'v1.1.0' into tuple of integers."""
    try:
        clean = str(version_str).strip().lstrip("v")
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0, 0, 0)


def get_remote_version() -> Optional[Dict[str, Any]]:
    """Fetches the latest version metadata from remote repository."""
    urls = [GITLAB_VERSION_URL, GITHUB_VERSION_URL]
    for url in urls:
        try:
            resp = requests.get(url, timeout=8)
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
            "local_version": local.get("version", "1.1.0"),
            "remote_version": None,
            "is_git": is_git,
            "message": "Δεν ήταν δυνατή η σύνδεση με το αποθετήριο για έλεγχο νέας έκδοσης.",
        }

    local_ver_str = local.get("version", "1.1.0")
    remote_ver_str = remote.get("version", "1.1.0")

    local_semver = parse_semver(local_ver_str)
    remote_semver = parse_semver(remote_ver_str)

    update_available = remote_semver > local_semver

    if is_git and not update_available:
        try:
            subprocess.run(["git", "fetch"], cwd=str(BASE_DIR), capture_output=True, timeout=10)
            res = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..origin/main"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                if int(res.stdout.strip()) > 0:
                    update_available = True
        except Exception as e:
            logger.debug(f"Git check error: {e}")

    return {
        "status": "success",
        "update_available": update_available,
        "local_version": local_ver_str,
        "remote_version": remote_ver_str,
        "release_date": remote.get("release_date", ""),
        "is_git": is_git,
        "message": f"Νέα έκδοση διαθέσιμη: v{remote_ver_str}" if update_available else "Το σύστημα είναι ενημερωμένο.",
    }


def run_update() -> Tuple[bool, str]:
    """Downloads update and triggers service restart."""
    is_git = (BASE_DIR / ".git").exists()
    system = platform.system()

    logger.info("=== Starting UPS Status Update Request ===")

    # Check directory write permissions
    if not os.access(str(BASE_DIR), os.W_OK):
        msg = f"Ανεπαρκή δικαιώματα εγγραφής στον φάκελο {BASE_DIR}."
        logger.error(msg)
        return False, msg

    if is_git:
        logger.info("Starting Git update (pulling latest commits)...")
        try:
            res = subprocess.run(
                ["git", "pull"], cwd=str(BASE_DIR), capture_output=True, text=True, check=True
            )
            logger.info(f"Git pull output: {res.stdout}")

            if system == "Linux":
                logger.info("Git update applied. Restarting systemd service...")
                time.sleep(1)
                os._exit(0)
            else:
                logger.info("Git update applied. Launching Windows auto-restart helper...")
                _create_windows_restart_helper()
                subprocess.Popen(["cmd", "/c", "start", "restart_helper.bat"], cwd=str(BASE_DIR), shell=True)
                time.sleep(1)
                os._exit(0)
        except Exception as e:
            err = f"Git update error: {e}"
            logger.error(err)
            return False, err

    else:
        # ZIP-based update
        logger.info("Starting ZIP update download...")
        try:
            download_url = GITLAB_ZIP_URL
            resp = requests.get(download_url, stream=True, timeout=30)
            if resp.status_code != 200:
                download_url = GITHUB_ZIP_URL
                resp = requests.get(download_url, stream=True, timeout=30)
            resp.raise_for_status()

            zip_path = BASE_DIR / "update.zip"
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Update ZIP downloaded successfully.")

            if system == "Windows":
                _create_windows_updater_script(zip_path)
                logger.info("Launching Windows updater script...")
                subprocess.Popen(["cmd", "/c", "start", "update_helper.bat"], cwd=str(BASE_DIR), shell=True)
                time.sleep(1)
                os._exit(0)
            else:
                _extract_linux_zip(zip_path)
                logger.info("Update applied on Linux. Exiting for systemd auto-restart...")
                time.sleep(1)
                os._exit(0)

        except Exception as e:
            err = f"ZIP update error: {e}"
            logger.error(err)
            return False, err

    return True, "Η ενημέρωση ολοκληρώθηκε επιτυχώς."


def _extract_linux_zip(zip_path: Path):
    """Extracts update zip on Linux, safely preserving user config and database."""
    temp_dir = BASE_DIR / "_temp_update"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    subdirs = [temp_dir / d for d in os.listdir(temp_dir) if (temp_dir / d).is_dir()]
    src_dir = subdirs[0] if subdirs else temp_dir

    preserve_files = {"config.json", "profiles.json", "ups_history.db", "ups_history.db-shm", "ups_history.db-wal", "learning.json", "app.log", ".venv"}

    for item in os.listdir(src_dir):
        if item in preserve_files:
            continue
        s = src_dir / item
        d = BASE_DIR / item
        if s.is_dir():
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    if zip_path.exists():
        os.remove(zip_path)


def _create_windows_restart_helper():
    """Creates a small helper script to restart the server on Windows."""
    script = """@echo off
timeout /t 2 /nobreak > nul
start start_server.bat
(goto) 2>nul & del "restart_helper.bat" & exit
"""
    with open(BASE_DIR / "restart_helper.bat", "w", encoding="utf-8") as f:
        f.write(script)


def _create_windows_updater_script(zip_path: Path):
    """Creates Windows batch updater script."""
    script = f"""@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo         UPS Status Web Monitor - Windows Updater
echo ============================================================
echo Waiting for server process to close...
timeout /t 3 /nobreak > nul

echo Extracting updates...
if exist "_temp_update" rmdir /s /q "_temp_update"
powershell -Command "Expand-Archive -Path '{zip_path.name}' -DestinationPath '_temp_update' -Force"

set "EXT_DIR="
for /d %%d in ("_temp_update\\*") do (
    set "EXT_DIR=%%d"
)

if defined EXT_DIR (
    echo Found update files in: !EXT_DIR!
    echo Moving files...
    xcopy /s /e /y /q "!EXT_DIR!\\*" "."
) else (
    echo Error: Could not find extracted folder.
    pause
    exit
)

echo Update Complete!
echo Restarting UPS Status Server...
start start_server.bat
echo Cleaning up...
del "{zip_path.name}"
rmdir /s /q "_temp_update"
(goto) 2>nul & del "update_helper.bat" & exit
"""
    with open(BASE_DIR / "update_helper.bat", "w", encoding="utf-8") as f:
        f.write(script)
