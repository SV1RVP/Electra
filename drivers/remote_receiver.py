from __future__ import annotations

import time
from typing import Any, Dict, Optional
from drivers.models import UPSData


class RemoteReceiver:
    """
    Manages telemetry received from remote UPS agents over IP/network.
    Maintains last-seen timestamps and automatically transitions to 'Offline'
    if heartbeat/telemetry expires.
    """

    def __init__(
        self,
        name: str = "Remote-UPS",
        location: str = "Remote Site",
        timeout_seconds: float = 30.0,
    ):
        self.name = name
        self.location = location
        self.timeout_seconds = timeout_seconds
        self.last_seen: float = 0.0
        self.latest_data: Optional[UPSData] = None
        self.remote_ip: Optional[str] = None

    def push_telemetry(self, payload: Dict[str, Any], client_ip: str = "unknown") -> UPSData:
        self.remote_ip = client_ip
        self.last_seen = time.time()

        name = payload.get("name", self.name)
        location = payload.get("location", self.location)

        data = UPSData(
            name=name,
            source=f"Remote IP: {client_ip}",
            connected=bool(payload.get("connected", True)),
            mode=payload.get("mode", "Line"),
            input_v=payload.get("input_v"),
            output_v=payload.get("output_v"),
            input_hz=payload.get("input_hz"),
            output_hz=payload.get("output_hz", payload.get("input_hz")),
            load_pct=payload.get("load_pct"),
            battery_v=payload.get("battery_v"),
            battery_pct=payload.get("battery_pct"),
            load_w_est=payload.get("load_w_est"),
            runtime_minutes=payload.get("runtime_minutes"),
            runtime_source=payload.get("runtime_source", "remote-agent"),
            temperature_c=payload.get("temperature_c"),
            beeper_on=payload.get("beeper_on"),
            battery_low=payload.get("battery_low"),
            fault=payload.get("fault"),
            raw=payload.get("raw"),
            error=payload.get("error"),
            last_updated=self.last_seen,
            location=location,
        )

        self.latest_data = data
        return data

    def read(self) -> UPSData:
        now = time.time()
        if self.latest_data is None:
            return UPSData(
                name=self.name,
                source="Remote IP (Awaiting agent)",
                connected=False,
                mode="Offline",
                error="No telemetry received yet from remote agent.",
                location=self.location,
                last_updated=0,
            )

        if now - self.last_seen > self.timeout_seconds:
            # Stale / connection lost
            stale = UPSData(
                name=self.latest_data.name,
                source=self.latest_data.source,
                connected=False,
                mode="Offline",
                error=f"Communication timeout: no signal for {int(now - self.last_seen)}s",
                location=self.latest_data.location,
                last_updated=self.last_seen,
            )
            return stale

        return self.latest_data
