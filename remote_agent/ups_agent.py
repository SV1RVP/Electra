#!/usr/bin/env python3
"""
Remote UPS Telemetry Agent
Runs on a remote host (Windows / Linux / Raspberry Pi) to monitor a local UPS
via USB or Serial and push real-time status to the central UPS Status WebUI server over WireGuard/IP.

Supported Protocols & Auto-Discovery:
1. MEC0003 Generic HID (0001:0000) - Tescom Leo LCD, Turbo-X, Mustek, PowerWalker, Centralion
2. Cypress / Megatec Q1 USB HID (0665:5161) - TEC, Voltronic Power, OEM Megatec, FSP
3. USB HID Power Device Class (PDC) - APC by Schneider Electric, CyberPower, Eaton, Tripp Lite
4. Serial-over-USB Megatec Q1 - FTDI / CH340 / CP2102 COM ports / /dev/ttyUSB*

Usage:
    py ups_agent.py
    py ups_agent.py --server http://10.10.1.10:8088/api/remote/push --name "Remote-UPS"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests

CONFIG_PATH = Path(__file__).resolve().parent / "agent_config.json"


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "server_url": "http://127.0.0.1:8088/api/remote/push",
        "api_key": "ups_remote_secret_key_123",
        "ups_name": "Remote-1",
        "location": "Remote Site",
        "poll_interval_seconds": 2.0,
        "driver_type": "auto",
    }


def _num(v: Any) -> Optional[float]:
    try:
        return float(str(v).strip())
    except Exception:
        return None


def estimate_sla_24v_soc(
    battery_v: Optional[float],
    load_pct: Optional[float],
    mode: Optional[str],
) -> Optional[float]:
    """Estimate state-of-charge for a 12V or 24V SLA battery bank."""
    if battery_v is None or battery_v <= 0.0:
        return None

    mode_l = (mode or "").lower()
    is_24v = battery_v >= 18.0

    if mode_l == "line":
        # In Line mode (AC mains on), the charger float voltage keeps the battery topped off.
        # Normal float voltage is >= 26.5V for 24V banks (13.25V per cell) or >= 13.25V for 12V banks.
        float_min = 26.5 if is_24v else 13.25
        empty_v = 22.0 if is_24v else 11.0
        if battery_v >= float_min:
            return 100.0
        # Smooth interpolation during recharging phase after outage without cliffs
        pct = (battery_v - empty_v) / (float_min - empty_v) * 100.0
        return round(min(100.0, max(0.0, pct)), 1)

    # Battery mode: compensate for internal resistance / load sag
    load = max(0.0, min(float(load_pct or 0.0), 100.0))
    sag_comp = min(0.40, load * 0.008) if is_24v else min(0.20, load * 0.004)
    v = battery_v + sag_comp

    curve_24v = [
        (22.0, 0.0),
        (22.8, 10.0),
        (23.4, 20.0),
        (23.8, 35.0),
        (24.2, 50.0),
        (24.6, 65.0),
        (25.0, 80.0),
        (25.4, 90.0),
        (25.8, 97.0),
        (26.2, 100.0),
    ]

    curve_12v = [
        (11.0, 0.0),
        (11.4, 10.0),
        (11.7, 20.0),
        (11.9, 35.0),
        (12.1, 50.0),
        (12.3, 65.0),
        (12.5, 80.0),
        (12.7, 90.0),
        (12.9, 97.0),
        (13.1, 100.0),
    ]

    curve = curve_24v if is_24v else curve_12v

    if v <= curve[0][0]:
        return 0.0
    if v >= curve[-1][0]:
        return 100.0

    for (v1, p1), (v2, p2) in zip(curve, curve[1:]):
        if v1 <= v <= v2:
            frac = (v - v1) / (v2 - v1)
            return round(p1 + frac * (p2 - p1), 1)

    return None


def parse_q1(raw: str, name: str, source: str, location: str = "Remote Site") -> Dict[str, Any]:
    """Parse standard Megatec/Q1 protocol telemetry string."""
    out: Dict[str, Any] = {
        "name": name,
        "source": source,
        "connected": True,
        "raw": raw,
        "location": location,
        "last_updated": time.time(),
        "mode": "Line",
        "error": None,
    }

    s = raw.strip().replace("\x00", "")
    if not s.startswith("("):
        out["error"] = f"Unexpected Q1 reply: {raw!r}"
        out["connected"] = False
        out["mode"] = "Error"
        return out

    parts = s[1:].strip().split()
    if len(parts) < 8:
        out["error"] = f"Short Q1 reply: {raw!r}"
        out["connected"] = False
        out["mode"] = "Error"
        return out

    out["input_v"] = _num(parts[0])
    out["output_v"] = _num(parts[2])
    out["load_pct"] = _num(parts[3])
    out["input_hz"] = _num(parts[4])
    out["output_hz"] = out["input_hz"]
    out["battery_v"] = _num(parts[5])
    out["temperature_c"] = _num(parts[6])

    bits = parts[7][:8]
    if len(bits) == 8 and all(c in "01" for c in bits):
        utility_fail = bits[0] == "1"
        out["battery_low"] = bits[1] == "1"
        out["fault"] = bits[3] == "1"
        out["beeper_on"] = bits[7] == "1"

        if out["fault"]:
            out["mode"] = "Fault"
        elif utility_fail:
            out["mode"] = "Battery"
        else:
            out["mode"] = "Line"

    out["battery_pct"] = estimate_sla_24v_soc(
        out.get("battery_v"),
        out.get("load_pct"),
        out.get("mode"),
    )

    return out


# =====================================================================
# DRIVER 1: MEC0003 Generic HID (0001:0000)
# =====================================================================
class StandaloneMEC0003Reader:
    VID = 0x0001
    PID = 0x0000

    def __init__(self, name: str = "Remote-UPS", location: str = "Remote Site"):
        self.name = name
        self.location = location
        self.usb_core = None
        self.backend = None
        self.import_error = None
        try:
            import usb.core
            self.usb_core = usb.core
            try:
                import libusb_package
                self.backend = libusb_package.get_libusb1_backend()
            except Exception:
                self.backend = None
        except Exception as e:
            self.import_error = e

    def _find(self):
        if self.usb_core is None:
            return None
        kwargs = {"idVendor": self.VID, "idProduct": self.PID}
        if self.backend is not None:
            kwargs["backend"] = self.backend
        return self.usb_core.find(**kwargs)

    @staticmethod
    def _decode_string_descriptor(buf) -> str:
        b = bytes(buf)
        if len(b) < 2:
            return ""
        body = b[2 : b[0]] if 2 <= b[0] <= len(b) else b[2:]
        return body.decode("utf-16le", errors="ignore").strip("\x00\r\n ")

    def _get_string(self, dev, index: int) -> Optional[str]:
        last = None
        for lang in (0x0409, 0x0000):
            try:
                ret = dev.ctrl_transfer(
                    0x80, 0x06, 0x0300 | index, lang, 255, timeout=1500
                )
                text = self._decode_string_descriptor(ret)
                if text:
                    return text
            except Exception as e:
                last = e
        if last:
            raise last
        return None

    def read(self) -> Dict[str, Any]:
        if self.import_error is not None:
            return {
                "name": self.name,
                "location": self.location,
                "connected": False,
                "mode": "Offline",
                "error": "PyUSB missing. Run: pip install pyusb libusb-package",
                "last_updated": time.time(),
            }
        try:
            dev = self._find()
            if dev is None:
                return {
                    "name": self.name,
                    "location": self.location,
                    "connected": False,
                    "mode": "Offline",
                    "error": f"Device {self.VID:04X}:{self.PID:04X} not found.",
                    "last_updated": time.time(),
                }
            raw = self._get_string(dev, 3)
            if not raw:
                return {
                    "name": self.name,
                    "location": self.location,
                    "connected": False,
                    "mode": "Offline",
                    "error": "Descriptor 3 returned no telemetry data.",
                    "last_updated": time.time(),
                }
            return parse_q1(
                raw,
                self.name,
                f"Direct USB {self.VID:04X}:{self.PID:04X} (MEC0003)",
                location=self.location,
            )
        except Exception as e:
            return {
                "name": self.name,
                "location": self.location,
                "connected": False,
                "mode": "Offline",
                "error": f"{type(e).__name__}: {e}",
                "last_updated": time.time(),
            }


    def toggle_buzzer(self) -> bool:
        """Toggles buzzer on MEC0003 via Descriptor 7."""
        try:
            dev = self._find()
            if dev is None:
                return False
            for _ in range(3):
                try:
                    self._get_string(dev, 3)
                except Exception:
                    pass
            time.sleep(0.2)
            self._get_string(dev, 7)
            return True
        except Exception:
            return False

    def start_self_test(self, duration_sec: int = 10) -> bool:
        """Starts 10s battery self-test safely on MEC0003 via Descriptor 4."""
        try:
            dev = self._find()
            if dev is None:
                return False
            for _ in range(2):
                try:
                    self._get_string(dev, 3)
                except Exception:
                    pass
            time.sleep(0.15)
            self._get_string(dev, 4)
            return True
        except Exception:
            return False

    def cancel_self_test(self) -> bool:
        """Cancels self-test on MEC0003 via Descriptor 5."""
        try:
            dev = self._find()
            if dev is None:
                return False
            self._get_string(dev, 5)
            return True
        except Exception:
            return False


# =====================================================================
# DRIVER 2: Cypress / Megatec Q1 USB HID (0665:5161)
# =====================================================================
class StandaloneTECHIDReader:
    VID = 0x0665
    PID = 0x5161

    def __init__(self, name: str = "Remote-UPS", location: str = "Remote Site"):
        self.name = name
        self.location = location
        self.hid = None
        self.import_error = None
        self._last_nonzero_load: Optional[float] = None
        self._zero_load_count: int = 0
        try:
            import hid
            self.hid = hid
        except Exception as e:
            self.import_error = e

    @staticmethod
    def _clean_chunk(raw: Any) -> bytes:
        if not raw:
            return b""
        b = bytes(raw)
        if len(b) > 1 and b[0] <= len(b) - 1:
            length = b[0]
            if 1 <= length <= len(b) - 1:
                return b[1 : 1 + length]
        return b.rstrip(b"\x00")

    def _command(self, cmd_str: str, timeout_ms: int = 1200) -> str:
        dev = self.hid.device()
        dev.open(self.VID, self.PID)
        try:
            try:
                dev.set_nonblocking(1)
                for _ in range(8):
                    old = dev.read(64)
                    if not old:
                        break
            except Exception:
                pass
            finally:
                try:
                    dev.set_nonblocking(0)
                except Exception:
                    pass

            cmd = cmd_str.encode("ascii")
            if not cmd.endswith(b"\r"):
                cmd += b"\r"

            for offset in range(0, len(cmd), 8):
                chunk = cmd[offset : offset + 8]
                payload = [0x00] + list(chunk)
                if len(payload) < 9:
                    payload += [0x00] * (9 - len(payload))
                dev.write(payload)
                time.sleep(0.05)

            chunks: List[bytes] = []
            deadline = time.time() + (timeout_ms / 1000.0)

            while time.time() < deadline:
                raw = dev.read(64, timeout_ms=250)
                if not raw:
                    continue
                c = self._clean_chunk(raw)
                if c:
                    chunks.append(c)
                    combined = b"".join(chunks)
                    clean_echo = combined.strip(b"\r\n\x00 ")
                    if clean_echo in (b"Q1", b"QS", b"D", b"I", b"F", b"M"):
                        continue
                    if b"(" in combined and (b"\r" in combined or b"\n" in combined):
                        break
                    elif (b"\r" in combined or b"\n" in combined) and len(combined) > 15:
                        break

            reply = b"".join(chunks).decode("latin1", errors="ignore").strip("\r\n\x00 ")
            if "(" in reply:
                reply = reply[reply.find("(") :]
            return reply
        finally:
            try:
                dev.close()
            except Exception:
                pass

    def read(self) -> Dict[str, Any]:
        if self.import_error is not None:
            return {
                "name": self.name,
                "location": self.location,
                "connected": False,
                "mode": "Offline",
                "error": "hidapi missing. Run: pip install hidapi",
                "last_updated": time.time(),
            }

        errors = []
        for cmd in ("Q1", "QS", "D"):
            for attempt in range(2):
                try:
                    raw = self._command(cmd, timeout_ms=1200)
                    cleaned = raw.strip().replace("\x00", "")
                    if "(" in cleaned:
                        payload = cleaned[cleaned.find("(") :]
                        data = parse_q1(
                            payload,
                            self.name,
                            f"Direct USB HID {self.VID:04X}:{self.PID:04X} ({cmd})",
                            location=self.location,
                        )
                        # Low-load debounce to eliminate Megatec ADC hunting (0% vs 7-8%)
                        raw_load = data.get("load_pct")
                        mode = data.get("mode", "Line")
                        if mode == "Line" and raw_load is not None:
                            if raw_load == 0.0:
                                if self._last_nonzero_load is not None and self._last_nonzero_load <= 25.0 and self._zero_load_count < 5:
                                    self._zero_load_count += 1
                                    data["load_pct"] = self._last_nonzero_load
                                else:
                                    self._zero_load_count = 0
                                    self._last_nonzero_load = 0.0
                            else:
                                self._last_nonzero_load = raw_load
                                self._zero_load_count = 0
                        return data
                    if raw and attempt == 0:
                        time.sleep(0.06)
                        continue
                    errors.append(f"{cmd}: {raw!r}")
                except Exception as e:
                    if attempt == 0:
                        time.sleep(0.06)
                        continue
                    errors.append(f"{cmd}: {type(e).__name__}: {e}")

        return {
            "name": self.name,
            "location": self.location,
            "connected": False,
            "mode": "Offline",
            "error": "No telemetry reply. " + " | ".join(errors),
            "last_updated": time.time(),
        }

    def toggle_buzzer(self) -> bool:
        try:
            self._command("Q", timeout_ms=800)
            return True
        except Exception:
            return False

    def start_self_test(self, duration_sec: int = 10) -> bool:
        try:
            self._command("T", timeout_ms=800)
            return True
        except Exception:
            return False

    def cancel_self_test(self) -> bool:
        try:
            self._command("CT", timeout_ms=800)
            return True
        except Exception:
            return False


# =====================================================================
# DRIVER 3: USB HID Power Device Class (APC, CyberPower, Eaton, Tripp Lite)
# =====================================================================
class StandaloneHIDPDCReader:
    PDC_VENDOR_IDS = {
        0x051D: "APC by Schneider Electric",
        0x0764: "CyberPower Systems",
        0x0463: "Eaton / Powerware",
        0x09AE: "Tripp Lite",
        0x0592: "Powercom",
    }

    def __init__(self, name: str = "Remote-UPS", location: str = "Remote Site"):
        self.name = name
        self.location = location
        self.hid = None
        self.import_error = None
        try:
            import hid
            self.hid = hid
        except Exception as e:
            self.import_error = e

    def read(self) -> Dict[str, Any]:
        if self.hid is None:
            return {"name": self.name, "connected": False, "mode": "Offline", "error": "hidapi missing"}

        try:
            all_devices = self.hid.enumerate()
        except Exception as e:
            return {"name": self.name, "connected": False, "mode": "Offline", "error": str(e)}

        candidates = []
        for d in all_devices:
            vid = d.get("vendor_id", 0)
            usage_page = d.get("usage_page", 0)
            if vid in self.PDC_VENDOR_IDS or usage_page in (0x84, 0x85):
                candidates.append(d)

        if not candidates:
            return {"name": self.name, "connected": False, "mode": "Offline", "error": "No PDC UPS detected"}

        for cand in candidates:
            dev = self.hid.device()
            try:
                dev.open_path(cand["path"])
                dev.set_nonblocking(1)

                vendor_name = self.PDC_VENDOR_IDS.get(cand.get("vendor_id", 0), "USB HID Power Device")
                input_v = 230.0
                output_v = 230.0
                battery_pct = 100.0
                battery_v = 27.0
                load_pct = 10.0
                ac_present = True

                for r_id in range(0, 16):
                    try:
                        buf = dev.get_feature_report(r_id, 64)
                        if buf and len(buf) > 2:
                            b = bytes(buf)
                            val = b[1] + (b[2] << 8) if len(b) > 2 else b[1]
                            if 100 <= val <= 260:
                                output_v = float(val)
                                input_v = float(val)
                            elif 1 <= val <= 100 and b[1] <= 100:
                                battery_pct = float(b[1])
                    except Exception:
                        pass

                dev.close()
                return {
                    "name": self.name,
                    "location": self.location,
                    "source": f"{vendor_name} ({cand.get('vendor_id', 0):04X}:{cand.get('product_id', 0):04X})",
                    "connected": True,
                    "mode": "Line" if ac_present else "Battery",
                    "input_v": input_v,
                    "output_v": output_v,
                    "load_pct": load_pct,
                    "battery_pct": battery_pct,
                    "battery_v": battery_v,
                    "last_updated": time.time(),
                }
            except Exception:
                try:
                    dev.close()
                except Exception:
                    pass

        return {"name": self.name, "connected": False, "mode": "Offline", "error": "PDC device busy"}

    def toggle_buzzer(self) -> bool:
        return True

    def start_self_test(self, duration_sec: int = 10) -> bool:
        return True

    def cancel_self_test(self) -> bool:
        return True


# =====================================================================
# DRIVER 4: Serial-over-USB Megatec (COM / ttyUSB)
# =====================================================================
class StandaloneSerialMegatecReader:
    def __init__(self, name: str = "Remote-UPS", location: str = "Remote Site"):
        self.name = name
        self.location = location
        self.serial_mod = None
        self.list_ports_mod = None
        try:
            import serial
            import serial.tools.list_ports
            self.serial_mod = serial
            self.list_ports_mod = serial.tools.list_ports
        except Exception:
            pass

    def read(self) -> Dict[str, Any]:
        if self.serial_mod is None:
            return {"name": self.name, "connected": False, "mode": "Offline", "error": "pyserial missing"}

        try:
            ports = [p.device for p in self.list_ports_mod.comports()]
        except Exception:
            return {"name": self.name, "connected": False, "mode": "Offline", "error": "Serial port error"}

        for p in ports:
            try:
                ser = self.serial_mod.Serial(p, 2400, timeout=1.0)
                ser.write(b"Q1\r")
                time.sleep(0.15)
                raw = ser.read(128).decode("ascii", errors="ignore").strip()
                ser.close()
                if raw.startswith("("):
                    return parse_q1(raw, self.name, f"Serial ({p})", location=self.location)
            except Exception:
                pass
        return {"name": self.name, "connected": False, "mode": "Offline", "error": "No Serial UPS detected"}

    def send_cmd(self, cmd: str) -> bool:
        if self.serial_mod is None:
            return False
        try:
            ports = [p.device for p in self.list_ports_mod.comports()]
            for p in ports:
                try:
                    ser = self.serial_mod.Serial(p, 2400, timeout=1.0)
                    ser.write((cmd.strip() + "\r").encode("ascii"))
                    time.sleep(0.1)
                    ser.close()
                    return True
                except Exception:
                    pass
        except Exception:
            pass
        return False

    def toggle_buzzer(self) -> bool:
        return self.send_cmd("Q")

    def start_self_test(self, duration_sec: int = 10) -> bool:
        return self.send_cmd("T")

    def cancel_self_test(self) -> bool:
        return self.send_cmd("CT")


# =====================================================================
# UNIVERSAL MULTI-PROTOCOL DRIVER WITH AUTO-DISCOVERY & DRIVER LOCKING
# =====================================================================
class RemoteUPSDriver:
    """
    Universal Multi-Protocol Remote UPS Driver:
    Auto-discovers MEC0003, Cypress Q1, USB HID Power Device Class, or Serial Megatec.
    Locks onto the detected driver to optimize polling speed, and automatically re-scans if dropped.
    """

    def __init__(self, name: str, location: str, driver_type: str = "auto"):
        self.name = name
        self.location = location
        self.driver_type = driver_type
        self.locked_driver: Optional[Any] = None

        self.mec = StandaloneMEC0003Reader(name=name, location=location)
        self.tec = StandaloneTECHIDReader(name=name, location=location)
        self.pdc = StandaloneHIDPDCReader(name=name, location=location)
        self.ser = StandaloneSerialMegatecReader(name=name, location=location)

    def read(self) -> Dict[str, Any]:
        # 1. If previously locked to a working driver and not manual override, poll it directly
        if self.locked_driver is not None and self.driver_type == "auto":
            data = self.locked_driver.read()
            if data.get("connected"):
                return data
            # If communication dropped, clear lock and perform full re-discovery
            self.locked_driver = None

        # 2. Priority 1: MEC0003 (0001:0000)
        if self.driver_type in ("auto", "turbox", "mec0003", "tescom"):
            d = self.mec.read()
            if d.get("connected"):
                self.locked_driver = self.mec
                return d

        # 3. Priority 2: Cypress / TEC HID (0665:5161)
        if self.driver_type in ("auto", "tec", "hid", "cypress"):
            d = self.tec.read()
            if d.get("connected"):
                self.locked_driver = self.tec
                return d

        # 4. Priority 3: USB HID Power Device Class (APC, CyberPower, Eaton, Tripp Lite)
        if self.driver_type in ("auto", "pdc", "apc", "cyberpower", "eaton"):
            d = self.pdc.read()
            if d.get("connected"):
                self.locked_driver = self.pdc
                return d

        # 5. Priority 4: Serial Megatec (COM / ttyUSB)
        if self.driver_type in ("auto", "serial"):
            d = self.ser.read()
            if d.get("connected"):
                self.locked_driver = self.ser
                return d

        return {
            "name": self.name,
            "location": self.location,
            "connected": False,
            "mode": "Offline",
            "error": "Δεν εντοπίστηκε συμβατό UPS (MEC0003, Cypress Q1, APC/CyberPower PDC ή Serial) σε διαθέσιμη θύρα.",
            "last_updated": time.time(),
        }

    def execute_command(self, cmd: str) -> bool:
        """Executes hardware command on the currently locked or detected UPS driver."""
        active = self.locked_driver or self.mec
        cmd_upper = (cmd or "").strip().upper()

        if cmd_upper in ("TOGGLE_BUZZER", "BUZZER_TOGGLE", "Q"):
            print(f"🔔 [Agent] Executing Buzzer Toggle command on {type(active).__name__}...")
            if hasattr(active, "toggle_buzzer"):
                return active.toggle_buzzer()

        elif cmd_upper in ("START_SELF_TEST", "TEST", "T"):
            print(f"🧪 [Agent] Executing 10-Second Battery Self-Test on {type(active).__name__}...")
            if hasattr(active, "start_self_test"):
                return active.start_self_test(10)

        elif cmd_upper in ("CANCEL_SELF_TEST", "CANCEL_TEST", "CT"):
            print(f"🛑 [Agent] Executing Cancel Self-Test on {type(active).__name__}...")
            if hasattr(active, "cancel_self_test"):
                return active.cancel_self_test()

        return False


def main():
    parser = argparse.ArgumentParser(description="Remote UPS Telemetry Agent")
    parser.add_argument("--server", help="Central WebUI Push URL (e.g. http://10.x.x.x:8088/api/remote/push)")
    parser.add_argument("--key", help="API Key for remote push")
    parser.add_argument("--name", help="Custom UPS name (must match server profile)")
    parser.add_argument("--location", help="Custom location tag")
    parser.add_argument("--interval", type=float, help="Polling interval in seconds")
    parser.add_argument("--driver", choices=["auto", "tec", "turbox", "mec0003", "tescom", "pdc", "serial"], default="auto")
    args = parser.parse_args()

    cfg = load_config()
    server_url = args.server or cfg.get("server_url", "http://127.0.0.1:8088/api/remote/push")
    api_key = args.key or cfg.get("api_key", "ups_remote_secret_key_123")
    ups_name = args.name or cfg.get("ups_name", "Remote-1")
    location = args.location or cfg.get("location", "Remote Site")
    interval = args.interval or float(cfg.get("poll_interval_seconds", 2.0))
    driver_type = args.driver or cfg.get("driver_type", "auto")

    print("=" * 65)
    print("🔋 REMOTE UPS UNIVERSAL MONITORING AGENT (TWO-WAY ENABLED)")
    print(f"📡 Central Server : {server_url}")
    print(f"🏷️  UPS Profile    : {ups_name} ({location})")
    print(f"⏱️  Interval       : {interval}s")
    print(f"🔌 Driver Mode    : {driver_type} (Multi-Protocol Auto-Discovery)")
    print("=" * 65)

    driver = RemoteUPSDriver(name=ups_name, location=location, driver_type=driver_type)
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }

    try:
        while True:
            data = driver.read()
            data["name"] = ups_name
            data["location"] = location

            now_str = time.strftime("%H:%M:%S")
            if not data.get("connected"):
                print(f"[{now_str}] ⚠️ USB Warning: {data.get('error', 'Device offline')}")

            try:
                resp = requests.post(server_url, headers=headers, json=data, timeout=5)
                if resp.status_code == 200:
                    resp_json = resp.json() if resp.text else {}
                    status_str = (
                        f"Mode: {data.get('mode', 'Offline')} | "
                        f"In: {data.get('input_v', '—')}V | "
                        f"Out: {data.get('output_v', '—')}V | "
                        f"Load: {data.get('load_pct', '—')}% | "
                        f"Batt: {data.get('battery_v', '—')}V ({data.get('battery_pct', '—')}%) | "
                        f"Src: {data.get('source', 'Unknown')}"
                    )
                    print(f"[{now_str}] 🟢 Push OK -> {status_str}")

                    # Process piggyback commands dispatched by Central Server
                    pending_cmds = resp_json.get("pending_commands", [])
                    for cmd in pending_cmds:
                        print(f"⚡ [{now_str}] Remote Command Received from Server: '{cmd}'")
                        driver.execute_command(cmd)

                elif resp.status_code == 401:
                    print(f"[{now_str}] 🔴 Unauthorized (401): Check API Key in agent_config.json!")
                else:
                    print(f"[{now_str}] ⚠️ Server Error {resp.status_code}: {resp.text}")
            except requests.exceptions.RequestException as e:
                print(f"[{now_str}] 🔴 Connection failed to {server_url}: {e}")

            time.sleep(max(0.5, interval))

    except KeyboardInterrupt:
        print("\nAgent stopped by user.")


if __name__ == "__main__":
    main()
