from __future__ import annotations

import time
from typing import Any, Optional
from drivers.models import UPSData
from drivers.estimator import estimate_sla_24v_soc


def _num(v: Any) -> Optional[float]:
    try:
        return float(str(v).strip())
    except Exception:
        return None


def parse_q1(raw: str, name: str, source: str, location: str = "Local") -> UPSData:
    out = UPSData(
        name=name,
        source=source,
        connected=True,
        raw=raw,
        location=location,
        last_updated=time.time(),
    )

    s = raw.strip().replace("\x00", "")
    if not s.startswith("("):
        out.error = f"Unexpected Q1 reply: {raw!r}"
        out.connected = False
        out.mode = "Error"
        return out

    parts = s[1:].strip().split()
    if len(parts) < 8:
        out.error = f"Short Q1 reply: {raw!r}"
        out.connected = False
        out.mode = "Error"
        return out

    out.input_v = _num(parts[0])
    # parts[1] = input/fault voltage
    out.output_v = _num(parts[2])
    out.load_pct = _num(parts[3])
    out.input_hz = _num(parts[4])
    out.output_hz = out.input_hz
    out.battery_v = _num(parts[5])
    out.temperature_c = _num(parts[6])

    bits = parts[7][:8]
    if len(bits) == 8 and all(c in "01" for c in bits):
        # Megatec/Q1 status bits:
        # [0] utility fail, [1] battery low, [2] bypass/boost/buck,
        # [3] UPS failed, [4] standby/line-interactive,
        # [5] test active, [6] shutdown active, [7] beeper on.
        utility_fail = bits[0] == "1"
        out.battery_low = bits[1] == "1"
        out.fault = bits[3] == "1"
        out.test_active = bits[5] == "1"
        out.beeper_on = bits[7] == "1"

        if out.fault:
            out.mode = "Fault"
        elif utility_fail:
            out.mode = "Battery"
        else:
            out.mode = "Line"

    out.battery_pct = estimate_sla_24v_soc(
        out.battery_v,
        out.load_pct,
        out.mode,
    )

    return out
