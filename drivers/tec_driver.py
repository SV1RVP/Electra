from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from drivers.models import UPSData
from drivers.base_driver import parse_q1

logger = logging.getLogger("UPSStatus.Driver.TEC")


class TECQ1Reader:
    """
    TEC UPS Reader:
    USB VID:PID 0665:5161 (Cypress USB-to-serial)
    Protocol: Megatec / Q1 (responds to QS command via 8-byte HID reports).
    """

    VID = 0x0665
    PID = 0x5161

    def __init__(self, name: str = "TEC", location: str = "Local", target_path: Optional[str] = None):
        self.name = name
        self.location = location
        self.target_path = target_path
        self.hid = None
        self.import_error = None
        try:
            import hid
            self.hid = hid
        except Exception as e:
            self.import_error = e

    def enumerate(self) -> List[Dict[str, Any]]:
        if self.hid is None:
            return []
        try:
            return self.hid.enumerate(self.VID, self.PID)
        except Exception:
            return []

    def _open(self, specific_path: Optional[str] = None):
        if self.hid is None:
            raise RuntimeError("hidapi is missing. Install with: py -m pip install hidapi")

        target = specific_path or self.target_path
        if target:
            try:
                d = self.hid.device()
                p = target if isinstance(target, bytes) else target.encode("utf-8")
                d.open_path(p)
                return d, {"path": target}
            except Exception as e:
                logger.debug(f"open_path failed for {target}: {e}, trying standard open({self.VID:04X}:{self.PID:04X})...")

        devices = self.enumerate()
        if not devices:
            # Direct attempt to open default VID/PID
            try:
                d = self.hid.device()
                d.open(self.VID, self.PID)
                return d, {"path": "default"}
            except Exception as e:
                raise RuntimeError(f"TEC USB {self.VID:04X}:{self.PID:04X} not found: {e}")

        last_error = None
        for info in devices:
            try:
                d = self.hid.device()
                path = info.get("path")
                if path:
                    d.open_path(path)
                else:
                    d.open(self.VID, self.PID)
                return d, info
            except Exception as e:
                last_error = e

        raise RuntimeError(f"Could not open TEC HID device: {last_error}")

    @staticmethod
    def _clean_chunk(chunk) -> bytes:
        b = bytes(chunk)
        if len(b) > 1 and b[0] == 0 and any(b[1:]):
            b = b[1:]
        return b

    def command(self, command: str, timeout_ms: int = 1200, target_path: Optional[str] = None) -> str:
        d, _info = self._open(specific_path=target_path)
        try:
            try:
                d.set_nonblocking(1)
                for _ in range(8):
                    old = d.read(64)
                    if not old:
                        break
            except Exception:
                pass
            finally:
                try:
                    d.set_nonblocking(0)
                except Exception:
                    pass

            cmd = command.encode("ascii")
            if not cmd.endswith(b"\r"):
                cmd += b"\r"

            for offset in range(0, len(cmd), 8):
                chunk = cmd[offset : offset + 8]
                payload = [0x00] + list(chunk)
                if len(payload) < 9:
                    payload += [0x00] * (9 - len(payload))
                d.write(payload)
                time.sleep(0.05)

            chunks: List[bytes] = []
            deadline = time.time() + (timeout_ms / 1000.0)

            while time.time() < deadline:
                raw = d.read(64, timeout_ms=250)
                if not raw:
                    continue
                c = self._clean_chunk(raw)
                if c:
                    chunks.append(c)
                    combined = b"".join(chunks)
                    
                    # Check if buffer is merely echoing the sent command (e.g. Q1, QS, D, I, F)
                    clean_cmd_echo = combined.strip(b"\r\n\x00 ")
                    if clean_cmd_echo in (b"Q1", b"QS", b"D", b"I", b"F", b"M"):
                        # Discard echo or continue reading for actual '(' response
                        continue

                    # If we have '(' and a terminator \r or \n, or response is long enough
                    if b"(" in combined and (b"\r" in combined or b"\n" in combined):
                        break
                    elif (b"\r" in combined or b"\n" in combined) and len(combined) > 15:
                        break

            reply = b"".join(chunks).decode("latin1", errors="ignore").strip("\r\n\x00 ")
            # If reply contains echo prefix followed by telemetry payload (e.g. "Q1\r(230.0..."), extract '('
            if "(" in reply:
                reply = reply[reply.find("(") :]
            return reply
        finally:
            try:
                d.close()
            except Exception:
                pass

    def probe_path(self, path: str) -> Optional[UPSData]:
        """Probes a specific physical HID path."""
        for cmd in ("QS", "Q1", "D"):
            for attempt in range(2):
                try:
                    raw = self.command(cmd, target_path=path, timeout_ms=1000)
                    cleaned = raw.strip().replace("\x00", "")
                    if "(" in cleaned:
                        payload = cleaned[cleaned.find("(") :]
                        return parse_q1(
                            payload, self.name, f"Cypress Q1 ({self.VID:04X}:{self.PID:04X} / {cmd})", location=self.location
                        )
                except Exception:
                    continue
        return None

    def read(self, specific_path: Optional[str] = None) -> UPSData:
        if self.import_error is not None:
            return UPSData(
                name=self.name,
                source="TEC direct USB",
                connected=False,
                mode="Offline",
                error="hidapi is missing. Run: py -m pip install hidapi",
                location=self.location,
            )

        errors = []
        target = specific_path or self.target_path
        for cmd in ("QS", "Q1", "D"):
            for attempt in range(2):  # 2 attempts per command
                try:
                    raw = self.command(cmd, target_path=target, timeout_ms=1200)
                    cleaned = raw.strip().replace("\x00", "")
                    if "(" in cleaned:
                        payload = cleaned[cleaned.find("(") :]
                        return parse_q1(
                            payload, self.name, f"Cypress Q1 ({self.VID:04X}:{self.PID:04X} / {cmd})", location=self.location
                        )
                    if raw and attempt == 0:
                        time.sleep(0.06)
                        continue
                    errors.append(f"{cmd}: {raw!r}")
                except Exception as e:
                    if attempt == 0:
                        time.sleep(0.06)
                        continue
                    errors.append(f"{cmd}: {type(e).__name__}: {e}")

        return UPSData(
            name=self.name,
            source=f"Cypress Q1 ({self.VID:04X}:{self.PID:04X})",
            connected=False,
            mode="Offline",
            error="No telemetry reply. " + " | ".join(errors),
            location=self.location,
        )

    def toggle_buzzer(self, target_path: Optional[str] = None) -> bool:
        """Sends Megatec 'Q' command to toggle alarm beeper/buzzer on/off."""
        try:
            target = target_path or self.target_path
            d, _info = self._open(specific_path=target)
            try:
                payload = [0x00, 0x51, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # Q\r
                try:
                    d.write(payload)
                except Exception:
                    d.send_feature_report(payload)
                return True
            finally:
                try:
                    d.close()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to toggle buzzer on TEC UPS: {e}")
            return False

    def start_self_test(self, duration_sec: int = 10, target_path: Optional[str] = None) -> bool:
        """Sends Megatec 'T' command to trigger battery self-test safely."""
        try:
            target = target_path or self.target_path
            d, _info = self._open(specific_path=target)
            try:
                # Standard Megatec 10-second test: 'T\r'
                payload_t = [0x00, 0x54, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]  # T\r
                try:
                    d.write(payload_t)
                except Exception:
                    d.send_feature_report(payload_t)
                return True
            finally:
                try:
                    d.close()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to initiate self-test on TEC UPS: {e}")
            return False

    def cancel_self_test(self, target_path: Optional[str] = None) -> bool:
        """Sends Megatec 'CT' command to cancel an ongoing battery self-test."""
        try:
            target = target_path or self.target_path
            d, _info = self._open(specific_path=target)
            try:
                payload = [0x00, 0x43, 0x54, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00]  # CT\r
                try:
                    d.write(payload)
                except Exception:
                    d.send_feature_report(payload)
                return True
            finally:
                try:
                    d.close()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to cancel self-test on TEC UPS: {e}")
            return False
