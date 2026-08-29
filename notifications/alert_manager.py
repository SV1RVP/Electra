from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from database.db_manager import DBManager
from drivers.models import UPSData, UPSEvent
from notifications.viber_service import ViberService

logger = logging.getLogger("UPSStatus.Alerts")


def _format_duration(seconds: float, lang: str = "el") -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s} δευτερόλεπτα" if lang == "el" else f"{s} seconds"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}λ {s}δ" if lang == "el" else f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}ω {m:02d}λ {s:02d}δ" if lang == "el" else f"{h}h {m:02d}m {s:02d}s"


def _fmt_runtime(minutes: Optional[float], lang: str = "el") -> str:
    if minutes is None or minutes < 0:
        return "—"
    if minutes >= 600:
        return "> 10 ώρες" if lang == "el" else "> 10 hours"
    total = int(round(minutes))
    if total < 60:
        return f"{total} λεπτά" if lang == "el" else f"{total} min"
    h, m = divmod(total, 60)
    return f"{h}ω {m:02d}λ" if lang == "el" else f"{h}h {m:02d}m"


def _fmt_timestamp(ts: Optional[float] = None, lang: str = "el") -> str:
    if ts is None:
        ts = time.time()
    st = time.localtime(ts)
    if lang == "el":
        return time.strftime("%d/%m/%Y %H:%M:%S", st)
    return time.strftime("%Y-%m-%d %H:%M:%S", st)


def _translate_error(err_str: Optional[str], lang: str = "el") -> str:
    if not err_str:
        return "Αποσυνδεδεμένο" if lang == "el" else "Disconnected"

    err_lower = err_str.lower()
    if "δεν εντοπίστηκε συμβατό" in err_lower or "no compatible" in err_lower:
        return (
            "Δεν εντοπίστηκε συμβατό συνδεδεμένο UPS σε διαθέσιμη θύρα USB/Serial."
            if lang == "el"
            else "No compatible connected UPS detected on available USB/Serial ports."
        )
    if "δεν αποκρίνεται" in err_lower or "not responding" in err_lower:
        return (
            "Το UPS στην καθορισμένη θύρα δεν αποκρίνεται."
            if lang == "el"
            else "The UPS on configured port is not responding."
        )
    if "αποσυνδέθηκε" in err_lower or "disconnected" in err_lower:
        return (
            "Το UPS αποσυνδέθηκε από την καθορισμένη θύρα."
            if lang == "el"
            else "UPS disconnected from configured port."
        )
    if "timeout" in err_lower:
        return "Λήξη χρονικού ορίου επικοινωνίας (Timeout)" if lang == "el" else "Communication timeout"

    return err_str


class AlertManager:
    """
    State-machine based Alert & Notification Manager.
    Detects power outages, recoveries, overloads, disconnects, low battery,
    and runs scheduled daily reports with full Greek & English localization.
    """

    def __init__(
        self,
        db: DBManager,
        viber: ViberService,
        config: Dict[str, Any],
        on_event_callback: Optional[Callable[[UPSEvent], None]] = None,
    ):
        self.db = db
        self.viber = viber
        self.config = config
        self.on_event_callback = on_event_callback

        # State tracking per UPS
        self.states: Dict[str, Dict[str, Any]] = {}
        self.last_daily_report_date: Optional[str] = None

    def update_config(self, config: Dict[str, Any]):
        self.config = config

    def _get_lang(self) -> str:
        # Check top-level or ui_settings language
        return self.config.get("language") or self.config.get("ui_settings", {}).get("language", "el")

    def _get_state(self, ups_name: str) -> Dict[str, Any]:
        if ups_name not in self.states:
            self.states[ups_name] = {
                "last_mode": None,
                "last_connected": None,
                "consecutive_failures": 0,
                "outage_start_time": None,
                "last_outage_repeat_alert": 0.0,
                "overload_active": False,
                "last_overload_alert": 0.0,
                "last_battery_low_alert": 0.0,
                "last_disconnect_alert": 0.0,
            }
        return self.states[ups_name]

    def _trigger_event(self, event: UPSEvent, send_viber: bool = True):
        # 1. Log to DB
        self.db.log_event(event)

        # 2. Call UI stream callback if present
        if self.on_event_callback:
            try:
                self.on_event_callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

        # 3. Send to Viber if enabled
        if send_viber and self.config.get("viber_enabled", True):
            success, err = self.viber.send_message(event.message)
            if not success and err:
                logger.warning(f"Failed to send Viber alert: {err}")

    def process_ups_update(self, data: UPSData):
        if not data:
            return

        lang = self._get_lang()
        name = data.name
        display_name = getattr(data, "display_name", None) or name
        location = data.location or "Local"
        state = self._get_state(name)
        now = time.time()
        now_str = _fmt_timestamp(now, lang=lang)
        overload_threshold = float(self.config.get("overload_threshold_pct", 70.0))
        alerts_cfg = self.config.get("alerts", {})

        # -------------------------------------------------------------
        # 1. Check Connection Lost / Restored with 3-failure debounce filter
        # -------------------------------------------------------------
        if not data.connected:
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        else:
            state["consecutive_failures"] = 0

        if state["last_connected"] is not None:
            # Only declare connection lost after 3 consecutive poll failures (approx. 6-10 sec of no response)
            if state["last_connected"] and not data.connected and state["consecutive_failures"] >= 3:
                state["last_connected"] = False
                if now - state["last_disconnect_alert"] > 60.0:
                    state["last_disconnect_alert"] = now
                    err_msg = _translate_error(data.error, lang=lang)
                    if lang == "el":
                        msg = (
                            f"🔌❌ *ΑΠΩΛΕΙΑ ΕΠΙΚΟΙΝΩΝΙΑΣ UPS*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ *UPS*: {display_name} ({location})\n"
                            f"📅 *Ώρα*: {now_str}\n"
                            f"🔴 *Κατάσταση*: OFFLINE / Δεν ανταποκρίνεται\n"
                            f"ℹ️ *Σφάλμα*: {err_msg}"
                        )
                    else:
                        msg = (
                            f"🔌❌ *UPS COMMUNICATION LOST*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ *UPS*: {display_name} ({location})\n"
                            f"📅 *Time*: {now_str}\n"
                            f"🔴 *Status*: OFFLINE / Not Responding\n"
                            f"ℹ️ *Error*: {err_msg}"
                        )

                    event = UPSEvent(
                        timestamp=now,
                        ups_name=display_name,
                        event_type="COMM_LOST",
                        message=msg,
                        severity="critical",
                        data={"error": data.error, "location": location, "raw_name": name},
                    )
                    self._trigger_event(event, send_viber=alerts_cfg.get("disconnect_alert", True))

            elif not state["last_connected"] and data.connected:
                # Connection restored
                state["last_connected"] = True
                if lang == "el":
                    msg = (
                        f"🔌✅ *ΕΠΑΝΑΦΟΡΑ ΕΠΙΚΟΙΝΩΝΙΑΣ UPS*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🟢 *UPS*: {display_name} ({location})\n"
                        f"📅 *Ώρα*: {now_str}\n"
                        f"🔋 *Κατάσταση*: {data.mode}\n"
                        f"⚡ *Είσοδος*: {data.input_v or '—'} V | *Έξοδος*: {data.output_v or '—'} V\n"
                        f"📊 *Φορτίο*: {data.load_pct or '0'}% ({data.load_w_est or '0'} W)\n"
                        f"🔋 *Μπαταρία*: {data.battery_pct or '—'}% ({data.battery_v or '—'} V)"
                    )
                else:
                    msg = (
                        f"🔌✅ *UPS COMMUNICATION RESTORED*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🟢 *UPS*: {display_name} ({location})\n"
                        f"📅 *Time*: {now_str}\n"
                        f"🔋 *Mode*: {data.mode}\n"
                        f"⚡ *Input*: {data.input_v or '—'} V | *Output*: {data.output_v or '—'} V\n"
                        f"📊 *Load*: {data.load_pct or '0'}% ({data.load_w_est or '0'} W)\n"
                        f"🔋 *Battery*: {data.battery_pct or '—'}% ({data.battery_v or '—'} V)"
                    )

                event = UPSEvent(
                    timestamp=now,
                    ups_name=display_name,
                    event_type="COMM_RESTORED",
                    message=msg,
                    severity="success",
                    data={"mode": data.mode, "location": location, "raw_name": name},
                )
                self._trigger_event(event, send_viber=alerts_cfg.get("disconnect_alert", True))
        elif state["last_connected"] is None and data.connected:
            state["last_connected"] = True

        # If offline, skip power/load alerts
        if not data.connected:
            return

        current_mode = (data.mode or "").capitalize()

        # -------------------------------------------------------------
        # 2. Check Power Outage (Line -> Battery & Repeating Updates)
        # -------------------------------------------------------------
        repeat_interval = float(self.config.get("outage_repeat_interval_seconds", 60.0))
        repeat_enabled = alerts_cfg.get("outage_repeat_alert", True) and repeat_interval > 0

        # Check if UPS is currently undergoing an intentional Self-Test
        is_in_self_test = bool(getattr(data, "test_active", False))
        if is_in_self_test:
            state["was_in_self_test"] = True

        if state["last_mode"] is not None:
            if state["last_mode"] != "Battery" and current_mode == "Battery":
                # Initial Outage Start
                state["outage_start_time"] = now
                state["last_outage_repeat_alert"] = now
                run_str = _fmt_runtime(data.runtime_minutes, lang=lang)

                if lang == "el":
                    msg = (
                        f"⚡🚨 *ΔΙΑΚΟΠΗ ΡΕΥΜΑΤΟΣ (MAINS FAILURE)*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ *UPS*: {display_name} ({location})\n"
                        f"📅 *Έναρξη*: {now_str}\n"
                        f"🔋 *Κατάσταση*: Λειτουργία με ΜΠΑΤΑΡΙΑ\n"
                        f"📉 *Τάση Εισόδου*: {data.input_v or 0:.1f} V (ΔΕΗ OFF)\n"
                        f"⚡ *Τάση Εξόδου*: {data.output_v or 230:.1f} V\n"
                        f"📊 *Φορτίο*: {data.load_pct or 0:.1f}% ({data.load_w_est or 0:.0f} W)\n"
                        f"🔋 *Επίπεδο Μπαταρίας*: ~{data.battery_pct or 100:.0f}% ({data.battery_v or 0:.1f} V)\n"
                        f"⏱️ *Εκτιμώμενη Αυτονομία*: {run_str}"
                    )
                else:
                    msg = (
                        f"⚡🚨 *MAINS POWER OUTAGE DETECTED*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ *UPS*: {display_name} ({location})\n"
                        f"📅 *Start Time*: {now_str}\n"
                        f"🔋 *Operating Mode*: BATTERY MODE\n"
                        f"📉 *Grid Input*: {data.input_v or 0:.1f} V (MAINS OFF)\n"
                        f"⚡ *UPS Output*: {data.output_v or 230:.1f} V\n"
                        f"📊 *Current Load*: {data.load_pct or 0:.1f}% ({data.load_w_est or 0:.0f} W)\n"
                        f"🔋 *Battery Level*: ~{data.battery_pct or 100:.0f}% ({data.battery_v or 0:.1f} V)\n"
                        f"⏱️ *Estimated Runtime*: {run_str}"
                    )

                event = UPSEvent(
                    timestamp=now,
                    ups_name=display_name,
                    event_type="POWER_OUTAGE",
                    message=msg,
                    severity="critical",
                    data={
                        "input_v": data.input_v,
                        "output_v": data.output_v,
                        "load_pct": data.load_pct,
                        "load_w": data.load_w_est,
                        "battery_pct": data.battery_pct,
                        "battery_v": data.battery_v,
                        "runtime_min": data.runtime_minutes,
                        "raw_name": name,
                    },
                )
                # Suppress false outage alert during battery self-test
                should_send = alerts_cfg.get("power_outage_alert", True) and not is_in_self_test
                self._trigger_event(event, send_viber=should_send)

            elif current_mode == "Battery" and state["last_mode"] == "Battery":
                # Continuing Outage: Periodic live status update
                if not state.get("outage_start_time"):
                    state["outage_start_time"] = now
                if not state.get("last_outage_repeat_alert"):
                    state["last_outage_repeat_alert"] = now

                time_since_last_alert = now - state["last_outage_repeat_alert"]
                if repeat_enabled and time_since_last_alert >= repeat_interval and not is_in_self_test:
                    state["last_outage_repeat_alert"] = now
                    duration_sec = now - state["outage_start_time"]
                    duration_str = _format_duration(duration_sec, lang=lang)
                    run_str = _fmt_runtime(data.runtime_minutes, lang=lang)

                    batt_low_threshold = float(self.config.get("battery_low_threshold_pct", 20.0))
                    crit_line = ""
                    if (data.battery_pct is not None and data.battery_pct <= batt_low_threshold) or bool(
                        data.battery_low
                    ):
                        crit_line = (
                            f"⚠️🚨 *ΚΡΙΣΙΜΗ ΧΑΜΗΛΗ ΙΣΧΥΣ* (<= {batt_low_threshold:.0f}%)\n"
                            if lang == "el"
                            else f"⚠️🚨 *CRITICAL LOW BATTERY* (<= {batt_low_threshold:.0f}%)\n"
                        )

                    if lang == "el":
                        msg = (
                            f"⚡⏳ *ΕΝΗΜΕΡΩΣΗ ΔΙΑΚΟΠΗΣ ΡΕΥΜΑΤΟΣ*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ *UPS*: {display_name} ({location})\n"
                            f"{crit_line}"
                            f"⏱️ *Διάρκεια Διακοπής*: {duration_str}\n"
                            f"🔋 *Μπαταρία*: {data.battery_pct or 0:.0f}% ({data.battery_v or 0:.1f} V)\n"
                            f"⏱️ *Υπολειπόμενη Αυτονομία*: {run_str}\n"
                            f"📊 *Τρέχον Φορτίο*: {data.load_pct or 0:.1f}% ({data.load_w_est or 0:.0f} W)\n"
                            f"⚡ *Τάση Εξόδου*: {data.output_v or 230:.1f} V"
                        )
                    else:
                        msg = (
                            f"⚡⏳ *ONGOING OUTAGE STATUS UPDATE*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ *UPS*: {display_name} ({location})\n"
                            f"{crit_line}"
                            f"⏱️ *Outage Elapsed*: {duration_str}\n"
                            f"🔋 *Battery Level*: {data.battery_pct or 0:.0f}% ({data.battery_v or 0:.1f} V)\n"
                            f"⏱️ *Remaining Runtime*: {run_str}\n"
                            f"📊 *Current Load*: {data.load_pct or 0:.1f}% ({data.load_w_est or 0:.0f} W)\n"
                            f"⚡ *UPS Output*: {data.output_v or 230:.1f} V"
                        )

                    event = UPSEvent(
                        timestamp=now,
                        ups_name=display_name,
                        event_type="OUTAGE_UPDATE",
                        message=msg,
                        severity="warning" if not crit_line else "critical",
                        data={
                            "duration": duration_str,
                            "battery_pct": data.battery_pct,
                            "battery_v": data.battery_v,
                            "runtime_min": data.runtime_minutes,
                            "load_pct": data.load_pct,
                            "load_w": data.load_w_est,
                            "is_critical": bool(crit_line),
                            "raw_name": name,
                        },
                    )
                    self._trigger_event(event, send_viber=alerts_cfg.get("power_outage_alert", True))

            # ---------------------------------------------------------
            # 3. Check Power Restored (Battery -> Line)
            # ---------------------------------------------------------
            elif state["last_mode"] == "Battery" and current_mode == "Line":
                was_self_test = is_in_self_test or state.get("was_in_self_test", False)
                state["was_in_self_test"] = False

                duration_str = "Άγνωστη" if lang == "el" else "Unknown"
                if state["outage_start_time"]:
                    duration_sec = now - state["outage_start_time"]
                    duration_str = _format_duration(duration_sec, lang=lang)
                state["outage_start_time"] = None
                state["last_outage_repeat_alert"] = 0.0

                if lang == "el":
                    msg = (
                        f"⚡🟢 *ΕΠΑΝΑΦΟΡΑ ΡΕΥΜΑΤΟΣ (MAINS RESTORED)*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ *UPS*: {display_name} ({location})\n"
                        f"📅 *Ώρα*: {now_str}\n"
                        f"⏱️ *Συνολική Διάρκεια Διακοπής*: {duration_str}\n"
                        f"📈 *Τάση Εισόδου*: {data.input_v or 230:.1f} V (Κανονική)\n"
                        f"⚡ *Τάση Εξόδου*: {data.output_v or 230:.1f} V\n"
                        f"📊 *Φορτίο*: {data.load_pct or 0:.1f}% ({data.load_w_est or 0:.0f} W)\n"
                        f"🔋 *Υπολειπόμενη Μπαταρία*: {data.battery_pct or 'CHG'}% ({data.battery_v or 0:.1f} V)"
                    )
                else:
                    msg = (
                        f"⚡🟢 *MAINS POWER RESTORED*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ *UPS*: {display_name} ({location})\n"
                        f"📅 *Time*: {now_str}\n"
                        f"⏱️ *Total Outage Duration*: {duration_str}\n"
                        f"📈 *Grid Input*: {data.input_v or 230:.1f} V (Normal)\n"
                        f"⚡ *UPS Output*: {data.output_v or 230:.1f} V\n"
                        f"📊 *Current Load*: {data.load_pct or 0:.1f}% ({data.load_w_est or 0:.0f} W)\n"
                        f"🔋 *Battery Status*: {data.battery_pct or 'CHG'}% ({data.battery_v or 0:.1f} V)"
                    )

                event = UPSEvent(
                    timestamp=now,
                    ups_name=display_name,
                    event_type="POWER_RESTORED",
                    message=msg,
                    severity="success",
                    data={
                        "duration": duration_str,
                        "input_v": data.input_v,
                        "battery_pct": data.battery_pct,
                        "raw_name": name,
                    },
                )
                # Suppress false restore alert if it was just a self-test cycle
                should_send = alerts_cfg.get("power_restore_alert", True) and not was_self_test
                self._trigger_event(event, send_viber=should_send)

        state["last_mode"] = current_mode

        # -------------------------------------------------------------
        # 4. Check Overload (> 70% or configured threshold)
        # -------------------------------------------------------------
        load_pct = data.load_pct or 0.0
        if load_pct >= overload_threshold:
            if not state["overload_active"] or (now - state["last_overload_alert"] > 600.0):
                state["overload_active"] = True
                state["last_overload_alert"] = now
                if lang == "el":
                    msg = (
                        f"⚠️🚨 *ΥΠΕΡΦΟΡΤΩΣΗ UPS (OVERLOAD)*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🔥 *UPS*: {display_name} ({location})\n"
                        f"📅 *Ώρα*: {now_str}\n"
                        f"📊 *Τρέχον Φορτίο*: {load_pct:.1f}% (Όριο: {overload_threshold:.0f}%)\n"
                        f"⚡ *Ισχύς*: ~{data.load_w_est or 0:.0f} W\n"
                        f"⚠️ Συνιστάται άμεση αποσύνδεση μη απαραίτητων συσκευών."
                    )
                else:
                    msg = (
                        f"⚠️🚨 *UPS OVERLOAD WARNING*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🔥 *UPS*: {display_name} ({location})\n"
                        f"📅 *Time*: {now_str}\n"
                        f"📊 *Current Load*: {load_pct:.1f}% (Threshold: {overload_threshold:.0f}%)\n"
                        f"⚡ *Power Load*: ~{data.load_w_est or 0:.0f} W\n"
                        f"⚠️ Immediate disconnect of non-critical devices recommended."
                    )

                event = UPSEvent(
                    timestamp=now,
                    ups_name=display_name,
                    event_type="OVERLOAD",
                    message=msg,
                    severity="warning",
                    data={"load_pct": load_pct, "load_w": data.load_w_est, "raw_name": name},
                )
                self._trigger_event(event, send_viber=alerts_cfg.get("overload_alert", True))
        elif load_pct < (overload_threshold - 5.0):
            if state["overload_active"]:
                state["overload_active"] = False
                if lang == "el":
                    msg = (
                        f"✅ *ΟΜΑΛΟΠΟΙΗΣΗ ΦΟΡΤΙΟΥ UPS*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🟢 *UPS*: {display_name} ({location})\n"
                        f"📅 *Ώρα*: {now_str}\n"
                        f"📊 *Τρέχον Φορτίο*: {load_pct:.1f}% (Κάτω από το όριο)"
                    )
                else:
                    msg = (
                        f"✅ *UPS LOAD NORMALIZED*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🟢 *UPS*: {display_name} ({location})\n"
                        f"📅 *Time*: {now_str}\n"
                        f"📊 *Current Load*: {load_pct:.1f}% (Below threshold)"
                    )

                event = UPSEvent(
                    timestamp=now,
                    ups_name=display_name,
                    event_type="OVERLOAD_CLEARED",
                    message=msg,
                    severity="info",
                    data={"load_pct": load_pct, "raw_name": name},
                )
                self._trigger_event(event, send_viber=False)

        # -------------------------------------------------------------
        # 5. Check Battery Low (Critical Low Power)
        # -------------------------------------------------------------
        batt_low_threshold = float(self.config.get("battery_low_threshold_pct", 20.0))
        is_batt_low = bool(data.battery_low) or (
            data.battery_pct is not None and data.battery_pct <= batt_low_threshold and current_mode == "Battery"
        )
        if is_batt_low:
            if now - state["last_battery_low_alert"] > 300.0:
                state["last_battery_low_alert"] = now
                run_str = _fmt_runtime(data.runtime_minutes, lang=lang)
                if lang == "el":
                    msg = (
                        f"🪫🚨 *ΚΡΙΣΙΜΗ ΧΑΜΗΛΗ ΙΣΧΥΣ UPS*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🔴 *UPS*: {display_name} ({location})\n"
                        f"📅 *Ώρα*: {now_str}\n"
                        f"⚠️ *Κατάσταση*: Κρίσιμη χαμηλή ισχύς (<= {batt_low_threshold:.0f}%)\n"
                        f"🔋 *Επίπεδο Μπαταρίας*: {data.battery_pct or 'Low'}% ({data.battery_v or 0:.1f} V)\n"
                        f"⏱️ *Υπολειπόμενος Χρόνος*: {run_str}\n"
                        f"⚠️ Επίκειται τερματισμός λειτουργίας!"
                    )
                else:
                    msg = (
                        f"🪫🚨 *CRITICAL LOW BATTERY WARNING*\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🔴 *UPS*: {display_name} ({location})\n"
                        f"📅 *Time*: {now_str}\n"
                        f"⚠️ *Condition*: Critical Low Battery (<= {batt_low_threshold:.0f}%)\n"
                        f"🔋 *Battery Level*: {data.battery_pct or 'Low'}% ({data.battery_v or 0:.1f} V)\n"
                        f"⏱️ *Remaining Runtime*: {run_str}\n"
                        f"⚠️ System shutdown imminent!"
                    )

                event = UPSEvent(
                    timestamp=now,
                    ups_name=display_name,
                    event_type="BATTERY_LOW",
                    message=msg,
                    severity="critical",
                    data={"battery_pct": data.battery_pct, "battery_v": data.battery_v, "raw_name": name},
                )
                self._trigger_event(event, send_viber=alerts_cfg.get("battery_low_alert", True))

    def check_daily_report_schedule(self, all_ups_data: List[UPSData]):
        """
        Sends a comprehensive daily status report once a day at the configured hour:minute (e.g. 09:00).
        """
        report_time_str = self.config.get("daily_report_time", "09:00").strip()
        enabled = self.config.get("alerts", {}).get("daily_report", True)
        if not enabled:
            return

        now_struct = time.localtime()
        current_hm = time.strftime("%H:%M", now_struct)
        today_date = time.strftime("%Y-%m-%d", now_struct)

        if current_hm == report_time_str and self.last_daily_report_date != today_date:
            self.last_daily_report_date = today_date
            self.send_daily_report(all_ups_data)

    def send_daily_report(self, all_ups_data: List[UPSData]) -> Tuple[bool, Optional[str]]:
        lang = self._get_lang()
        now_str = _fmt_timestamp(time.time(), lang=lang)

        if lang == "el":
            msg = (
                f"📊 *ΗΜΕΡΗΣΙΑ ΑΝΑΦΟΡΑ ΚΑΤΑΣΤΑΣΗΣ UPS*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 Ημερομηνία & Ώρα: {now_str}\n\n"
            )
        else:
            msg = (
                f"📊 *UPS DAILY STATUS REPORT*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 Date & Time: {now_str}\n\n"
            )

        total_watts = 0.0

        for d in all_ups_data:
            disp = getattr(d, "display_name", None) or d.name
            loc = d.location or "Local"
            icon = "🟢" if (d.connected and d.mode == "Line") else ("🟡" if d.mode == "Battery" else "🔴")
            status_title = d.mode if d.connected else "OFFLINE"
            watts = d.load_w_est or 0.0
            total_watts += watts if d.connected else 0.0

            msg += f"{icon} *{disp}* [{loc}]\n"
            if d.connected:
                if lang == "el":
                    msg += (
                        f"  • Κατάσταση: *{status_title}*\n"
                        f"  • Τάση ΔΕΗ / Έξοδος: {d.input_v or '—'} V / {d.output_v or '—'} V ({d.input_hz or '—'} Hz)\n"
                        f"  • Φορτίο: *{d.load_pct or 0:.1f}%* (~{watts:.0f} W)\n"
                        f"  • Μπαταρία: *{d.battery_pct or 'CHG'}%* ({d.battery_v or '—'} V)\n"
                        f"  • Αυτονομία: ~{_fmt_runtime(d.runtime_minutes, lang=lang)}\n\n"
                    )
                else:
                    msg += (
                        f"  • Status: *{status_title}*\n"
                        f"  • Grid In / Out: {d.input_v or '—'} V / {d.output_v or '—'} V ({d.input_hz or '—'} Hz)\n"
                        f"  • Load: *{d.load_pct or 0:.1f}%* (~{watts:.0f} W)\n"
                        f"  • Battery: *{d.battery_pct or 'CHG'}%* ({d.battery_v or '—'} V)\n"
                        f"  • Runtime: ~{_fmt_runtime(d.runtime_minutes, lang=lang)}\n\n"
                    )
            else:
                err_text = _translate_error(d.error, lang=lang)
                if lang == "el":
                    msg += f"  • Κατάσταση: *OFFLINE* ({err_text})\n\n"
                else:
                    msg += f"  • Status: *OFFLINE* ({err_text})\n\n"

        if lang == "el":
            msg += (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ *Συνολική Κατανάλωση*: ~{total_watts:.0f} W\n"
                f"🛡️ Όλα τα συστήματα προστασίας ενεργά."
            )
        else:
            msg += (
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ *Total Power Load*: ~{total_watts:.0f} W\n"
                f"🛡️ All protection systems online and active."
            )

        event = UPSEvent(
            timestamp=time.time(),
            ups_name="SYSTEM",
            event_type="DAILY_REPORT",
            message=msg,
            severity="info",
            data={"total_watts": total_watts, "ups_count": len(all_ups_data)},
        )

        self._trigger_event(event, send_viber=True)
        return True, None

    def send_self_test_started_alert(
        self,
        ups_name: str,
        slot_name: str,
        location: str,
        trigger_type: str = "manual",
    ) -> UPSEvent:
        lang = self._get_lang()
        now = time.time()
        now_str = _fmt_timestamp(now, lang=lang)
        trig_str = "Αυτόματο (Χρονοδιακόπτης)" if trigger_type == "schedule" else "Χειροκίνητο (WebUI)"
        if lang != "el":
            trig_str = "Scheduled (Timer)" if trigger_type == "schedule" else "Manual (WebUI)"

        safe_ups_name = ups_name or slot_name or "UPS"
        if lang == "el":
            msg = (
                f"🧪⚡ *ΕΝΑΡΞΗ SELF-TEST UPS*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ *UPS*: {safe_ups_name} [{slot_name}] ({location})\n"
                f"📅 *Ώρα*: {now_str}\n"
                f"⚙️ *Τύπος Έναρξης*: {trig_str}\n"
                f"⏳ Εκτέλεση δοκιμής μπαταρίας 10 δευτερολέπτων..."
            )
        else:
            msg = (
                f"🧪⚡ *UPS SELF-TEST STARTED*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ *UPS*: {safe_ups_name} [{slot_name}] ({location})\n"
                f"📅 *Time*: {now_str}\n"
                f"⚙️ *Trigger*: {trig_str}\n"
                f"⏳ Running 10-second battery discharge test..."
            )

        viber_enabled = self.config.get("alerts", {}).get("self_test_alert", True) and self.config.get(
            "self_test", {}
        ).get("notify_viber", True)

        event = UPSEvent(
            timestamp=now,
            ups_name=safe_ups_name,
            event_type="SELF_TEST_STARTED",
            message=msg,
            severity="info",
            data={"slot_name": slot_name, "trigger_type": trigger_type, "location": location},
        )
        self._trigger_event(event, send_viber=viber_enabled)
        return event

    def send_self_test_result_alert(
        self,
        ups_name: str,
        slot_name: str,
        location: str,
        status: str,  # 'PASSED' or 'FAILED'
        battery_v_before: Optional[float] = None,
        battery_v_min: Optional[float] = None,
        battery_pct: Optional[float] = None,
        load_pct: Optional[float] = None,
        load_w: Optional[float] = None,
        duration_sec: float = 10.0,
        trigger_type: str = "manual",
        details: str = "",
    ) -> UPSEvent:
        lang = self._get_lang()
        now = time.time()
        now_str = _fmt_timestamp(now, lang=lang)
        safe_ups_name = ups_name or slot_name or "UPS"
        viber_enabled = self.config.get("alerts", {}).get("self_test_alert", True) and self.config.get(
            "self_test", {}
        ).get("notify_viber", True)

        v_min_str = f"{battery_v_min:.1f} V" if battery_v_min is not None else "—"
        v_bef_str = f"{battery_v_before:.1f} V" if battery_v_before is not None else "—"
        load_pct_str = f"{load_pct:.1f}%" if load_pct is not None else "0%"
        load_w_str = f"~{load_w:.0f} W" if load_w is not None else "— W"
        batt_pct_str = f"~{battery_pct:.0f}%" if battery_pct is not None else "—"

        if status == "PASSED":
            if lang == "el":
                msg = (
                    f"🧪✅ *ΕΠΙΤΥΧΕΣ SELF-TEST UPS*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🟢 *UPS*: {safe_ups_name} [{slot_name}] ({location})\n"
                    f"📅 *Ώρα Ολοκλήρωσης*: {now_str}\n"
                    f"🔋 *Τάση Μπαταρίας (Υπό Δοκιμή)*: {v_min_str} (Αρχική: {v_bef_str})\n"
                    f"🔋 *Στάθμη Μπαταρίας*: {batt_pct_str}\n"
                    f"📊 *Φορτίο*: {load_pct_str} ({load_w_str})\n"
                    f"⏱️ *Διάρκεια*: {duration_sec:.0f} δευτερόλεπτα\n"
                    f"✅ *Αποτέλεσμα*: Όλα τα συστήματα και η μπαταρία λειτουργούν άψογα!"
                )
            else:
                msg = (
                    f"🧪✅ *UPS SELF-TEST PASSED*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🟢 *UPS*: {safe_ups_name} [{slot_name}] ({location})\n"
                    f"📅 *Completion Time*: {now_str}\n"
                    f"🔋 *Battery Voltage (Under Test)*: {v_min_str} (Initial: {v_bef_str})\n"
                    f"🔋 *Battery Level*: {batt_pct_str}\n"
                    f"📊 *Load*: {load_pct_str} ({load_w_str})\n"
                    f"⏱️ *Duration*: {duration_sec:.0f} seconds\n"
                    f"✅ *Result*: Battery and inverter circuits tested healthy!"
                )

            event = UPSEvent(
                timestamp=now,
                ups_name=safe_ups_name,
                event_type="SELF_TEST_PASSED",
                message=msg,
                severity="success",
                data={
                    "slot_name": slot_name,
                    "status": "PASSED",
                    "battery_v_min": battery_v_min,
                    "battery_v_before": battery_v_before,
                    "battery_pct": battery_pct,
                    "load_pct": load_pct,
                    "duration_sec": duration_sec,
                    "trigger_type": trigger_type,
                    "details": details,
                },
            )
            self._trigger_event(event, send_viber=viber_enabled)
            return event
        else:
            if lang == "el":
                msg = (
                    f"🧪🚨❌ *ΑΠΟΤΥΧΙΑ SELF-TEST UPS*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 *UPS*: {safe_ups_name} [{slot_name}] ({location})\n"
                    f"📅 *Ώρα*: {now_str}\n"
                    f"⚠️ *Αποτέλεσμα*: ΑΣΤΟΧΙΑ ΔΟΚΙΜΗΣ ΜΠΑΤΑΡΙΑΣ!\n"
                    f"🔋 *Ελάχιστη Τάση*: {v_min_str} (Αρχική: {v_bef_str})\n"
                    f"📊 *Φορτίο*: {load_pct_str} ({load_w_str})\n"
                    f"ℹ️ *Σφάλμα/Λεπτομέρειες*: {details or 'Κρίσιμη πτώση τάσης υπό φορτίο'}\n"
                    f"⚠️ *Προσοχή*: Συνιστάται άμεσος τεχνικός έλεγχος ή αντικατάσταση των μπαταριών!"
                )
            else:
                msg = (
                    f"🧪🚨❌ *UPS SELF-TEST FAILED*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 *UPS*: {safe_ups_name} [{slot_name}] ({location})\n"
                    f"📅 *Time*: {now_str}\n"
                    f"⚠️ *Result*: BATTERY SELF-TEST FAILED!\n"
                    f"🔋 *Lowest Voltage*: {v_min_str} (Initial: {v_bef_str})\n"
                    f"📊 *Load*: {load_pct_str} ({load_w_str})\n"
                    f"ℹ️ *Details*: {details or 'Critical voltage sag under load'}\n"
                    f"⚠️ *Warning*: Urgent battery inspection or replacement recommended!"
                )

            event = UPSEvent(
                timestamp=now,
                ups_name=safe_ups_name,
                event_type="SELF_TEST_FAILED",
                message=msg,
                severity="critical",
                data={
                    "slot_name": slot_name,
                    "status": "FAILED",
                    "battery_v_min": battery_v_min,
                    "battery_v_before": battery_v_before,
                    "battery_pct": battery_pct,
                    "load_pct": load_pct,
                    "duration_sec": duration_sec,
                    "trigger_type": trigger_type,
                    "details": details,
                },
            )
            self._trigger_event(event, send_viber=viber_enabled)
            return event

    def log_buzzer_toggle_event(self, ups_name: str, slot_name: str, new_state_on: bool) -> UPSEvent:
        lang = self._get_lang()
        now = time.time()
        now_str = _fmt_timestamp(now, lang=lang)
        safe_ups_name = ups_name or slot_name or "UPS"
        state_str = "Ενεργοποιήθηκε (ON)" if new_state_on else "Σιγάστηκε / Απενεργοποιήθηκε (MUTED/OFF)"
        if lang != "el":
            state_str = "Enabled (ON)" if new_state_on else "Silenced / Disabled (MUTED/OFF)"

        if lang == "el":
            msg = (
                f"🔔 *ΑΛΛΑΓΗ ΚΑΤΑΣΤΑΣΗΣ BUZZER UPS*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ *UPS*: {safe_ups_name} [{slot_name}]\n"
                f"📅 *Ώρα*: {now_str}\n"
                f"📢 *Ηχητικός Συναγερμός (Buzzer)*: {state_str}"
            )
        else:
            msg = (
                f"🔔 *UPS BUZZER STATE CHANGED*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ *UPS*: {safe_ups_name} [{slot_name}]\n"
                f"📅 *Time*: {now_str}\n"
                f"📢 *Audible Buzzer*: {state_str}"
            )

        event = UPSEvent(
            timestamp=now,
            ups_name=safe_ups_name,
            event_type="BUZZER_TOGGLED",
            message=msg,
            severity="info",
            data={"slot_name": slot_name, "beeper_on": new_state_on},
        )
        self._trigger_event(event, send_viber=False)
        return event
