#!/usr/bin/env python3
"""
Electra Remote UPS Agent - Manual Auto-Updater
Author: Alexandros - Ermis Tsourapas (SV1RVP)
License: GNU AGPLv3

Safely updates the remote agent files from the central Electra server or GitHub,
while preserving and smartly migrating user configuration in agent_config.json.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' module is missing. Please run: pip install requests")
    sys.exit(1)

# Paths
AGENT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = AGENT_DIR / "agent_config.json"
BACKUP_CONFIG_FILE = AGENT_DIR / "agent_config.json.bak"

# Remote GitHub URLs (Fallback)
GITHUB_ZIP_URL = "https://github.com/SV1RVP/Electra/archive/refs/heads/main.zip"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/SV1RVP/Electra/main/remote_agent"

# Files that should be updated
UPDATABLE_FILES = [
    "ups_agent.py",
    "requirements.txt",
    "README.md",
    "install-windows.bat",
    "install-linux.sh",
    "run_agent.bat",
    "run_agent.sh",
    "uninstall-windows.bat",
    "uninstall-linux.sh",
    "update.py",
    "update.bat",
    "update.sh",
]


def print_banner():
    print("=" * 68)
    print("⚡ ELECTRA REMOTE UPS AGENT - MANUAL UPDATER")
    print("=" * 68)


def load_local_config() -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Loads existing agent_config.json.
    Returns (config_dict, is_valid_json).
    """
    if not CONFIG_FILE.exists():
        return None, True
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None, False
        return data, True
    except Exception as e:
        print(f"⚠️ Προειδοποίηση κατά την ανάγνωση του agent_config.json: {e}")
        return None, False


def merge_configuration(
    current_cfg: Optional[Dict[str, Any]],
    new_template: Dict[str, Any]
) -> Tuple[Dict[str, Any], bool, str]:
    """
    Smart config merge:
    - Preserves all existing user settings.
    - Appends any newly introduced configuration parameters.
    - Detects type collisions or breaking schema conflicts.
    Returns (merged_dict, has_critical_conflict, message).
    """
    if current_cfg is None:
        return new_template, False, "Δημιουργήθηκε αρχικό agent_config.json."

    has_conflict = False
    conflict_notes = []
    merged = dict(current_cfg)

    # Validate essential fields
    for essential_key in ("server_url", "api_key"):
        if essential_key not in merged or not str(merged[essential_key]).strip():
            has_conflict = True
            conflict_notes.append(f"Λείπει ή είναι κενό το βασικό πεδίο '{essential_key}'")

    for k, default_val in new_template.items():
        if k not in merged:
            merged[k] = default_val
            print(f"  ➕ Προστέθηκε νέα παράμετρος ρύθμισης: '{k}' = {default_val!r}")
        else:
            curr_val = merged[k]
            # Check type compatibility (numeric conversions allowed)
            curr_type = type(curr_val)
            def_type = type(default_val)
            is_num = curr_type in (int, float) and def_type in (int, float)
            if not is_num and curr_val is not None and default_val is not None:
                if curr_type is not def_type:
                    has_conflict = True
                    conflict_notes.append(
                        f"Το πεδίο '{k}' αναμενόταν τύπου {def_type.__name__}, βρέθηκε {curr_type.__name__}"
                    )

    msg = "; ".join(conflict_notes) if conflict_notes else "Όλες οι υπάρχουσες ρυθμίσεις συγχωνεύτηκαν επιτυχώς."
    return merged, has_conflict, msg


def download_from_central_server(cfg: Dict[str, Any]) -> Optional[bytes]:
    """Attempts to download update zip package directly from central Electra server."""
    server_push_url = cfg.get("server_url", "")
    api_key = cfg.get("api_key", "ups_remote_secret_key_123")
    if not server_push_url:
        return None

    try:
        parsed = urlparse(server_push_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        update_url = f"{base_url}/api/remote/agent/update-package"
        print(f"📡 Έλεγχος για πακέτο ενημέρωσης από τον κεντρικό διακομιστή ({update_url})...")

        headers = {
            "User-Agent": "Electra-Agent-Updater/1.4",
            "X-API-Key": api_key,
        }
        resp = requests.get(update_url, timeout=12, headers=headers)
        if resp.status_code == 200 and len(resp.content) > 500:
            if resp.content[:4] == b"PK\x03\x04":
                print(f"✅ Επιτυχής λήψη {len(resp.content) / 1024:.1f} KB από τον κεντρικό διακομιστή!")
                return resp.content
            else:
                print("⚠️ Το πακέτο από τον διακομιστή δεν ήταν έγκυρο αρχείο ZIP.")
        elif resp.status_code == 401:
            print("⚠️ Αποτυχία ταυτοποίησης στον διακομιστή (Λανθασμένο API Key).")
        else:
            print(f"ℹ️ Ο διακομιστής επέστρεψε HTTP {resp.status_code}.")
    except Exception as e:
        print(f"ℹ️ Δεν κατέστη δυνατή η απευθείας σύνδεση με τον διακομιστή: {e}")

    return None


def download_from_github(cfg: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    """Downloads repository archive from GitHub."""
    print(f"⬇️  Λήψη πακέτου ενημέρωσης από το GitHub...")
    headers = {"User-Agent": "Electra-Agent-Updater/1.4"}

    # Use optional github_token from agent_config.json or environment
    gh_token = None
    if cfg and cfg.get("github_token"):
        gh_token = cfg.get("github_token")
    elif os.environ.get("GITHUB_TOKEN"):
        gh_token = os.environ.get("GITHUB_TOKEN")

    if gh_token:
        headers["Authorization"] = f"token {gh_token}"

    try:
        resp = requests.get(GITHUB_ZIP_URL, timeout=25, headers=headers)
        if resp.status_code == 200 and len(resp.content) > 1000:
            if resp.content[:4] == b"PK\x03\x04":
                print(f"✅ Λήφθηκαν {len(resp.content) / 1024:.1f} KB από το GitHub.")
                return resp.content
            else:
                print(f"❌ Το ληφθέν αρχείο δεν είναι έγκυρο ZIP.")
        elif resp.status_code == 404 and not gh_token:
            print("ℹ️ Το GitHub επέστρεψε 404 (Το αποθετήριο μπορεί να είναι Private).")
        else:
            print(f"❌ Αποτυχία λήψης από GitHub. HTTP status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Σφάλμα σύνδεσης με GitHub: {e}")
    return None


def apply_update_from_zip(zip_bytes: bytes) -> bool:
    """Extracts remote_agent files from zip and applies update safely."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as e:
        print(f"❌ Αποτυχία αποσυμπίεσης ZIP: {e}")
        return False

    # Find prefix (either 'remote_agent/' or 'Electra-main/remote_agent/')
    prefix = None
    for name in zf.namelist():
        if name.endswith("ups_agent.py"):
            prefix = name[:-len("ups_agent.py")]
            break

    if prefix is None:
        print("❌ Δεν εντοπίστηκαν τα αρχεία του remote_agent στο πακέτο.")
        return False

    # 1. Read existing config
    current_cfg, is_valid = load_local_config()

    # 2. Extract incoming template config if available
    incoming_cfg_path = prefix + "agent_config.json"
    new_template = {}
    if incoming_cfg_path in zf.namelist():
        try:
            raw_new = zf.read(incoming_cfg_path).decode("utf-8")
            new_template = json.loads(raw_new)
        except Exception:
            pass

    # 3. Handle smart config preservation & migration
    if current_cfg is not None or not is_valid:
        # Backup existing config
        if CONFIG_FILE.exists():
            try:
                shutil.copy2(CONFIG_FILE, BACKUP_CONFIG_FILE)
                print(f"💾 Δημιουργήθηκε αντίγραφο ασφαλείας: {BACKUP_CONFIG_FILE.name}")
            except Exception as e:
                print(f"⚠️ Προειδοποίηση κατά το backup: {e}")

        merged_cfg, has_conflict, reason = merge_configuration(current_cfg, new_template)

        if has_conflict or not is_valid:
            print("\n" + "!" * 72)
            print("🚨 ΣΗΜΑΝΤΙΚΗ ΕΙΔΟΠΟΙΗΣΗ / IMPORTANT CONFIGURATION NOTICE:")
            print("Το αρχείο ρυθμίσεων (agent_config.json) χρειάζεται έλεγχο και επαναρρύθμιση!")
            print(f"Αιτία: {reason}")
            print(f"Το προηγούμενο αρχείο σας διατηρήθηκε ως: {BACKUP_CONFIG_FILE.name}")
            print("Παρακαλούμε ανοίξτε το 'agent_config.json' και επιβεβαιώστε τις ρυθμίσεις σας.")
            print("!" * 72 + "\n")
        else:
            print(f"🛡️  Διατηρήθηκαν όλες οι υπάρχουσες ρυθμίσεις σας ({reason})")

        # Write merged config back safely
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(merged_cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Αποτυχία αποθήκευσης ρυθμίσεων: {e}")
    else:
        # First-time initial setup
        if new_template:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_template, f, indent=2, ensure_ascii=False)
            print("✨ Δημιουργήθηκε αρχικό agent_config.json.")

    # 4. Extract and update all code files safely
    updated_count = 0
    for file_name in UPDATABLE_FILES:
        member = prefix + file_name
        if member in zf.namelist():
            content = zf.read(member)
            target = AGENT_DIR / file_name
            try:
                target.write_bytes(content)
                updated_count += 1
                print(f"  🔄 Ενημερώθηκε: {file_name}")
            except Exception as e:
                print(f"  ⚠️ Δεν ήταν δυνατή η ενημέρωση του {file_name}: {e}")

    print(f"\n✅ Ενημερώθηκαν επιτυχώς {updated_count} αρχεία κώδικα.")
    return True


def run_manual_update():
    print_banner()
    print(f"📁 Φάκελος Agent: {AGENT_DIR}")

    current_cfg, _ = load_local_config()

    # Step 1: Try downloading directly from central Electra server (LAN/WireGuard)
    zip_bytes = None
    if current_cfg:
        zip_bytes = download_from_central_server(current_cfg)

    # Step 2: Fallback to GitHub download
    if not zip_bytes:
        zip_bytes = download_from_github(current_cfg)

    if zip_bytes:
        ok = apply_update_from_zip(zip_bytes)
        if ok:
            print("\n" + "=" * 68)
            print("🎉 Η ΕΝΗΜΕΡΩΣΗ ΟΛΟΚΛΗΡΩΘΗΚΕ ΜΕ ΕΠΙΤΥΧΙΑ! (Update Complete)")
            print("Μπορείτε τώρα να εκκινήσετε τον agent:")
            print("  • Windows: run_agent.bat")
            print("  • Linux  : ./run_agent.sh")
            print("=" * 68)
            return

    print("\n❌ Η ενημέρωση απέτυχε. Ελέγξτε τη σύνδεση δικτύου με τον κεντρικό server ή το GitHub.")


if __name__ == "__main__":
    run_manual_update()
