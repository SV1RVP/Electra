"""
Electra - UPS Status Central Monitor - Auto-Updater & Upgrade Engine
Author: Alexandros - Ermis Tsourapas (SV1RVP)
License: GNU AGPLv3
"""

from __future__ import annotations

import io
import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import requests

logger = logging.getLogger("Electra.Updater")

BASE_DIR = Path(__file__).resolve().parent
VERSION_FILE = BASE_DIR / "version.json"

# Remote repository release metadata endpoints (GitHub)
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/SV1RVP/Electra/main/version.json"
GITHUB_ZIP_URL = "https://github.com/SV1RVP/Electra/archive/refs/heads/main.zip"

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


def get_github_token() -> Optional[str]:
    """Retrieves GitHub token from config.json, environment, or Git Credential Manager."""
    config_file = BASE_DIR / "config.json"
    try:
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                c = json.load(f)
                tok = c.get("github_token")
                if tok and str(tok).strip():
                    return str(tok).strip()
    except Exception:
        pass

    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()

    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n",
            text=True,
            capture_output=True,
            timeout=3,
        )
        if proc.returncode == 0 and proc.stdout:
            for line in proc.stdout.splitlines():
                if line.startswith("password="):
                    pwd = line.split("=", 1)[1].strip()
                    if pwd:
                        return pwd
    except Exception:
        pass
    return None


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
        "version": "1.4.1",
        "author": "Alexandros - Ermis Tsourapas (SV1RVP)",
        "license": "GNU Affero General Public License v3.0 (AGPL-3.0)"
    }


def parse_semver(version_str: str) -> Tuple[int, ...]:
    """Parses semantic version string like '1.3.2' or 'v1.3.2' into tuple of integers."""
    try:
        clean = str(version_str).strip().lstrip("v")
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0, 0, 0)


def get_remote_version() -> Optional[Dict[str, Any]]:
    """Fetches the latest version metadata from GitHub."""
    token = get_github_token()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Electra-Updater/1.4"}
    if token:
        headers["Authorization"] = f"token {token}"

    urls = [GITHUB_VERSION_URL]
    for url in urls:
        try:
            resp = requests.get(url, timeout=8, headers=headers)
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
            "local_version": local.get("version", "1.4.1"),
            "remote_version": None,
            "is_git": is_git,
            "message": "Δεν ήταν δυνατή η σύνδεση με το GitHub για έλεγχο νέας έκδοσης.",
        }

    local_ver_str = local.get("version", "1.4.1")
    remote_ver_str = remote.get("version", "1.4.1")

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
        "download_url": remote.get("download_url", GITHUB_ZIP_URL),
        "repository": remote.get("repository", "https://github.com/SV1RVP/Electra"),
        "is_git": is_git,
        "message": f"Νέα έκδοση διαθέσιμη: v{remote_ver_str}" if update_available else "Χρησιμοποιείτε την πιο πρόσφατη έκδοση.",
    }


def download_valid_zip(dest_path: Path) -> bool:
    """Downloads update zip from remote mirrors and validates its integrity."""
    token = get_github_token()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Electra-Updater/1.4"}
    if token:
        headers["Authorization"] = f"token {token}"

    urls = [GITHUB_ZIP_URL]
    for url in urls:
        try:
            logger.info(f"Downloading update package from {url} ...")
            resp = requests.get(url, stream=True, timeout=30, headers=headers)
            if resp.status_code == 200:
                content = resp.content
                # Verify that it is a valid, uncorrupted zip archive
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    if len(z.namelist()) > 0:
                        with open(dest_path, "wb") as f:
                            f.write(content)
                        logger.info(f"Successfully downloaded and verified {len(content)} bytes ({len(z.namelist())} files).")
                        return True
        except Exception as e:
            logger.warning(f"Failed to download/validate archive from {url}: {e}")
            continue

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

    for root, dirs, files in os.walk(src_dir):
        rel_root = Path(root).relative_to(src_dir)
        dest_root = BASE_DIR / rel_root
        dest_root.mkdir(parents=True, exist_ok=True)

        for file in files:
            if file in PRESERVED_USER_FILES and (dest_root / file).exists():
                logger.info(f"[Updater] Preserving user file: {file}")
                continue
            src_file = Path(root) / file
            dest_file = dest_root / file
            shutil.copy2(src_file, dest_file)

    # Cleanup temp archives
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    if zip_path.exists():
        try:
            os.remove(zip_path)
        except Exception:
            pass


def _create_python_update_runner() -> Path:
    """Creates a standalone Python updater script for bulletproof execution on Windows."""
    runner_path = BASE_DIR / "update_runner.py"
    code = """import os, sys, shutil, zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ZIP_PATH = BASE_DIR / "update.zip"
TEMP_DIR = BASE_DIR / "_temp_update"

PRESERVE = {
    "config.json", "profiles.json", "learning.json",
    "telemetry.db", "telemetry.db-shm", "telemetry.db-wal",
    "ups_history.db", "ups_history.db-shm", "ups_history.db-wal",
    "app.log", "cert.pem", "key.pem", ".venv"
}

try:
    if not ZIP_PATH.exists():
        print("[ERROR] update.zip does not exist.")
        sys.exit(1)

    print("[1/3] Extracting update files...")
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(TEMP_DIR)

    subdirs = [TEMP_DIR / d for d in os.listdir(TEMP_DIR) if (TEMP_DIR / d).is_dir()]
    src_dir = subdirs[0] if subdirs else TEMP_DIR

    print(f"[2/3] Applying updated files from {src_dir.name}...")
    for root, dirs, files in os.walk(src_dir):
        rel_root = Path(root).relative_to(src_dir)
        dest_root = BASE_DIR / rel_root
        dest_root.mkdir(parents=True, exist_ok=True)

        for file in files:
            if file in PRESERVE and (dest_root / file).exists():
                print(f"  [PRESERVED] {file}")
                continue
            src_file = Path(root) / file
            dest_file = dest_root / file
            shutil.copy2(src_file, dest_file)

    print("[3/3] Cleaning temporary files...")
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
    if ZIP_PATH.exists():
        try:
            os.remove(ZIP_PATH)
        except Exception:
            pass

    print("[SUCCESS] Electra files updated successfully!")
except Exception as e:
    print(f"[ERROR] Update process encountered an error: {e}")
"""
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(code)
    return runner_path


def create_windows_update_helper() -> Path:
    """Generates the clean Windows helper batch script calling update_runner.py."""
    helper_path = BASE_DIR / "update_helper.bat"
    _create_python_update_runner()

    script = f"""@echo off
title Electra - Windows Auto-Updater
cd /d "{BASE_DIR}"

echo ============================================================
echo         Electra - UPDATING APPLICATION FILES
echo ============================================================
echo Waiting for active server processes to close...
timeout /t 2 /nobreak > nul

if exist ".venv\\Scripts\\python.exe" (
    set "PYTHON_EXE=.venv\\Scripts\\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Executing update engine...
"%PYTHON_EXE%" update_runner.py

echo.
echo ============================================================
echo   [SUCCESS] Electra update completed!
echo   Restarting Electra Web Server...
echo ============================================================
start "" "start_server.bat"

(goto) 2>nul & del "update_runner.py" 2>nul & del "%~f0" 2>nul & exit
"""
    with open(helper_path, "w", encoding="utf-8") as f:
        f.write(script)
    return helper_path


def run_update() -> Tuple[bool, str]:
    """
    Downloads latest release from GitHub, safely replaces files without touching user configs/databases,
    and automatically restarts Electra server / systemd service.
    """
    system = platform.system()
    zip_path = BASE_DIR / "update.zip"

    logger.info("=== Starting Electra Auto-Update ===")

    # 1. Download and validate ZIP
    downloaded = download_valid_zip(zip_path)
    if not downloaded or not zip_path.exists():
        return False, "Αποτυχία λήψης έγκυρου πακέτου ενημέρωσης από το GitHub."

    # 2. Apply and Restart
    if system == "Windows":
        create_windows_update_helper()

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
