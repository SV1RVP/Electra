from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from drivers.hid_pdc_driver import HIDPowerDeviceClassReader, PDC_VENDOR_IDS
from drivers.models import UPSData
from drivers.serial_driver import SerialMegatecReader
from drivers.tec_driver import TECQ1Reader
from drivers.turbox_driver import TurboXMEC0003Reader

logger = logging.getLogger("UPSStatus.DeviceManager")


class USBDeviceManager:
    """
    Universal USB UPS Discovery, Collision Prevention & Persistent Binding Manager:
    - Scans all physical USB HID, USB Raw, and Serial endpoints.
    - Probes for supported protocols (Cypress Q1, MEC0003, USB HID PDC, Serial Megatec).
    - Persistent Port Binding: Locks slots to designated physical hardware paths.
    - Prevents multi-port collision: ensures multiple UPS units (even identical models)
      are uniquely bound to distinct physical hardware ports.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Maps physical_id -> slot_name (e.g. "hid:\\?\HID#VID_0665&PID_5161#..." -> "Local-1")
        self.claimed_devices: Dict[str, str] = {}
        # Maps slot_name -> (driver_instance, physical_id, driver_type, consecutive_errors)
        self.active_slots: Dict[str, Dict[str, Any]] = {}

    def release_slot(self, slot_name: str):
        """Releases any hardware device claimed by the specified slot."""
        with self._lock:
            if slot_name in self.active_slots:
                dev_id = self.active_slots[slot_name].get("dev_id")
                if dev_id and dev_id in self.claimed_devices:
                    del self.claimed_devices[dev_id]
                del self.active_slots[slot_name]
                logger.info(f"Released device claim for slot '{slot_name}' ({dev_id})")

    def release_all(self):
        """Releases all active slots and device claims."""
        with self._lock:
            self.claimed_devices.clear()
            self.active_slots.clear()
            logger.info("Released all active slots and device claims for re-scan.")

    def get_driver_for_slot(self, slot_name: str) -> Optional[Any]:
        """Returns active driver instance for slot if present, with alias resolution."""
        if not slot_name:
            return None
        with self._lock:
            if slot_name in self.active_slots:
                return self.active_slots[slot_name].get("driver")
            # Try fuzzy/alias matching
            s_clean = slot_name.lower().replace("-", "").replace("_", "").replace(" ", "")
            for k, info in self.active_slots.items():
                k_clean = k.lower().replace("-", "").replace("_", "").replace(" ", "")
                if k_clean in s_clean or s_clean in k_clean:
                    return info.get("driver")
                if ("1" in s_clean or "tec" in s_clean or "primary" in s_clean) and "1" in k:
                    return info.get("driver")
                if ("2" in s_clean or "turbo" in s_clean or "secondary" in s_clean) and "2" in k:
                    return info.get("driver")
        return None

    def toggle_buzzer(self, slot_name: str) -> Dict[str, Any]:
        """Toggles buzzer / beeper alarm on designated slot."""
        driver = self.get_driver_for_slot(slot_name)
        if not driver:
            return {"success": False, "error": f"No active driver for slot '{slot_name}'"}
        try:
            if hasattr(driver, "toggle_buzzer"):
                ok = driver.toggle_buzzer()
                return {"success": ok, "message": "Buzzer toggled successfully" if ok else "Buzzer command failed"}
            return {"success": False, "error": "Driver does not support buzzer toggle"}
        except Exception as e:
            logger.error(f"Error toggling buzzer for {slot_name}: {e}")
            return {"success": False, "error": str(e)}

    def start_self_test(self, slot_name: str, duration_sec: int = 10) -> Dict[str, Any]:
        """Triggers battery self-test on designated slot."""
        driver = self.get_driver_for_slot(slot_name)
        if not driver:
            return {"success": False, "error": f"No active driver for slot '{slot_name}'"}
        try:
            if hasattr(driver, "start_self_test"):
                ok = driver.start_self_test(duration_sec=duration_sec)
                return {"success": ok, "message": "Self-test started" if ok else "Failed to start self-test"}
            return {"success": False, "error": "Driver does not support self-test command"}
        except Exception as e:
            logger.error(f"Error starting self-test for {slot_name}: {e}")
            return {"success": False, "error": str(e)}

    def cancel_self_test(self, slot_name: str) -> Dict[str, Any]:
        """Cancels an ongoing battery self-test on designated slot."""
        driver = self.get_driver_for_slot(slot_name)
        if not driver:
            return {"success": False, "error": f"No active driver for slot '{slot_name}'"}
        try:
            if hasattr(driver, "cancel_self_test"):
                ok = driver.cancel_self_test()
                return {"success": ok, "message": "Self-test canceled" if ok else "Failed to cancel self-test"}
            return {"success": False, "error": "Driver does not support cancel self-test"}
        except Exception as e:
            logger.error(f"Error canceling self-test for {slot_name}: {e}")
            return {"success": False, "error": str(e)}

    def create_driver_for_binding(
        self,
        driver_type: str,
        dev_id: str,
        display_name: str,
        location: str,
    ) -> Optional[Any]:
        """Instantiates the appropriate driver given a saved driver_type and physical dev_id."""
        try:
            if driver_type == "CypressQ1":
                target_path = dev_id.replace("hid:", "")
                return TECQ1Reader(name=display_name, location=location, target_path=target_path)

            elif driver_type == "HID_PDC":
                target_path = dev_id.replace("hid:", "")
                return HIDPowerDeviceClassReader(name=display_name, location=location, target_path=target_path)

            elif driver_type == "MEC0003":
                # dev_id format: usb:BUS:ADDRESS
                parts = dev_id.replace("usb:", "").split(":")
                if len(parts) == 2:
                    bus, addr = int(parts[0]), int(parts[1])
                    return TurboXMEC0003Reader(name=display_name, location=location, target_bus=bus, target_address=addr)
                return TurboXMEC0003Reader(name=display_name, location=location)

            elif driver_type == "SerialQ1":
                port = dev_id.replace("serial:", "")
                return SerialMegatecReader(port=port, name=display_name, location=location)

        except Exception as e:
            logger.error(f"Failed to create driver for {driver_type} on {dev_id}: {e}")
        return None

    def poll_slot(
        self,
        slot_name: str,
        display_name: str = "",
        location: str = "Local",
        bound_device_id: str = "",
        bound_driver_type: str = "",
        on_new_binding: Optional[Callable[[str, str, str], None]] = None,
    ) -> UPSData:
        """
        Polls the hardware device assigned to a slot.
        - If bound_device_id is configured in profile, polling is locked strictly to that hardware path.
        - If bound_device_id is empty, auto-discovery runs once and saves the detected hardware binding.
        """
        disp_name = display_name or slot_name

        # -------------------------------------------------------------
        # 1. Slot has a Locked / Saved Hardware Binding
        # -------------------------------------------------------------
        if bound_device_id and bound_driver_type:
            with self._lock:
                slot_info = self.active_slots.get(slot_name)

                # Check if currently active driver matches the bound hardware
                if not slot_info or slot_info.get("dev_id") != bound_device_id:
                    driver = self.create_driver_for_binding(bound_driver_type, bound_device_id, disp_name, location)
                    if driver:
                        self.claimed_devices[bound_device_id] = slot_name
                        slot_info = {
                            "driver": driver,
                            "dev_id": bound_device_id,
                            "driver_type": bound_driver_type,
                            "errors": 0,
                            "bound_at": time.time(),
                        }
                        self.active_slots[slot_name] = slot_info

            if slot_info and slot_info.get("driver"):
                try:
                    data = slot_info["driver"].read()
                    data.name = disp_name
                    data.location = location
                    if data.connected:
                        slot_info["errors"] = 0
                        return data
                    else:
                        slot_info["errors"] = slot_info.get("errors", 0) + 1
                        return data
                except Exception as e:
                    logger.debug(f"Poll error on locked slot '{slot_name}' ({bound_device_id}): {e}")
                    slot_info["errors"] = slot_info.get("errors", 0) + 1

            return UPSData(
                name=disp_name,
                source=f"Locked ({bound_driver_type})",
                connected=False,
                mode="Offline",
                error=f"Το UPS στην καθορισμένη θύρα δεν αποκρίνεται ({bound_device_id}).",
                location=location,
            )

        # -------------------------------------------------------------
        # 2. Slot is Unbound: Auto-Discovery & Auto-Lock
        # -------------------------------------------------------------
        with self._lock:
            slot_info = self.active_slots.get(slot_name)

        if slot_info and slot_info.get("driver"):
            try:
                data = slot_info["driver"].read()
                data.name = disp_name
                data.location = location
                if data.connected:
                    slot_info["errors"] = 0
                    return data
                else:
                    slot_info["errors"] = slot_info.get("errors", 0) + 1
            except Exception as e:
                logger.debug(f"Read error on slot '{slot_name}': {e}")
                slot_info["errors"] = slot_info.get("errors", 0) + 1

            if slot_info["errors"] >= 3:
                logger.warning(f"Slot '{slot_name}' failed 3 consecutive polls. Releasing for auto-rescan.")
                self.release_slot(slot_name)

        # Run Auto-Discovery and persist binding
        data = self._auto_discover_and_bind(slot_name, disp_name, location)
        if data.connected and on_new_binding:
            with self._lock:
                active_info = self.active_slots.get(slot_name)
                if active_info:
                    dev_id = active_info.get("dev_id", "")
                    driver_type = active_info.get("driver_type", "")
                    if dev_id and driver_type:
                        try:
                            on_new_binding(slot_name, dev_id, driver_type)
                        except Exception as e:
                            logger.error(f"Failed to persist new binding for {slot_name}: {e}")

        return data

    def rescan_all(
        self,
        profiles_dict: Dict[str, Dict[str, Any]],
        save_callback: Optional[Callable[[Dict[str, Dict[str, Any]]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Forces a full hardware re-scan across all physical USB and Serial ports.
        Updates and persists the detected hardware bindings in profiles.json.
        """
        logger.info("Executing full manual USB hardware re-scan...")
        self.release_all()

        results: Dict[str, Any] = {}
        claimed_ids: Set[str] = set()

        for slot_name in ["Local-1", "Local-2"]:
            prof = profiles_dict.get(slot_name, {})
            if not prof.get("enabled", True):
                continue

            disp_name = prof.get("display_name", slot_name)
            location = prof.get("location", "Local")

            # 1. Probe HID Candidates
            data, dev_id, driver_type = self._probe_hid(slot_name, disp_name, location, claimed_ids)
            
            # 2. Probe PyUSB Candidates if not found
            if not data:
                data, dev_id, driver_type = self._probe_pyusb(slot_name, disp_name, location, claimed_ids)

            # 3. Probe Serial Candidates if not found
            if not data:
                data, dev_id, driver_type = self._probe_serial(slot_name, disp_name, location, claimed_ids)

            if data and dev_id:
                claimed_ids.add(dev_id)
                prof["device_id"] = dev_id
                prof["driver_type"] = driver_type
                results[slot_name] = {
                    "found": True,
                    "device_id": dev_id,
                    "driver_type": driver_type,
                    "protocol": data.source,
                    "connected": data.connected,
                }
                logger.info(f"Re-Scan bound '{slot_name}' -> {driver_type} ({dev_id})")
            else:
                prof["device_id"] = ""
                prof["driver_type"] = ""
                results[slot_name] = {
                    "found": False,
                    "device_id": "",
                    "driver_type": "",
                    "connected": False,
                }
                logger.info(f"Re-Scan: No available hardware found for '{slot_name}'")

        if save_callback:
            try:
                save_callback(profiles_dict)
                logger.info("Successfully persisted new hardware bindings to profiles.json")
            except Exception as e:
                logger.error(f"Error saving profiles during re-scan: {e}")

        return results

    def _auto_discover_and_bind(self, slot_name: str, display_name: str, location: str) -> UPSData:
        """Scans unclaimed physical USB / Serial devices and binds the first working candidate."""
        with self._lock:
            claimed_ids = set(self.claimed_devices.keys())

        # 1. Probe HID Devices
        data, dev_id, driver_type = self._probe_hid(slot_name, display_name, location, claimed_ids)
        if data:
            return data

        # 2. Probe PyUSB Devices
        data, dev_id, driver_type = self._probe_pyusb(slot_name, display_name, location, claimed_ids)
        if data:
            return data

        # 3. Probe Serial COM ports
        data, dev_id, driver_type = self._probe_serial(slot_name, display_name, location, claimed_ids)
        if data:
            return data

        return UPSData(
            name=display_name or slot_name,
            source="Auto-Scan",
            connected=False,
            mode="Offline",
            error="Δεν εντοπίστηκε συμβατό συνδεδεμένο UPS σε διαθέσιμη θύρα USB/Serial.",
            location=location,
        )

    def _probe_hid(
        self, slot_name: str, display_name: str, location: str, claimed_ids: Set[str]
    ) -> Tuple[Optional[UPSData], str, str]:
        """Probes all unclaimed USB HID candidates."""
        try:
            import hid
            all_hid = hid.enumerate()
        except Exception:
            return None, "", ""

        for info in all_hid:
            raw_path = info.get("path")
            if not raw_path:
                continue
            path_str = raw_path.decode("utf-8", errors="ignore") if isinstance(raw_path, bytes) else str(raw_path)
            dev_id = f"hid:{path_str}"

            if dev_id in claimed_ids:
                continue

            vid = info.get("vendor_id", 0)
            pid = info.get("product_id", 0)

            # Case A: Cypress Q1 (0665:5161)
            if vid == 0x0665 and pid == 0x5161:
                reader = TECQ1Reader(name=display_name or slot_name, location=location, target_path=path_str)
                data = reader.read(specific_path=path_str)
                if data.connected:
                    self._bind_slot(slot_name, reader, dev_id, "CypressQ1")
                    logger.info(f"Slot '{slot_name}' claimed Cypress Q1 UPS on {dev_id}")
                    return data, dev_id, "CypressQ1"

            # Case B: USB Power Device Class (APC, CyberPower, Eaton, Tripp Lite)
            usage_page = info.get("usage_page", 0)
            if vid in PDC_VENDOR_IDS or usage_page in (0x84, 0x85):
                pdc_reader = HIDPowerDeviceClassReader(
                    name=display_name or slot_name, location=location, target_path=path_str
                )
                data = pdc_reader.read()
                if data.connected:
                    self._bind_slot(slot_name, pdc_reader, dev_id, "HID_PDC")
                    logger.info(f"Slot '{slot_name}' claimed HID Power Device Class UPS on {dev_id}")
                    return data, dev_id, "HID_PDC"

        return None, "", ""

    def _probe_pyusb(
        self, slot_name: str, display_name: str, location: str, claimed_ids: Set[str]
    ) -> Tuple[Optional[UPSData], str, str]:
        """Probes all unclaimed PyUSB / MEC0003 candidates."""
        try:
            tx_probe = TurboXMEC0003Reader(name=display_name or slot_name, location=location)
            candidates = tx_probe.enumerate_candidates()
        except Exception:
            return None, "", ""

        for dev in candidates:
            dev_id = f"usb:{dev.bus}:{dev.address}"
            if dev_id in claimed_ids:
                continue

            data = tx_probe.probe_device(dev)
            if data and data.connected:
                reader = TurboXMEC0003Reader(
                    name=display_name or slot_name,
                    location=location,
                    target_bus=dev.bus,
                    target_address=dev.address,
                )
                self._bind_slot(slot_name, reader, dev_id, "MEC0003")
                logger.info(f"Slot '{slot_name}' claimed MEC0003 UPS on {dev_id}")
                return data, dev_id, "MEC0003"

        return None, "", ""

    def _probe_serial(
        self, slot_name: str, display_name: str, location: str, claimed_ids: Set[str]
    ) -> Tuple[Optional[UPSData], str, str]:
        """Probes all unclaimed serial / virtual COM ports."""
        try:
            ser_probe = SerialMegatecReader(name=display_name or slot_name, location=location)
            ports = ser_probe.enumerate_candidates()
        except Exception:
            return None, "", ""

        for p in ports:
            dev_id = f"serial:{p}"
            if dev_id in claimed_ids:
                continue

            data = ser_probe.probe(p)
            if data and data.connected:
                reader = SerialMegatecReader(port=p, name=display_name or slot_name, location=location)
                self._bind_slot(slot_name, reader, dev_id, "SerialQ1")
                logger.info(f"Slot '{slot_name}' claimed Serial Megatec UPS on {dev_id}")
                return data, dev_id, "SerialQ1"

        return None, "", ""

    def _bind_slot(self, slot_name: str, driver: Any, dev_id: str, driver_type: str = "Auto"):
        """Binds a slot to a unique physical device identifier."""
        with self._lock:
            self.claimed_devices[dev_id] = slot_name
            self.active_slots[slot_name] = {
                "driver": driver,
                "dev_id": dev_id,
                "driver_type": driver_type,
                "errors": 0,
                "bound_at": time.time(),
            }


# Singleton global manager instance
device_manager = USBDeviceManager()
