"""
Electra - Multi-UPS MQTT & Home Assistant Discovery Service
Dynamic, multi-device, resilient MQTT integration for Home Assistant.
Supports local UPS units and dynamic network/remote agents.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion
    PAHO_V2 = True
except (ImportError, AttributeError):
    try:
        import paho.mqtt.client as mqtt
        CallbackAPIVersion = None
        PAHO_V2 = False
    except ImportError:
        mqtt = None
        CallbackAPIVersion = None
        PAHO_V2 = False


def _ensure_paho() -> bool:
    """Dynamically re-attempts importing paho-mqtt if it was not available at initial load."""
    global mqtt, CallbackAPIVersion, PAHO_V2
    if mqtt is not None:
        return True
    try:
        import paho.mqtt.client as _mqtt
        from paho.mqtt.enums import CallbackAPIVersion as _cb
        mqtt = _mqtt
        CallbackAPIVersion = _cb
        PAHO_V2 = True
        return True
    except (ImportError, AttributeError):
        try:
            import paho.mqtt.client as _mqtt
            mqtt = _mqtt
            CallbackAPIVersion = None
            PAHO_V2 = False
            return True
        except ImportError:
            mqtt = None
            CallbackAPIVersion = None
            PAHO_V2 = False
            return False

logger = logging.getLogger("Electra.MQTT")


def slugify_slot(slot: str) -> str:
    """Converts a slot name like 'Local-1' or 'Remote-2' to a safe topic/unique_id slug like 'local_1'."""
    return str(slot).strip().lower().replace("-", "_").replace(" ", "_")


class MQTTService:
    """
    Manages connection to MQTT broker and publishes Home Assistant Discovery
    and live telemetry for all local and network UPS units dynamically.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, app_version: str = "1.5.0"):
        self.app_version = app_version
        self._lock = threading.Lock()
        self._client: Optional[Any] = None
        self._connected: bool = False
        self._started: bool = False
        self._discovered_slots: Set[str] = set()
        self._cached_telemetry: Dict[str, Dict[str, Any]] = {}
        self._last_publish_time: float = 0.0
        self._last_error: Optional[str] = None

        self.update_config(config or {})

    def update_config(self, config: Dict[str, Any]) -> None:
        """Applies updated configuration and restarts MQTT connection if needed."""
        with self._lock:
            self.config = config.get("mqtt", config) if "mqtt" in config else config
            self.enabled = bool(self.config.get("enabled", False))
            self.host = str(self.config.get("host", "")).strip()
            self.port = int(self.config.get("port", 1883))
            self.username = str(self.config.get("username", "")).strip()
            self.password = str(self.config.get("password", "")).strip()
            self.client_id = str(self.config.get("client_id", "electra_ups_monitor")).strip() or "electra_ups_monitor"
            self.discovery_prefix = str(self.config.get("discovery_prefix", "homeassistant")).strip() or "homeassistant"
            self.base_topic = str(self.config.get("base_topic", "electra/ups")).strip().rstrip("/") or "electra/ups"
            self.qos = int(self.config.get("qos", 1))
            self.retain = bool(self.config.get("retain", True))

            self.global_status_topic = f"{self.base_topic}/status"

        if self._started:
            logger.info("MQTT configuration updated; restarting client connection...")
            self.stop()
            if self.is_configured:
                self.start()

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.host and _ensure_paho())

    @property
    def is_connected(self) -> bool:
        return bool(self._connected and self.is_configured)

    def get_status(self) -> Dict[str, Any]:
        """Returns live MQTT operational status for WebUI presentation."""
        return {
            "enabled": self.enabled,
            "connected": self.is_connected,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
            "base_topic": self.base_topic,
            "discovery_prefix": self.discovery_prefix,
            "discovered_slots": sorted(list(self._discovered_slots)),
            "published_count": len(self._discovered_slots),
            "last_publish_time": self._last_publish_time,
            "last_publish_iso": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._last_publish_time)) if self._last_publish_time > 0 else None,
            "error": self._last_error,
        }

    def start(self) -> None:
        """Starts asynchronous background MQTT client."""
        if not self.is_configured:
            return

        if not _ensure_paho() or mqtt is None:
            self._last_error = "paho-mqtt library is not installed in the active Python environment"
            logger.error(self._last_error)
            return

        with self._lock:
            if self._started:
                return

            try:
                if PAHO_V2:
                    self._client = mqtt.Client(
                        callback_api_version=CallbackAPIVersion.VERSION2,
                        client_id=self.client_id,
                    )
                else:
                    self._client = mqtt.Client(client_id=self.client_id)

                if self.username:
                    self._client.username_pw_set(self.username, self.password or None)

                # Last Will & Testament (LWT) for Electra Central Monitor
                self._client.will_set(
                    topic=self.global_status_topic,
                    payload="offline",
                    qos=self.qos,
                    retain=self.retain,
                )

                self._client.on_connect = self._on_connect
                self._client.on_disconnect = self._on_disconnect

                # Auto-reconnect backoff (1s - 60s)
                self._client.reconnect_delay_set(min_delay=1, max_delay=60)

                logger.info(f"Connecting to MQTT Broker at {self.host}:{self.port} (Client ID: {self.client_id})...")
                self._client.connect_async(self.host, self.port, keepalive=60)
                self._client.loop_start()
                self._started = True
                self._last_error = None
            except Exception as exc:
                self._last_error = str(exc)
                logger.error(f"Failed to start MQTT client: {exc}")

    def stop(self) -> None:
        """Gracefully disconnects and terminates MQTT client loop."""
        with self._lock:
            if not self._started or self._client is None:
                return

            try:
                if self._connected:
                    # Publish global offline status and offline for each UPS
                    self._client.publish(
                        self.global_status_topic, "offline", qos=self.qos, retain=self.retain
                    )
                    for slot in list(self._discovered_slots):
                        slot_slug = slugify_slot(slot)
                        self._client.publish(
                            f"{self.base_topic}/{slot_slug}/status",
                            "offline",
                            qos=self.qos,
                            retain=self.retain,
                        )
                    time.sleep(0.1)

                self._client.loop_stop()
                self._client.disconnect()
                logger.info("MQTT service stopped.")
            except Exception as exc:
                logger.warning(f"Error during MQTT shutdown: {exc}")
            finally:
                self._connected = False
                self._started = False

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: Any, properties: Any = None) -> None:
        code = getattr(rc, "value", rc)
        if code == 0:
            self._connected = True
            self._last_error = None
            logger.info(f"Connected to MQTT Broker at {self.host}:{self.port}")

            # 1. Global Online Availability
            self._client.publish(
                self.global_status_topic, "online", qos=self.qos, retain=self.retain
            )

            # 2. Re-publish Home Assistant Discovery for all known slots
            for slot in list(self._discovered_slots):
                self._publish_slot_discovery(slot)

            # 3. Re-publish last known telemetry states
            for slot, state in list(self._cached_telemetry.items()):
                self._publish_slot_state(slot, state)
        else:
            self._connected = False
            self._last_error = f"Connection refused by broker (Code: {code})"
            logger.warning(f"MQTT connection refused with result code: {rc}")

    def _on_disconnect(self, client: Any, userdata: Any, disconnect_flags_or_rc: Any, rc: Any = None, properties: Any = None) -> None:
        self._connected = False
        raw_code = rc if rc is not None else disconnect_flags_or_rc
        val = getattr(raw_code, "value", raw_code)
        if val not in (0, None):
            self._last_error = f"Disconnected from broker (code {val})"
        logger.warning(f"Disconnected from MQTT broker (code: {val}). Reconnecting in background...")

    def _get_entity_definitions(self, slot_slug: str) -> List[Dict[str, Any]]:
        """Standardized Home Assistant entity schemas for each UPS unit."""
        return [
            {
                "component": "sensor",
                "key": "mode",
                "name": "Status Mode",
                "unique_id": f"electra_{slot_slug}_mode",
                "icon": "mdi:power-settings",
            },
            {
                "component": "sensor",
                "key": "input_v",
                "name": "Input Voltage",
                "unique_id": f"electra_{slot_slug}_input_v",
                "unit_of_measurement": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "icon": "mdi:sine-wave",
            },
            {
                "component": "sensor",
                "key": "output_v",
                "name": "Output Voltage",
                "unique_id": f"electra_{slot_slug}_output_v",
                "unit_of_measurement": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "icon": "mdi:power-plug",
            },
            {
                "component": "sensor",
                "key": "input_hz",
                "name": "Input Frequency",
                "unique_id": f"electra_{slot_slug}_input_hz",
                "unit_of_measurement": "Hz",
                "device_class": "frequency",
                "state_class": "measurement",
                "icon": "mdi:current-ac",
            },
            {
                "component": "sensor",
                "key": "output_hz",
                "name": "Output Frequency",
                "unique_id": f"electra_{slot_slug}_output_hz",
                "unit_of_measurement": "Hz",
                "device_class": "frequency",
                "state_class": "measurement",
                "icon": "mdi:current-ac",
            },
            {
                "component": "sensor",
                "key": "load_pct",
                "name": "Load Percentage",
                "unique_id": f"electra_{slot_slug}_load_pct",
                "unit_of_measurement": "%",
                "state_class": "measurement",
                "icon": "mdi:gauge",
            },
            {
                "component": "sensor",
                "key": "load_w_est",
                "name": "Load Power",
                "unique_id": f"electra_{slot_slug}_load_w",
                "unit_of_measurement": "W",
                "device_class": "power",
                "state_class": "measurement",
                "icon": "mdi:flash",
            },
            {
                "component": "sensor",
                "key": "load_a_est",
                "name": "Load Current",
                "unique_id": f"electra_{slot_slug}_load_a",
                "unit_of_measurement": "A",
                "device_class": "current",
                "state_class": "measurement",
                "icon": "mdi:sine-wave",
            },
            {
                "component": "sensor",
                "key": "battery_pct",
                "name": "Battery Level",
                "unique_id": f"electra_{slot_slug}_battery_pct",
                "unit_of_measurement": "%",
                "device_class": "battery",
                "state_class": "measurement",
            },
            {
                "component": "sensor",
                "key": "battery_v",
                "name": "Battery Voltage",
                "unique_id": f"electra_{slot_slug}_battery_v",
                "unit_of_measurement": "V",
                "device_class": "voltage",
                "state_class": "measurement",
                "icon": "mdi:car-battery",
            },
            {
                "component": "sensor",
                "key": "runtime_minutes",
                "name": "Runtime Remaining",
                "unique_id": f"electra_{slot_slug}_runtime_min",
                "unit_of_measurement": "min",
                "device_class": "duration",
                "state_class": "measurement",
                "icon": "mdi:timer-outline",
            },
            {
                "component": "sensor",
                "key": "temperature_c",
                "name": "Temperature",
                "unique_id": f"electra_{slot_slug}_temperature",
                "unit_of_measurement": "°C",
                "device_class": "temperature",
                "state_class": "measurement",
            },
            {
                "component": "binary_sensor",
                "key": "battery_low",
                "name": "Battery Low",
                "unique_id": f"electra_{slot_slug}_battery_low",
                "device_class": "battery",
                "payload_on": True,
                "payload_off": False,
                "icon": "mdi:battery-alert",
            },
            {
                "component": "binary_sensor",
                "key": "fault",
                "name": "Fault Alert",
                "unique_id": f"electra_{slot_slug}_fault",
                "device_class": "problem",
                "payload_on": True,
                "payload_off": False,
                "icon": "mdi:alert-circle",
            },
            {
                "component": "binary_sensor",
                "key": "connected",
                "name": "Connectivity",
                "unique_id": f"electra_{slot_slug}_connected",
                "device_class": "connectivity",
                "payload_on": True,
                "payload_off": False,
            },
            {
                "component": "sensor",
                "key": "timestamp",
                "name": "Last Telemetry",
                "unique_id": f"electra_{slot_slug}_last_seen",
                "device_class": "timestamp",
                "icon": "mdi:clock-check-outline",
            },
        ]

    def _publish_slot_discovery(
        self,
        slot_name: str,
        display_name: Optional[str] = None,
        location: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        """Publishes Home Assistant MQTT Discovery configuration for a single UPS device."""
        if not self._client or not self._connected:
            return

        slot_slug = slugify_slot(slot_name)
        disp_name = display_name or slot_name
        loc = location or "Local Port"
        src = source or ("Remote IP" if slot_name.startswith("Remote") else "USB HID")

        state_topic = f"{self.base_topic}/{slot_slug}/state"
        avail_topic = self.global_status_topic
        slot_status_topic = f"{self.base_topic}/{slot_slug}/status"

        # Ensure slot availability is online
        try:
            self._client.publish(slot_status_topic, "online", qos=self.qos, retain=self.retain)
        except Exception:
            pass

        device_info = {
            "identifiers": [f"electra_ups_{slot_slug}"],
            "name": f"Electra UPS - {disp_name}",
            "manufacturer": "Electra / RFNews",
            "model": f"{src} Monitor ({loc})",
            "sw_version": self.app_version,
        }

        entities = self._get_entity_definitions(slot_slug)
        for ent in entities:
            comp = ent.get("component", "sensor")
            ent_key = ent["key"]
            disc_topic = f"{self.discovery_prefix}/{comp}/electra_{slot_slug}/{ent_key}/config"

            payload: Dict[str, Any] = {
                "name": ent["name"],
                "unique_id": ent["unique_id"],
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{ent_key} }}}}",
                "availability_topic": avail_topic,
                "payload_available": "online",
                "payload_not_available": "offline",
                "device": device_info,
            }

            if comp == "binary_sensor":
                payload["payload_on"] = ent.get("payload_on", True)
                payload["payload_off"] = ent.get("payload_off", False)

            for opt_key in ("unit_of_measurement", "device_class", "state_class", "icon"):
                if opt_key in ent:
                    payload[opt_key] = ent[opt_key]

            try:
                self._client.publish(
                    disc_topic,
                    json.dumps(payload, ensure_ascii=False),
                    qos=self.qos,
                    retain=self.retain,
                )
            except Exception as e:
                logger.warning(f"Failed to publish discovery for {slot_name}/{ent_key}: {e}")

        logger.info(f"Published Home Assistant Discovery for UPS '{disp_name}' ({slot_name}) [{len(entities)} entities].")

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cleans and validates numbers and booleans for valid JSON transmission."""
        clean: Dict[str, Any] = {}
        for k, v in data.items():
            if v is None:
                clean[k] = None
            elif isinstance(v, bool):
                clean[k] = v
            elif isinstance(v, (int,)):
                clean[k] = v
            elif isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    clean[k] = None
                else:
                    clean[k] = round(v, 2)
            else:
                clean[k] = str(v)
        return clean

    def _publish_slot_state(self, slot_name: str, payload_data: Dict[str, Any]) -> None:
        """Publishes the state JSON payload and slot availability."""
        if not self._client or not self._connected:
            return

        slot_slug = slugify_slot(slot_name)
        state_topic = f"{self.base_topic}/{slot_slug}/state"
        avail_topic = f"{self.base_topic}/{slot_slug}/status"

        is_connected = bool(payload_data.get("connected", True))
        status_payload = "online" if is_connected else "offline"

        try:
            # 1. Availability for this specific UPS
            self._client.publish(avail_topic, status_payload, qos=self.qos, retain=self.retain)

            # 2. State Telemetry JSON
            clean_state = self._sanitize_data(payload_data)
            self._client.publish(state_topic, json.dumps(clean_state, ensure_ascii=False), qos=self.qos, retain=self.retain)
            self._last_publish_time = time.time()
        except Exception as e:
            self._last_error = f"Error publishing state for {slot_name}: {e}"
            logger.warning(self._last_error)

    def publish_ups(self, ups_data: Any) -> None:
        """
        Publishes telemetry for an individual UPSData object.
        Automatically registers new devices via Home Assistant Discovery if seen for the first time.
        """
        if not self.is_configured:
            return

        slot_name = getattr(ups_data, "name", None) or getattr(ups_data, "slot_name", "Local-1")
        disp_name = getattr(ups_data, "display_name", None) or slot_name
        location = getattr(ups_data, "location", "Local Port")
        source = getattr(ups_data, "source", "Auto-Scan")

        # Dynamic multi-UPS discovery check
        if slot_name not in self._discovered_slots:
            self._discovered_slots.add(slot_name)
            if self._connected:
                self._publish_slot_discovery(slot_name, disp_name, location, source)

        iso_ts = datetime.now().astimezone().isoformat()

        state = {
            "slot_name": slot_name,
            "display_name": disp_name,
            "connected": bool(getattr(ups_data, "connected", False)),
            "mode": getattr(ups_data, "mode", "Offline"),
            "input_v": getattr(ups_data, "input_v", None),
            "output_v": getattr(ups_data, "output_v", None),
            "input_hz": getattr(ups_data, "input_hz", None),
            "output_hz": getattr(ups_data, "output_hz", None),
            "load_pct": getattr(ups_data, "load_pct", None),
            "load_w_est": getattr(ups_data, "load_w_est", None),
            "load_a_est": getattr(ups_data, "load_a_est", None),
            "battery_pct": getattr(ups_data, "battery_pct", None),
            "battery_v": getattr(ups_data, "battery_v", None),
            "runtime_minutes": getattr(ups_data, "runtime_minutes", None),
            "temperature_c": getattr(ups_data, "temperature_c", None),
            "battery_low": bool(getattr(ups_data, "battery_low", False)),
            "fault": bool(getattr(ups_data, "fault", False)),
            "test_active": bool(getattr(ups_data, "test_active", False)),
            "timestamp": iso_ts,
        }

        self._cached_telemetry[slot_name] = state

        if self._connected:
            self._publish_slot_state(slot_name, state)

    def publish_all(self, ups_list: List[Any]) -> None:
        """Batch helper to publish telemetry for all active and remote UPS devices."""
        if not self.is_configured or not ups_list:
            return
        for ups in ups_list:
            if ups:
                self.publish_ups(ups)
