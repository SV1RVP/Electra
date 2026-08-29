from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from drivers.base_driver import parse_q1
from drivers.models import UPSData

logger = logging.getLogger("UPSStatus.Driver.Serial")


class SerialMegatecReader:
    """
    Serial-over-USB Megatec Q1 Reader:
    Queries serial ports (virtual COM / ttyUSB / ttyACM / FTDI / CH340 / CP2102)
    using the standard Megatec Q1 protocol at 2400 / 9600 baud.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 2400,
        name: str = "Serial-UPS",
        location: str = "Local (Serial)",
    ):
        self.port = port
        self.baudrate = baudrate
        self.name = name
        self.location = location
        self.serial_mod = None
        self.import_error = None

        try:
            import serial
            import serial.tools.list_ports

            self.serial_mod = serial
            self.list_ports_mod = serial.tools.list_ports
        except Exception as e:
            self.import_error = e

    def enumerate_candidates(self) -> List[str]:
        """Returns list of available serial port device names."""
        if self.serial_mod is None:
            return []
        try:
            ports = self.list_ports_mod.comports()
            return [p.device for p in ports]
        except Exception as e:
            logger.debug(f"Serial port enumeration error: {e}")
            return []

    def probe(self, port_name: Optional[str] = None) -> Optional[UPSData]:
        """Probes a specific serial port with Megatec Q1 query."""
        if self.serial_mod is None:
            return None

        target = port_name or self.port
        if not target:
            return None

        for baud in (self.baudrate, 2400, 9600):
            ser = None
            try:
                ser = self.serial_mod.Serial(
                    port=target,
                    baudrate=baud,
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                    timeout=1.2,
                    write_timeout=1.2,
                )
                # Flush existing buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # Send Q1 query
                ser.write(b"Q1\r")
                time.sleep(0.15)
                raw_bytes = ser.read(128)
                ser.close()

                if raw_bytes and b"(" in raw_bytes:
                    text = raw_bytes.decode("ascii", errors="ignore").strip()
                    if text.startswith("("):
                        return parse_q1(text, self.name, f"Serial ({target} @ {baud})", self.location)
            except Exception as e:
                logger.debug(f"Serial probe failed on {target} @ {baud}: {e}")
                if ser:
                    try:
                        ser.close()
                    except Exception:
                        pass
        return None

    def read(self) -> UPSData:
        if self.import_error is not None:
            return UPSData(
                name=self.name,
                source="Serial Megatec",
                connected=False,
                mode="Offline",
                error="pyserial not installed",
                location=self.location,
            )

        if not self.port:
            return UPSData(
                name=self.name,
                source="Serial Megatec",
                connected=False,
                mode="Offline",
                error="No COM port assigned",
                location=self.location,
            )

        data = self.probe(self.port)
        if data is None:
            return UPSData(
                name=self.name,
                source=f"Serial ({self.port})",
                connected=False,
                mode="Offline",
                error="No response from UPS on serial port",
                location=self.location,
            )
        return data

    def send_command(self, cmd: str) -> str:
        """Sends raw command string to serial UPS."""
        if self.serial_mod is None or not self.port:
            return ""
        try:
            ser = self.serial_mod.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=1.0,
                write_timeout=1.0,
            )
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            payload = cmd.encode("ascii")
            if not payload.endswith(b"\r"):
                payload += b"\r"
            ser.write(payload)
            time.sleep(0.15)
            reply = ser.read(64).decode("latin1", errors="ignore").strip()
            ser.close()
            return reply
        except Exception as e:
            logger.error(f"Serial command '{cmd}' failed on {self.port}: {e}")
            return ""

    def toggle_buzzer(self) -> bool:
        """Toggles serial UPS buzzer ON/OFF via 'Q' command."""
        res = self.send_command("Q")
        return True

    def start_self_test(self, duration_sec: int = 10) -> bool:
        """Triggers battery self-test via 'T' command."""
        cmd = "T" if duration_sec <= 10 else f"T{max(1, duration_sec // 60)}"
        self.send_command(cmd)
        return True

    def cancel_self_test(self) -> bool:
        """Cancels battery self-test via 'CT' command."""
        self.send_command("CT")
        return True
