from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import (
    BASE_DIR,
    DB_FILE,
    LEARNING_FILE,
    get_config,
    get_profiles,
    save_config,
    save_profiles,
)
from database.db_manager import DBManager
from drivers.estimator import RuntimeEstimator
from drivers.models import UPSData, UPSEvent
from drivers.remote_receiver import RemoteReceiver
from drivers.device_manager import device_manager
from notifications.alert_manager import AlertManager
from notifications.viber_service import ViberService
import updater

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Electra.App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(monitoring_loop())
    yield
    task.cancel()


app = FastAPI(title="Electra - UPS Status Central Monitor", version="1.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# App Global State
config_data = get_config()
profiles_data = get_profiles()

db_manager = DBManager(DB_FILE)
estimator = RuntimeEstimator(profiles_data, LEARNING_FILE)

viber_cfg = config_data.get("viber", {})
viber_service = ViberService(
    token=viber_cfg.get("channel_token", ""),
    sender_name=viber_cfg.get("sender_name", "UPS Monitor"),
    receiver_id=viber_cfg.get("receiver_id", ""),
)

# Active SSE Client Queues
sse_clients: List[asyncio.Queue] = []


def on_new_event(event: UPSEvent):
    """Broadcasts newly created events to all connected WebUI streams."""
    payload = f"event: ups_event\ndata: {json.dumps(event.to_dict())}\n\n"
    for q in list(sse_clients):
        try:
            q.put_nowait(payload)
        except Exception:
            pass


alert_manager = AlertManager(
    db=db_manager,
    viber=viber_service,
    config=config_data,
    on_event_callback=on_new_event,
)

# Hardware Driver / Receiver Instances
remote_receiver = RemoteReceiver(name="Remote-1", location="Remote Site")

# Live state container (Local-1, Local-2, Remote-1)
latest_ups_state: Dict[str, UPSData] = {
    "Local-1": UPSData(name="Local-1", source="Auto-Scan", location="Local Port 1"),
    "Local-2": UPSData(name="Local-2", source="Auto-Scan", location="Local Port 2"),
    "Remote-1": UPSData(name="Remote-1", source="Remote IP", location="Remote Site"),
}

last_db_log_time = 0.0
last_cleanup_time = 0.0
last_logged_telemetry_snapshot: Dict[str, Dict[str, Any]] = {}

# Remote Command Queue for Remote Agent (Piggyback Two-Way Dispatch)
remote_pending_commands: List[str] = []

active_self_tests: Dict[str, Dict[str, Any]] = {}
last_scheduled_self_test_key: Optional[str] = None


def resolve_slot_name(slot_name: str) -> str:
    """Resolves arbitrary slot names, display names, or aliases into canonical slot keys (Local-1, Local-2, Remote-1)."""
    if not slot_name:
        return "Local-1"
    if slot_name in latest_ups_state:
        return slot_name
    profiles = get_profiles()
    if slot_name in profiles:
        return slot_name
    for k, p in profiles.items():
        if p.get("display_name") == slot_name:
            return k
        if p.get("display_name", "").replace(" ", "_") == slot_name:
            return k
    s_clean = slot_name.lower().replace("-", "").replace("_", "").replace(" ", "")
    for k in ("Local-1", "Local-2", "Remote-1"):
        k_clean = k.lower().replace("-", "").replace("_", "").replace(" ", "")
        if k_clean in s_clean or s_clean in k_clean:
            return k
    if "1" in s_clean or "tec" in s_clean or "primary" in s_clean or "usb1" in s_clean:
        return "Local-1"
    if "2" in s_clean or "turbo" in s_clean or "secondary" in s_clean or "usb2" in s_clean:
        return "Local-2"
    if "3" in s_clean or "remote" in s_clean or "network" in s_clean:
        return "Remote-1"
    return slot_name


def queue_remote_command(cmd: str):
    """Queues command for next remote agent push response."""
    global remote_pending_commands
    if cmd not in remote_pending_commands:
        remote_pending_commands.append(cmd)
        logger.info(f"Queued remote command: '{cmd}'")


def get_ups_list_for_response() -> List[Dict[str, Any]]:
    out = []
    latest_st_map = db_manager.get_all_latest_self_tests()
    profs = get_profiles()

    ordered_slots = []
    seen = set()

    # Priority slot order
    for s in ["Local-1", "Local-2", "Remote-1", "TEC", "Turbo-X", "Remote-UPS"]:
        if s in profs or s in latest_ups_state:
            if s not in seen:
                seen.add(s)
                ordered_slots.append(s)

    if not ordered_slots:
        ordered_slots = ["Local-1", "Local-2", "Remote-1"]

    for slot in ordered_slots:
        d = latest_ups_state.get(slot)
        if not d:
            prof = profs.get(slot, {})
            disp = prof.get("display_name", "Primary UPS (USB 1)" if slot == "Local-1" else ("Secondary UPS (USB 2)" if slot == "Local-2" else "Remote UPS (Network / IP)"))
            loc = prof.get("location", "Local")
            d = UPSData(name=disp, source="Auto-Scan", connected=False, mode="Offline", location=loc, display_name=disp)
            latest_ups_state[slot] = d

        d_dict = d.to_dict()
        d_dict["slot_name"] = slot
        d_dict["last_self_test"] = latest_st_map.get(slot) or latest_st_map.get(d.name)
        active_st = active_self_tests.get(slot)
        d_dict["test_active"] = bool(d.test_active or active_st is not None)
        if active_st:
            elapsed = time.time() - active_st["start_time"]
            total_dur = active_st.get("duration", 10.0)
            d_dict["test_progress"] = {
                "elapsed": round(elapsed, 1),
                "duration": total_dur,
                "remaining": max(0.0, round(total_dur - elapsed, 1)),
                "v_min": active_st.get("v_min"),
                "status": "RUNNING",
            }
        out.append(d_dict)
    return out


async def run_self_test_flow(slot_name: str, trigger_type: str = "manual") -> Dict[str, Any]:
    """Executes a complete 10-second battery self-test cycle on a given UPS slot."""
    slot_name = resolve_slot_name(slot_name)
    data = latest_ups_state.get(slot_name)
    if not data or not data.connected:
        return {"success": False, "error": f"UPS '{slot_name}' is offline or disconnected."}

    if (data.mode or "").capitalize() != "Line":
        return {"success": False, "error": f"Cannot run self-test while UPS is in {data.mode} mode."}

    if slot_name in active_self_tests:
        return {"success": False, "error": f"Self-test already in progress for '{slot_name}'."}

    disp_name = data.display_name or data.name
    location = data.location or "Local"
    v_before = data.battery_v if data.battery_v is not None else 27.0
    load_pct = data.load_pct if data.load_pct is not None else 0.0
    load_w = data.load_w_est if data.load_w_est is not None else 0.0

    test_info = {
        "slot_name": slot_name,
        "ups_name": disp_name,
        "start_time": time.time(),
        "duration": 10.0,
        "v_before": v_before,
        "v_min": v_before,
        "trigger_type": trigger_type,
        "cancel_requested": False,
    }
    active_self_tests[slot_name] = test_info

    # 1. Alert UI stream that test started
    alert_manager.send_self_test_started_alert(
        ups_name=disp_name,
        slot_name=slot_name,
        location=location,
        trigger_type=trigger_type,
    )

    # 2. Issue hardware command (Local vs Remote)
    loop = asyncio.get_running_loop()
    if slot_name == "Remote-1":
        queue_remote_command("START_SELF_TEST")
    else:
        await loop.run_in_executor(None, device_manager.start_self_test, slot_name, 10)

    # 3. Monitor during the 10-12s test cycle
    deadline = time.time() + 11.5
    while time.time() < deadline:
        await asyncio.sleep(1.0)
        if test_info.get("cancel_requested"):
            if slot_name == "Remote-1":
                queue_remote_command("CANCEL_SELF_TEST")
            else:
                await loop.run_in_executor(None, device_manager.cancel_self_test, slot_name)
            active_self_tests.pop(slot_name, None)
            db_manager.log_self_test_record(
                ups_name=disp_name,
                slot_name=slot_name,
                status="ABORTED",
                battery_v_before=v_before,
                battery_v_min=test_info["v_min"],
                battery_pct=data.battery_pct,
                load_pct=load_pct,
                duration_sec=round(time.time() - test_info["start_time"], 1),
                trigger_type=trigger_type,
                details="Aborted by user",
            )
            return {"success": False, "message": "Self-test aborted."}

        curr = latest_ups_state.get(slot_name)
        if curr and curr.battery_v is not None:
            if curr.battery_v < test_info["v_min"]:
                test_info["v_min"] = curr.battery_v

    # 4. Evaluate outcome
    active_self_tests.pop(slot_name, None)
    final_data = latest_ups_state.get(slot_name)
    v_min = test_info["v_min"]
    is_24v = (v_before or 24.0) >= 18.0
    min_healthy_v = 22.8 if is_24v else 11.4

    passed = True
    fail_reason = ""

    if not final_data or not final_data.connected:
        passed = False
        fail_reason = "Communication lost during self-test"
    elif final_data.fault:
        passed = False
        fail_reason = "UPS reported fault condition during battery discharge"
    elif v_min is not None and v_min < min_healthy_v:
        passed = False
        fail_reason = f"Battery voltage dropped critically to {v_min:.1f} V (minimum healthy: {min_healthy_v:.1f} V)"

    status = "PASSED" if passed else "FAILED"
    duration_actual = time.time() - test_info["start_time"]
    batt_pct = final_data.battery_pct if final_data else 100.0
    curr_load_pct = final_data.load_pct if final_data else load_pct
    curr_load_w = final_data.load_w_est if final_data else load_w

    # Log to SQLite DB
    db_manager.log_self_test_record(
        ups_name=disp_name,
        slot_name=slot_name,
        status=status,
        battery_v_before=v_before,
        battery_v_min=v_min,
        battery_pct=batt_pct,
        load_pct=curr_load_pct,
        duration_sec=round(duration_actual, 1),
        trigger_type=trigger_type,
        details=fail_reason if not passed else "Battery tested healthy under load",
    )

    # Trigger Viber Notification & Event
    alert_manager.send_self_test_result_alert(
        ups_name=disp_name,
        slot_name=slot_name,
        location=location,
        status=status,
        battery_v_before=v_before,
        battery_v_min=v_min,
        battery_pct=batt_pct,
        load_pct=curr_load_pct,
        load_w=curr_load_w,
        duration_sec=duration_actual,
        trigger_type=trigger_type,
        details=fail_reason,
    )

    return {
        "success": passed,
        "status": status,
        "battery_v_min": v_min,
        "battery_v_before": v_before,
        "details": fail_reason if not passed else "Self-test passed",
    }


def check_self_test_schedule():
    """Checks if current time matches scheduled self-test and executes if due."""
    global last_scheduled_self_test_key
    st_cfg = config_data.get("self_test", {})
    if not st_cfg.get("schedule_enabled", False):
        return

    freq = st_cfg.get("frequency", "daily").lower()
    sched_time = st_cfg.get("time", "09:00").strip()
    now_struct = time.localtime()
    curr_hm = time.strftime("%H:%M", now_struct)
    if curr_hm != sched_time:
        return

    today_str = time.strftime("%Y-%m-%d", now_struct)
    day_name = time.strftime("%A", now_struct).lower()
    day_of_month = now_struct.tm_mday

    target_key = None
    if freq == "daily":
        target_key = f"daily_{today_str}"
    elif freq == "weekly":
        cfg_day = st_cfg.get("day_of_week", "sunday").lower()
        if day_name == cfg_day:
            year_week = time.strftime("%Y_W%W", now_struct)
            target_key = f"weekly_{year_week}"
    elif freq == "monthly":
        cfg_mday = int(st_cfg.get("day_of_month", 1))
        if day_of_month == cfg_mday:
            year_month = time.strftime("%Y_%m", now_struct)
            target_key = f"monthly_{year_month}"

    if target_key and last_scheduled_self_test_key != target_key:
        last_scheduled_self_test_key = target_key
        target_slots = st_cfg.get("target_slots", ["Local-1", "Local-2"])
        for slot in target_slots:
            if slot in latest_ups_state and latest_ups_state[slot].connected:
                asyncio.create_task(run_self_test_flow(slot, trigger_type="schedule"))


def on_discovered_binding(slot: str, dev_id: str, driver_type: str):
    try:
        profs = get_profiles()
        if slot in profs:
            profs[slot]["device_id"] = dev_id
            profs[slot]["driver_type"] = driver_type
            save_profiles(profs)
            logger.info(f"Auto-saved locked hardware binding for '{slot}' -> {driver_type} ({dev_id})")
    except Exception as e:
        logger.error(f"Failed to auto-save binding for {slot}: {e}")


async def monitoring_loop():
    """Continuous background worker polling local devices and checking health."""
    global last_db_log_time, last_cleanup_time

    logger.info("Starting UPS Hardware Monitoring Loop...")

    while True:
        try:
            current_profiles = get_profiles()
            # Normalize legacy profile names if present
            if "Local-1" not in current_profiles and "TEC" in current_profiles:
                current_profiles["Local-1"] = current_profiles["TEC"]
            if "Local-2" not in current_profiles and "Turbo-X" in current_profiles:
                current_profiles["Local-2"] = current_profiles["Turbo-X"]
            if "Remote-1" not in current_profiles and "Remote-UPS" in current_profiles:
                current_profiles["Remote-1"] = current_profiles["Remote-UPS"]

            estimator.update_profiles(current_profiles)

            loop = asyncio.get_running_loop()

            # Poll local Slot 1 (Local-1) via DeviceManager with persistent port binding
            if current_profiles.get("Local-1", {}).get("enabled", True):
                prof_1 = current_profiles.get("Local-1", {})
                disp_name = prof_1.get("display_name", "Primary UPS (USB 1)")
                loc = prof_1.get("location", "Local Port 1")
                b_dev = prof_1.get("device_id", "")
                b_drv = prof_1.get("driver_type", "")
                l1_raw = await loop.run_in_executor(
                    None, device_manager.poll_slot, "Local-1", disp_name, loc, b_dev, b_drv, on_discovered_binding
                )
                l1_data = estimator.update(l1_raw)
                latest_ups_state["Local-1"] = l1_data
                alert_manager.process_ups_update(l1_data)

            # Poll local Slot 2 (Local-2) via DeviceManager with persistent port binding
            if current_profiles.get("Local-2", {}).get("enabled", True):
                prof_2 = current_profiles.get("Local-2", {})
                disp_name = prof_2.get("display_name", "Secondary UPS (USB 2)")
                loc = prof_2.get("location", "Local Port 2")
                b_dev = prof_2.get("device_id", "")
                b_drv = prof_2.get("driver_type", "")
                l2_raw = await loop.run_in_executor(
                    None, device_manager.poll_slot, "Local-2", disp_name, loc, b_dev, b_drv, on_discovered_binding
                )
                l2_data = estimator.update(l2_raw)
                latest_ups_state["Local-2"] = l2_data
                alert_manager.process_ups_update(l2_data)

            # Read Remote Receiver status (Remote-1)
            if current_profiles.get("Remote-1", {}).get("enabled", True):
                remote_raw = remote_receiver.read()
                remote_data = estimator.update(remote_raw)
                prof_rem = current_profiles.get("Remote-1", {})
                remote_data.display_name = prof_rem.get("display_name", "Remote UPS (Network / IP)")
                remote_data.location = prof_rem.get("location", "Remote Site")
                latest_ups_state["Remote-1"] = remote_data
                alert_manager.process_ups_update(remote_data)

            # Check daily report schedule
            all_data = list(latest_ups_state.values())
            alert_manager.check_daily_report_schedule(all_data)

            # Check scheduled self-test
            check_self_test_schedule()

            # Periodic SQLite Telemetry Logging
            now = time.time()
            any_on_battery = any(d.connected and d.mode == "Battery" for d in all_data)
            outage_fast_log = bool(config_data.get("db_outage_fast_log", True))

            if any_on_battery and outage_fast_log:
                # Fast 1-second resolution during active power outages
                effective_interval = 1.0
            else:
                effective_interval = float(
                    config_data.get("db_log_interval_seconds", 60.0)
                )

            # Check if a noticeable change occurred on any UPS
            log_on_change = bool(config_data.get("db_log_on_change", True))
            has_significant_change = False

            if log_on_change:
                for d in all_data:
                    if not d:
                        continue
                    prev = last_logged_telemetry_snapshot.get(d.name)
                    if not prev:
                        has_significant_change = True
                        break
                    
                    if prev.get("connected") != d.connected or prev.get("mode") != d.mode:
                        has_significant_change = True
                        break

                    if d.input_v is not None and prev.get("input_v") is not None:
                        if abs(d.input_v - prev["input_v"]) >= 2.0:
                            has_significant_change = True
                            break

                    if d.output_v is not None and prev.get("output_v") is not None:
                        if abs(d.output_v - prev["output_v"]) >= 2.0:
                            has_significant_change = True
                            break

                    if d.load_pct is not None and prev.get("load_pct") is not None:
                        if abs(d.load_pct - prev["load_pct"]) >= 3.0:
                            has_significant_change = True
                            break

                    if d.battery_pct is not None and prev.get("battery_pct") is not None:
                        if abs(d.battery_pct - prev["battery_pct"]) >= 1.0:
                            has_significant_change = True
                            break

            should_log = (now - last_db_log_time >= effective_interval) or has_significant_change
            if should_log:
                last_db_log_time = now
                for d in all_data:
                    if d:
                        last_logged_telemetry_snapshot[d.name] = {
                            "connected": d.connected,
                            "mode": d.mode,
                            "input_v": d.input_v,
                            "output_v": d.output_v,
                            "load_pct": d.load_pct,
                            "battery_pct": d.battery_pct,
                        }
                await loop.run_in_executor(
                    None, db_manager.log_telemetry_batch, all_data
                )

            # Periodic Database Retention Housekeeping (runs every 6 hours)
            if now - last_cleanup_time >= 21600.0:
                last_cleanup_time = now
                retention_days = int(config_data.get("db_retention_days", 30))
                if retention_days > 0:
                    await loop.run_in_executor(
                        None, db_manager.cleanup_old_records, retention_days
                    )

            # Broadcast live state to SSE clients
            status_payload = {
                "timestamp": now,
                "ups_list": get_ups_list_for_response(),
                "summary": compute_summary(all_data),
            }
            sse_msg = f"event: ups_status\ndata: {json.dumps(status_payload)}\n\n"
            for q in list(sse_clients):
                try:
                    q.put_nowait(sse_msg)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

        poll_interval = float(
            config_data.get("server", {}).get("poll_interval_seconds", 2.0)
        )
        await asyncio.sleep(max(0.5, poll_interval))


def compute_summary(ups_list: List[UPSData]) -> Dict[str, Any]:
    total_watts = 0.0
    total_load_pct_sum = 0.0
    connected_count = 0
    battery_mode_count = 0
    overload_count = 0
    overload_thresh = float(config_data.get("overload_threshold_pct", 70.0))

    for d in ups_list:
        if d.connected:
            connected_count += 1
            total_watts += float(d.load_w_est or 0.0)
            total_load_pct_sum += float(d.load_pct or 0.0)
            if (d.mode or "").capitalize() == "Battery":
                battery_mode_count += 1
            if (d.load_pct or 0.0) >= overload_thresh:
                overload_count += 1

    avg_load = round(total_load_pct_sum / max(1, connected_count), 1) if connected_count > 0 else 0.0

    system_status = "NORMAL"
    if battery_mode_count > 0:
        system_status = "ON_BATTERY"
    elif connected_count == 0:
        system_status = "OFFLINE"
    elif overload_count > 0:
        system_status = "OVERLOAD"

    return {
        "system_status": system_status,
        "total_watts": round(total_watts, 1),
        "avg_load_pct": avg_load,
        "total_ups": len(ups_list),
        "online_ups": connected_count,
        "on_battery_count": battery_mode_count,
        "overload_count": overload_count,
    }


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.get("/api/status")
def get_status():
    all_data = list(latest_ups_state.values())
    return {
        "timestamp": time.time(),
        "timestamp_iso": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ups_list": get_ups_list_for_response(),
        "summary": compute_summary(all_data),
    }


@app.get("/api/history")
def get_history(
    period: int = Query(3600, description="Period in seconds (300, 3600, 21600, 86400, 604800)"),
    ups_name: Optional[str] = Query(None, description="Filter by UPS name"),
):
    data = db_manager.get_history(
        ups_name=ups_name,
        period_seconds=float(period),
        max_points=250,
    )
    return {"status": "ok", "period": period, "history": data}


@app.get("/api/events")
def get_events(
    limit: int = Query(50, ge=1, le=500),
    ups_name: Optional[str] = None,
    severity: Optional[str] = None,
):
    events = db_manager.get_events(limit=limit, ups_name=ups_name, severity=severity)
    return {"status": "ok", "count": len(events), "events": events}


@app.post("/api/remote/push")
async def push_remote_telemetry(
    request: Request,
    x_api_key: Optional[str] = Header(None),
):
    global remote_pending_commands
    expected_key = config_data.get("remote_api_key", "ups_remote_secret_key_123")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid X-API-Key header.")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    client_ip = request.client.host if request.client else "unknown"
    remote_data = remote_receiver.push_telemetry(body, client_ip=client_ip)

    target_slot = "Remote-1" if "Remote-1" in get_profiles() else body.get("name", "Remote-1")
    prof_rem = get_profiles().get(target_slot, {})
    remote_data.name = target_slot
    remote_data.display_name = prof_rem.get("display_name", "Remote UPS (Network / IP)")
    if prof_rem.get("location"):
        remote_data.location = prof_rem.get("location")

    # Run estimator with canonical profile slot
    remote_data = estimator.update(remote_data)
    
    # Check if Remote-1 is currently undergoing a self-test
    if target_slot in active_self_tests or "Remote-1" in active_self_tests:
        remote_data.test_active = True

    latest_ups_state[target_slot] = remote_data
    alert_manager.process_ups_update(remote_data)

    # Pop pending commands for this remote agent
    cmds_to_send = list(remote_pending_commands)
    remote_pending_commands.clear()

    return {
        "status": "success",
        "received_at": time.time(),
        "ups": remote_data.display_name or remote_data.name,
        "pending_commands": cmds_to_send,
    }


@app.get("/api/settings")
def get_settings():
    return {
        "config": get_config(),
        "profiles": get_profiles(),
        "learning": estimator.learning,
    }


@app.post("/api/settings")
async def save_settings_endpoint(request: Request):
    global config_data, profiles_data
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    if "config" in body:
        new_cfg = body["config"]
        save_config(new_cfg)
        config_data = get_config()

        # Update Viber service
        v_cfg = config_data.get("viber", {})
        viber_service.update_config(
            token=v_cfg.get("channel_token", ""),
            sender_name=v_cfg.get("sender_name", "UPS Monitor"),
            receiver_id=v_cfg.get("receiver_id", ""),
        )
        alert_manager.update_config(config_data)

    if "profiles" in body:
        new_prof = body["profiles"]
        save_profiles(new_prof)
        profiles_data = get_profiles()
        estimator.update_profiles(profiles_data)

        # Immediately update in-memory state display_name and location
        for k, p in profiles_data.items():
            if k in latest_ups_state:
                latest_ups_state[k].display_name = p.get("display_name", k)
                if p.get("location"):
                    latest_ups_state[k].location = p.get("location")

    return {"status": "success", "message": "Settings updated successfully."}


@app.post("/api/settings/language")
async def set_language_endpoint(request: Request):
    global config_data
    try:
        body = await request.json()
        lang = body.get("language", "el")
    except Exception:
        lang = "el"

    config_data = get_config()
    config_data["language"] = lang
    if "ui_settings" not in config_data:
        config_data["ui_settings"] = {}
    config_data["ui_settings"]["language"] = lang
    save_config(config_data)
    alert_manager.update_config(config_data)

    return {"status": "success", "language": lang}


@app.post("/api/viber/test")
def test_viber():
    lang = config_data.get("language") or config_data.get("ui_settings", {}).get("language", "el")
    success, err = viber_service.send_test_message(lang=lang)
    if not success:
        return {"status": "error", "message": err or "Failed to send test message."}
    return {"status": "success", "message": "Test alert sent successfully to Viber!"}


@app.post("/api/viber/daily-report")
def manual_daily_report():
    all_data = list(latest_ups_state.values())
    success, err = alert_manager.send_daily_report(all_data)
    if not success:
        return {"status": "error", "message": err or "Failed to send report."}
    return {"status": "success", "message": "Daily report sent to Viber!"}


@app.post("/api/devices/rescan")
async def rescan_devices():
    loop = asyncio.get_running_loop()
    current_profiles = get_profiles()
    results = await loop.run_in_executor(
        None,
        device_manager.rescan_all,
        current_profiles,
        save_profiles,
    )
    return {
        "status": "success",
        "message": "USB device re-scan completed successfully.",
        "results": results,
        "profiles": get_profiles(),
    }


@app.post("/api/learning/reset")
def reset_learning():
    estimator.learning = {}
    estimator._save_learning()
    return {"status": "success", "message": "Battery learning reset to default."}


@app.post("/api/ups/{slot_name}/buzzer/toggle")
async def toggle_ups_buzzer(slot_name: str):
    slot_name = resolve_slot_name(slot_name)
    if slot_name == "Remote-1":
        queue_remote_command("TOGGLE_BUZZER")
        data = latest_ups_state.get(slot_name)
        disp_name = (data.display_name or data.name or slot_name) if data else slot_name
        new_state = not (data.beeper_on if data and data.beeper_on is not None else False)
        if data:
            data.beeper_on = new_state
        alert_manager.log_buzzer_toggle_event(disp_name, slot_name, new_state)
        return {
            "status": "success",
            "slot_name": slot_name,
            "beeper_on": new_state,
            "message": "Buzzer toggle command queued for Remote UPS.",
        }

    loop = asyncio.get_running_loop()
    res = await loop.run_in_executor(None, device_manager.toggle_buzzer, slot_name)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to toggle buzzer."))

    data = latest_ups_state.get(slot_name)
    disp_name = (data.display_name or data.name or slot_name) if data else slot_name
    # Invert known beeper state
    new_state = not (data.beeper_on if data and data.beeper_on is not None else False)
    if data:
        data.beeper_on = new_state

    alert_manager.log_buzzer_toggle_event(disp_name, slot_name, new_state)
    return {
        "status": "success",
        "slot_name": slot_name,
        "beeper_on": new_state,
        "message": "Buzzer state toggled successfully.",
    }


@app.post("/api/ups/{slot_name}/self-test")
async def start_ups_self_test(slot_name: str):
    canonical_slot = resolve_slot_name(slot_name)
    if canonical_slot not in latest_ups_state and canonical_slot not in get_profiles():
        raise HTTPException(status_code=404, detail=f"UPS slot '{slot_name}' not found.")

    ups_data = latest_ups_state.get(canonical_slot)
    if not ups_data or not ups_data.connected:
        raise HTTPException(status_code=400, detail=f"UPS '{canonical_slot}' is currently offline.")

    if canonical_slot in active_self_tests:
        raise HTTPException(status_code=400, detail=f"Self-test is already running for '{canonical_slot}'.")

    # run_self_test_flow initializes active_self_tests and calls hardware
    asyncio.create_task(run_self_test_flow(canonical_slot, trigger_type="manual"))
    return {
        "status": "started",
        "slot_name": canonical_slot,
        "message": "Battery self-test started (10 seconds)...",
    }


@app.post("/api/ups/{slot_name}/self-test/cancel")
async def cancel_ups_self_test(slot_name: str):
    canonical_slot = resolve_slot_name(slot_name)
    if canonical_slot in active_self_tests:
        active_self_tests[canonical_slot]["cancel_requested"] = True
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, device_manager.cancel_self_test, canonical_slot)
        return {"status": "success", "message": "Cancellation requested for self-test."}
    return {"status": "error", "message": "No active self-test to cancel."}


@app.get("/api/self-test/latest")
def get_latest_self_tests_endpoint():
    return {"status": "ok", "latest": db_manager.get_all_latest_self_tests()}


@app.get("/api/self-test/history")
def get_self_test_history_endpoint(
    slot_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    lim = int(limit.default if hasattr(limit, "default") else limit)
    history = db_manager.get_self_test_history(slot_name=slot_name, limit=lim)
    return {"status": "ok", "count": len(history), "history": history}


@app.get("/api/version")
def get_version_info():
    return updater.get_local_version()


@app.get("/api/update/status")
@app.get("/api/check-update")
def get_update_status():
    return updater.check_for_updates()


@app.post("/api/update/perform")
@app.post("/api/apply-update")
def perform_update():
    success, msg = updater.run_update()
    if not success:
        return {"status": "error", "message": msg}
    return {"status": "success", "message": msg}


@app.get("/api/export/csv")
def export_csv(
    type: str = Query("events", pattern="^(events|telemetry)$"),
    hours: int = Query(24, ge=1, le=720),
):
    if type == "events":
        csv_str = db_manager.export_events_csv()
        filename = f"ups_events_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        csv_str = db_manager.export_telemetry_csv(hours=hours)
        filename = f"ups_telemetry_{time.strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/stream")
async def sse_stream():
    """Server-Sent Events for real-time live telemetry without repeated polling."""
    queue = asyncio.Queue()
    sse_clients.append(queue)

    async def event_generator():
        # Send initial full status upon connection
        initial_data = {
            "timestamp": time.time(),
            "ups_list": get_ups_list_for_response(),
            "summary": compute_summary(list(latest_ups_state.values())),
        }
        yield f"event: ups_status\ndata: {json.dumps(initial_data)}\n\n"

        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            if queue in sse_clients:
                sse_clients.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Static Frontend Files
STATIC_DIR = BASE_DIR / "static"
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>UPS Status WebUI is loading...</h1>")


def main():
    cfg = get_config()
    server_cfg = cfg.get("server", {})
    host = server_cfg.get("host", "0.0.0.0")
    port = int(server_cfg.get("port", 8088))

    print("=" * 60)
    print("⚡ UPS STATUS WEB MONITOR 3.0")
    print(f"🌐 WebUI URL: http://localhost:{port}")
    print(f"📡 Remote Push API: http://localhost:{port}/api/remote/push")
    print("=" * 60)

    uvicorn.run("app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
