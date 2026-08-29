from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from drivers.models import UPSData


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
        float_min = 26.5 if is_24v else 13.25
        empty_v = 22.0 if is_24v else 11.0
        if battery_v >= float_min:
            return 100.0
        pct = (battery_v - empty_v) / (float_min - empty_v) * 100.0
        return round(min(100.0, max(0.0, pct)), 1)

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


def peukert_capacity_factor(load_w: float, profile: Dict[str, float]) -> float:
    """
    Approximate the reduction in usable SLA capacity at higher discharge rates.
    """
    bank_v = max(float(profile.get("bank_v", 24.0)), 1.0)
    ah = max(float(profile.get("battery_ah", 9.0)), 0.1)
    eff = max(min(float(profile.get("inverter_efficiency", 0.85)), 0.98), 0.50)
    k = max(float(profile.get("peukert_exponent", 1.15)), 1.0)

    if load_w <= 1.0:
        return 1.0

    battery_current_a = load_w / (bank_v * eff)
    reference_current_a = ah / 20.0  # nominal 20-hour capacity rating

    if battery_current_a <= reference_current_a:
        return 1.0

    factor = (reference_current_a / battery_current_a) ** (k - 1.0)
    return max(0.35, min(1.0, factor))


class RuntimeEstimator:
    """
    Runtime estimator with two layers:
    1) Immediate model:
       rated watts + load % + 24 V battery Ah + SOC + inverter efficiency + Peukert correction.
    2) Adaptive learning:
       watches real battery discharge events and updates persistent battery-health factor.
    """

    def __init__(self, profiles: Dict[str, Dict[str, float]], learning_path: Path):
        self.profiles = profiles
        self.learning_path = learning_path
        self.learning = self._load_json(learning_path, {})
        if not isinstance(self.learning, dict):
            self.learning = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _load_json(path: Path, default):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    def _save_learning(self) -> None:
        try:
            self.learning_path.write_text(
                json.dumps(self.learning, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def update_profiles(self, profiles: Dict[str, Dict[str, float]]):
        self.profiles = profiles

    def _profile(self, name: str) -> Dict[str, float]:
        if not name:
            return self._default_profile()

        # 1. Direct match
        p = self.profiles.get(name)
        if isinstance(p, dict):
            return p

        # 2. Match by display_name or canonical keys
        name_clean = name.lower().replace("-", "").replace("_", "").replace(" ", "")
        for k, prof in self.profiles.items():
            if not isinstance(prof, dict):
                continue
            k_clean = k.lower().replace("-", "").replace("_", "").replace(" ", "")
            disp = str(prof.get("display_name", "")).lower().replace("-", "").replace("_", "").replace(" ", "")
            if name_clean in (k_clean, disp) or k_clean in name_clean or disp in name_clean:
                return prof
            if ("remote" in name_clean or "network" in name_clean or "3" in name_clean) and "remote" in k_clean:
                return prof

        return self._default_profile()

    def _default_profile(self) -> Dict[str, float]:
        return {
            "rated_w": 900.0,
            "bank_v": 24.0,
            "battery_ah": 9.0,
            "inverter_efficiency": 0.85,
            "peukert_exponent": 1.15,
        }

    def get_health(self, name: str) -> float:
        item = self.learning.get(name, {})
        try:
            return max(0.35, min(1.20, float(item.get("health_factor", 1.0))))
        except Exception:
            return 1.0

    def _model_runtime(
        self,
        d: UPSData,
        profile: Dict[str, float],
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if d.load_pct is None:
            return None, None, None

        rated_w = max(float(profile.get("rated_w", 1200.0)), 0.0)
        bank_v = max(float(profile.get("bank_v", 24.0)), 1.0)
        ah = max(float(profile.get("battery_ah", 9.0)), 0.1)
        eff = max(min(float(profile.get("inverter_efficiency", 0.85)), 0.98), 0.50)

        load_pct = max(0.0, min(float(d.load_pct), 100.0))
        load_w = rated_w * load_pct / 100.0

        if rated_w <= 0:
            return load_w, None, None

        # If battery % is not directly reported, calculate SOC approximation
        soc_val = d.battery_pct
        if soc_val is None:
            soc_val = estimate_sla_24v_soc(d.battery_v, d.load_pct, d.mode)
            if soc_val is not None:
                d.battery_pct = soc_val

        if soc_val is None:
            # If still None (e.g. charging), default to full runtime estimation for line mode display
            if (d.mode or "").lower() == "line":
                soc_val = 100.0
            else:
                return load_w, None, None

        if load_w < 5.0:
            return load_w, None, None

        soc = max(0.0, min(float(soc_val), 100.0)) / 100.0
        peukert = peukert_capacity_factor(load_w, profile)
        health = self.get_health(d.name)

        nominal_wh = bank_v * ah
        usable_output_wh = nominal_wh * soc * eff * peukert * health
        runtime_min = (usable_output_wh / load_w) * 60.0

        return load_w, max(0.0, runtime_min), peukert

    def _slope_runtime(self, name: str, d: UPSData) -> Optional[float]:
        sess = self.sessions.get(name)
        if not sess or d.battery_pct is None or d.load_pct is None:
            return None

        hist = sess.get("history")
        if not hist or len(hist) < 2:
            return None

        now = time.monotonic()
        current_soc = float(d.battery_pct)
        current_load = max(float(d.load_pct), 0.1)

        candidates = [x for x in hist if now - x[0] >= 180.0]
        if not candidates:
            return None

        old_t, old_soc, old_load = candidates[0]
        dt_min = (now - old_t) / 60.0
        drop = old_soc - current_soc
        if dt_min < 3.0 or drop < 3.0:
            return None

        rate_pct_per_min = drop / dt_min
        if rate_pct_per_min <= 0:
            return None

        loads = [x[2] for x in hist if x[0] >= old_t]
        avg_load = sum(loads) / len(loads) if loads else current_load
        if avg_load <= 0:
            return None
        ratio = current_load / avg_load
        if ratio < 0.70 or ratio > 1.30:
            return None

        remaining = current_soc / rate_pct_per_min
        return max(0.0, min(600.0, remaining))

    def _start_or_update_session(
        self,
        d: UPSData,
        profile: Dict[str, float],
        load_w: Optional[float],
        peukert: Optional[float],
    ) -> None:
        if d.battery_pct is None:
            return

        now = time.monotonic()
        sess = self.sessions.get(d.name)

        if sess is None:
            sess = {
                "start": now,
                "last": now,
                "initial_soc": float(d.battery_pct),
                "last_soc": float(d.battery_pct),
                "energy_out_wh": 0.0,
                "peukert_seconds": 0.0,
                "seconds": 0.0,
                "history": deque(maxlen=1800),
            }
            self.sessions[d.name] = sess

        dt = max(0.0, min(now - float(sess["last"]), 30.0))
        sess["last"] = now
        sess["last_soc"] = float(d.battery_pct)

        if load_w is not None and dt > 0:
            sess["energy_out_wh"] += load_w * dt / 3600.0

        if peukert is not None and dt > 0:
            sess["peukert_seconds"] += peukert * dt
            sess["seconds"] += dt

        sess["history"].append((now, float(d.battery_pct), float(d.load_pct or 0.0)))

    def _finish_session(self, name: str, profile: Dict[str, float]) -> None:
        sess = self.sessions.pop(name, None)
        if not sess:
            return

        duration = float(sess["last"]) - float(sess["start"])
        initial_soc = float(sess["initial_soc"])
        final_soc = float(sess["last_soc"])
        delta_soc = initial_soc - final_soc
        energy_out_wh = float(sess["energy_out_wh"])

        if duration < 600.0 or delta_soc < 10.0 or energy_out_wh < 2.0:
            return

        bank_v = max(float(profile.get("bank_v", 24.0)), 1.0)
        ah = max(float(profile.get("battery_ah", 9.0)), 0.1)
        eff = max(min(float(profile.get("inverter_efficiency", 0.85)), 0.98), 0.50)
        nominal_wh = bank_v * ah

        secs = max(float(sess["seconds"]), 1.0)
        avg_peukert = float(sess["peukert_seconds"]) / secs
        avg_peukert = max(0.35, min(1.0, avg_peukert))

        expected_output_wh_at_full_health = (
            nominal_wh * (delta_soc / 100.0) * eff * avg_peukert
        )

        if expected_output_wh_at_full_health <= 0:
            return

        observed_health = energy_out_wh / expected_output_wh_at_full_health
        observed_health = max(0.35, min(1.20, observed_health))

        item = self.learning.get(name, {})
        try:
            old_health = float(item.get("health_factor", 1.0))
        except Exception:
            old_health = 1.0

        sessions = int(item.get("sessions", 0))
        new_health = 0.80 * old_health + 0.20 * observed_health

        self.learning[name] = {
            "health_factor": round(max(0.35, min(1.20, new_health)), 4),
            "sessions": sessions + 1,
            "last_observed_health": round(observed_health, 4),
            "last_duration_min": round(duration / 60.0, 1),
            "last_soc_drop_pct": round(delta_soc, 1),
            "last_energy_out_wh": round(energy_out_wh, 2),
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save_learning()

    def update(self, d: UPSData) -> UPSData:
        if not d.connected:
            return d

        profile = self._profile(d.name)

        # Estimate SLA SOC if not provided
        if d.battery_pct is None:
            d.battery_pct = estimate_sla_24v_soc(d.battery_v, d.load_pct, d.mode)

        load_w, model_runtime, peukert = self._model_runtime(d, profile)
        d.load_w_est = round(load_w, 1) if load_w is not None else None

        if (d.mode or "").lower() == "battery":
            self._start_or_update_session(d, profile, load_w, peukert)
            slope_runtime = self._slope_runtime(d.name, d)

            if model_runtime is not None and slope_runtime is not None:
                sess = self.sessions.get(d.name, {})
                initial_soc = float(sess.get("initial_soc", d.battery_pct or 0.0))
                drop = max(0.0, initial_soc - float(d.battery_pct or 0.0))

                w = max(0.20, min(0.70, drop / 25.0))
                d.runtime_minutes = model_runtime * (1.0 - w) + slope_runtime * w
                d.runtime_source = "model+live-learning"
            else:
                d.runtime_minutes = model_runtime
                d.runtime_source = "model"
        else:
            if d.name in self.sessions:
                self._finish_session(d.name, profile)

            d.runtime_minutes = model_runtime
            d.runtime_source = "model"

        if d.runtime_minutes is not None:
            d.runtime_minutes = round(max(0.0, min(600.0, d.runtime_minutes)), 1)

        return d
