from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
PROFILES_FILE = BASE_DIR / "profiles.json"
LEARNING_FILE = BASE_DIR / "learning.json"
DB_FILE = BASE_DIR / "ups_history.db"

DEFAULT_CONFIG: Dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 8088,
        "poll_interval_seconds": 2.0,
        "db_log_interval_seconds": 5.0,
    },
    "viber": {
        "enabled": True,
        "channel_token": "",
        "sender_name": "UPS Monitor",
        "receiver_id": "",
    },
    "alerts": {
        "power_outage_alert": True,
        "power_restore_alert": True,
        "outage_repeat_alert": True,
        "overload_alert": True,
        "disconnect_alert": True,
        "battery_low_alert": True,
        "daily_report": True,
        "self_test_alert": True,
    },
    "self_test": {
        "schedule_enabled": False,
        "frequency": "daily",
        "time": "09:00",
        "day_of_week": "sunday",
        "day_of_month": 1,
        "notify_viber": True,
        "target_slots": ["Local-1", "Local-2"],
    },
    "outage_repeat_interval_seconds": 60,
    "overload_threshold_pct": 70.0,
    "battery_low_threshold_pct": 20.0,
    "daily_report_time": "09:00",
    "db_log_interval_seconds": 60,
    "db_retention_days": 30,
    "db_log_on_change": True,
    "db_outage_fast_log": True,
    "remote_api_key": "ups_remote_secret_key_123",
    "language": "el",
    "ui_settings": {
        "theme": "cyberpunk",
        "language": "el",
        "sound_alarms": True,
        "sound_volume": 0.8,
    },
}

DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "Local-1": {
        "display_name": "Primary UPS (USB 1)",
        "location": "Local Port 1",
        "rated_w": 1200.0,
        "bank_v": 24.0,
        "battery_ah": 9.0,
        "inverter_efficiency": 0.85,
        "peukert_exponent": 1.15,
        "enabled": True,
    },
    "Local-2": {
        "display_name": "Secondary UPS (USB 2)",
        "location": "Local Port 2",
        "rated_w": 1200.0,
        "bank_v": 24.0,
        "battery_ah": 9.0,
        "inverter_efficiency": 0.85,
        "peukert_exponent": 1.15,
        "enabled": True,
    },
    "Remote-1": {
        "display_name": "Remote UPS (Network / IP)",
        "location": "Remote Site",
        "rated_w": 1200.0,
        "bank_v": 24.0,
        "battery_ah": 9.0,
        "inverter_efficiency": 0.85,
        "peukert_exponent": 1.15,
        "enabled": True,
    },
}


def load_json_file(path: Path, default_data: Any) -> Any:
    if not path.exists():
        save_json_file(path, default_data)
        return json.loads(json.dumps(default_data))
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Merge with default keys to ensure missing fields exist
            if isinstance(default_data, dict) and isinstance(data, dict):
                merged = json.loads(json.dumps(default_data))
                merged.update(data)
                return merged
            return data
    except Exception:
        return default_data


def save_json_file(path: Path, data: Any) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {path}: {e}")


def get_config() -> Dict[str, Any]:
    return load_json_file(CONFIG_FILE, DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    save_json_file(CONFIG_FILE, cfg)


def get_profiles() -> Dict[str, Dict[str, Any]]:
    return load_json_file(PROFILES_FILE, DEFAULT_PROFILES)


def save_profiles(profiles: Dict[str, Dict[str, Any]]) -> None:
    save_json_file(PROFILES_FILE, profiles)
