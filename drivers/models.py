from __future__ import annotations

import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional, List


@dataclass
class UPSData:
    name: str
    source: str
    connected: bool = False
    mode: Optional[str] = "Offline"  # "Line", "Battery", "Bypass", "Fault", "Offline"
    input_v: Optional[float] = None
    output_v: Optional[float] = None
    input_hz: Optional[float] = None
    output_hz: Optional[float] = None
    load_pct: Optional[float] = None
    battery_v: Optional[float] = None
    battery_pct: Optional[float] = None
    load_w_est: Optional[float] = None
    runtime_minutes: Optional[float] = None
    runtime_source: Optional[str] = None
    temperature_c: Optional[float] = None
    beeper_on: Optional[bool] = None
    battery_low: Optional[bool] = None
    fault: Optional[bool] = None
    test_active: Optional[bool] = False
    last_self_test: Optional[Dict[str, Any]] = None
    raw: Optional[str] = None
    error: Optional[str] = None
    last_updated: float = field(default_factory=time.time)
    location: str = "Local"
    display_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["display_name"] = self.display_name or self.name
        d["last_updated_iso"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(self.last_updated)
        )
        return d


@dataclass
class UPSEvent:
    timestamp: float
    ups_name: str
    event_type: str  # POWER_OUTAGE, POWER_RESTORED, OVERLOAD, OVERLOAD_CLEARED, COMM_LOST, COMM_RESTORED, BATTERY_LOW, DAILY_REPORT, INFO
    message: str
    severity: str = "info"  # info, warning, critical, success
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp_iso"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)
        )
        return d
