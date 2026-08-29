from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from drivers.models import UPSData
from drivers.base_driver import parse_q1

logger = logging.getLogger("UPSStatus.Driver.TurboX")


class TurboXMEC0003Reader:
    """
    Turbo-X / Tescom / Mustek / PowerWalker UPS Reader:
    USB VID:PID 0001:0000 (MEC0003)
    Protocol: Telemetry retrieved via USB string descriptor 3.
    """

    VID = 0x0001
    PID = 0x0000

    def __init__(
        self,
        name: str = "Turbo-X",
        location: str = "Local",
        target_bus: Optional[int] = None,
        target_address: Optional[int] = None,
    ):
        self.name = name
        self.location = location
        self.target_bus = target_bus
        self.target_address = target_address
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

    def enumerate_candidates(self) -> List[Any]:
        """Enumerates connected USB devices matching VID 0001:0000."""
        if self.usb_core is None:
            return []
        try:
            kwargs: Dict[str, Any] = {"idVendor": self.VID, "idProduct": self.PID, "find_all": True}
            if self.backend is not None:
                kwargs["backend"] = self.backend
            devs = list(self.usb_core.find(**kwargs))
            return devs
        except Exception as e:
            logger.debug(f"Turbo-X enumeration error: {e}")
            return []

    def _find(self, target_bus: Optional[int] = None, target_address: Optional[int] = None):
        if self.usb_core is None:
            return None
        bus = target_bus if target_bus is not None else self.target_bus
        addr = target_address if target_address is not None else self.target_address

        devs = self.enumerate_candidates()
        if not devs:
            return None

        if bus is not None and addr is not None:
            for d in devs:
                if d.bus == bus and d.address == addr:
                    return d

        return devs[0] if devs else None

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
                ret = dev.ctrl_transfer(0x80, 0x06, 0x0300 | index, lang, 255, timeout=1500)
                text = self._decode_string_descriptor(ret)
                if text:
                    return text
            except Exception as e:
                last = e
        if last:
            raise last
        return None

    def probe_device(self, dev) -> Optional[UPSData]:
        """Probes a specific PyUSB device for MEC0003 telemetry."""
        for idx in (3, 2, 4, 1):
            try:
                raw = self._get_string(dev, idx)
                if raw and raw.startswith("("):
                    bus_info = f"Bus {dev.bus} Addr {dev.address}"
                    return parse_q1(raw, self.name, f"MEC0003 ({self.VID:04X}:{self.PID:04X} @ {bus_info})", location=self.location)
            except Exception:
                continue
        return None

    def read(self, specific_bus: Optional[int] = None, specific_addr: Optional[int] = None) -> UPSData:
        if self.import_error is not None:
            return UPSData(
                name=self.name,
                source="Turbo-X direct USB",
                connected=False,
                mode="Offline",
                error="pyusb/libusb missing",
                location=self.location,
            )

        dev = self._find(target_bus=specific_bus, target_address=specific_addr)
        if dev is None:
            return UPSData(
                name=self.name,
                source=f"Turbo-X direct USB ({self.VID:04X}:{self.PID:04X})",
                connected=False,
                mode="Offline",
                error=f"Device {self.VID:04X}:{self.PID:04X} not detected",
                location=self.location,
            )

        data = self.probe_device(dev)
        if data is not None:
            return data

        return UPSData(
            name=self.name,
            source=f"Turbo-X direct USB ({self.VID:04X}:{self.PID:04X})",
            connected=False,
            mode="Offline",
            error="Device connected but no telemetry string descriptor returned",
            location=self.location,
        )

    def send_command(self, cmd: str) -> bool:
        """Sends command to Turbo-X / MEC0003 using GET_DESCRIPTOR index dispatch safely."""
        dev = self._find()
        if dev is None:
            logger.warning("Turbo-X device not found for sending command")
            return False

        cmd_clean = cmd.strip("\r\n ")
        first_char = cmd_clean[0].upper() if cmd_clean else ""
        first_char_code = ord(first_char) if first_char else 0

        # Safe GET_DESCRIPTOR index dispatch
        if first_char_code > 0:
            for lang in (0x0409, 0x0000):
                try:
                    dev.ctrl_transfer(0x80, 0x06, 0x0300 | first_char_code, lang, 255, timeout=800)
                except Exception:
                    pass

        return True

    def toggle_buzzer(self) -> bool:
        """
        Toggles Turbo-X / MEC0003 audible alarm buzzer on/off.
        Protocol: GET_DESCRIPTOR on String Index 7 (following wakeup polling on index 3).
        """
        dev = self._find()
        if dev is None:
            logger.warning("Turbo-X device not found for toggling buzzer")
            return False

        try:
            # Wakeup / flush device state via telemetry descriptor 3
            for _ in range(3):
                try:
                    self._get_string(dev, 3)
                except Exception:
                    pass
            time.sleep(0.2)

            # Trigger buzzer toggle using String Descriptor 7
            self._get_string(dev, 7)
            logger.info("Turbo-X buzzer toggle command sent (Descriptor 7)")
            return True
        except Exception as e:
            logger.warning(f"Turbo-X buzzer toggle via descriptor 7 failed: {e}. Falling back to standard send_command('Q')")
            return self.send_command("Q")

    def start_self_test(self, duration_sec: int = 10) -> bool:
        """
        Safely triggers 10s battery self-test on Turbo-X / MEC0003 via Descriptor 4.
        Never uses raw USB OUT endpoint writes which cause emergency shutdowns.
        """
        dev = self._find()
        if dev is None:
            logger.warning("Turbo-X device not found for starting self-test")
            return False

        try:
            # Wakeup / flush telemetry first
            for _ in range(2):
                try:
                    self._get_string(dev, 3)
                except Exception:
                    pass
            time.sleep(0.15)

            # Descriptor 4 triggers standard 10s battery test on MEC0003
            self._get_string(dev, 4)
            logger.info("Turbo-X battery self-test started (Descriptor 4)")
            return True
        except Exception as e:
            logger.warning(f"Turbo-X start_self_test failed: {e}")
            return False

    def cancel_self_test(self) -> bool:
        """Safely cancels self-test on Turbo-X / MEC0003 via Descriptor 5/6."""
        dev = self._find()
        if dev is None:
            return False
        try:
            self._get_string(dev, 5)
            logger.info("Turbo-X battery self-test cancelled (Descriptor 5)")
            return True
        except Exception as e:
            logger.warning(f"Turbo-X cancel_self_test failed: {e}")
            return False
