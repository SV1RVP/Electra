from __future__ import annotations

import csv
import io
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from drivers.models import UPSData, UPSEvent


class DBManager:
    """
    SQLite Database Manager with WAL mode for high-concurrency logging,
    smart time-series queries with downsampling, and event history tracking.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    ups_name TEXT NOT NULL,
                    connected INTEGER NOT NULL,
                    mode TEXT,
                    input_v REAL,
                    output_v REAL,
                    input_hz REAL,
                    output_hz REAL,
                    load_pct REAL,
                    load_w REAL,
                    battery_v REAL,
                    battery_pct REAL,
                    runtime_min REAL,
                    temperature_c REAL
                );

                CREATE INDEX IF NOT EXISTS idx_telemetry_ups_time 
                ON telemetry(ups_name, timestamp);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    ups_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'info',
                    data_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_events_time 
                ON events(timestamp DESC);

                CREATE TABLE IF NOT EXISTS self_test_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    ups_name TEXT NOT NULL,
                    slot_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    battery_v_before REAL,
                    battery_v_min REAL,
                    battery_pct REAL,
                    load_pct REAL,
                    duration_sec REAL,
                    trigger_type TEXT NOT NULL DEFAULT 'manual',
                    details TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_self_test_ups 
                ON self_test_history(slot_name, timestamp DESC);
                """
            )

    def log_telemetry_batch(self, data_list: List[UPSData]) -> None:
        now = time.time()
        rows = []
        for d in data_list:
            if not d:
                continue
            rows.append(
                (
                    now,
                    d.name,
                    1 if d.connected else 0,
                    d.mode,
                    d.input_v,
                    d.output_v,
                    d.input_hz,
                    d.output_hz,
                    d.load_pct,
                    d.load_w_est,
                    d.battery_v,
                    d.battery_pct,
                    d.runtime_minutes,
                    d.temperature_c,
                )
            )

        if not rows:
            return

        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO telemetry (
                    timestamp, ups_name, connected, mode, input_v, output_v,
                    input_hz, output_hz, load_pct, load_w, battery_v,
                    battery_pct, runtime_min, temperature_c
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def log_event(self, event: UPSEvent) -> int:
        data_str = json.dumps(event.data) if event.data else None
        safe_ups_name = event.ups_name or "UPS"
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO events (timestamp, ups_name, event_type, message, severity, data_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp,
                    safe_ups_name,
                    event.event_type,
                    event.message,
                    event.severity,
                    data_str,
                ),
            )
            return cur.lastrowid

    def get_events(
        self,
        limit: int = 100,
        ups_name: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM events"
        params: List[Any] = []
        conditions = []

        if ups_name:
            conditions.append("ups_name = ?")
            params.append(ups_name)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["timestamp_iso"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(r["timestamp"])
                )
                if item.get("data_json"):
                    try:
                        item["data"] = json.loads(item["data_json"])
                    except Exception:
                        item["data"] = None
                results.append(item)
            return results

    def get_history(
        self,
        ups_name: Optional[str] = None,
        period_seconds: float = 3600.0,
        max_points: int = 200,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieves time-series data for charts. If there are many rows,
        buckets and averages them to return smooth, fast series.
        """
        start_time = time.time() - period_seconds

        with self._get_connection() as conn:
            cur = conn.execute("SELECT DISTINCT ups_name FROM telemetry")
            all_db_names = [row["ups_name"] for row in cur.fetchall()]

            if ups_name and ups_name.lower() != "all":
                target_names = []
                u_clean = ups_name.lower().replace("-", "").replace("_", "").replace(" ", "")
                for dbn in all_db_names:
                    dbn_clean = dbn.lower().replace("-", "").replace("_", "").replace(" ", "")
                    if dbn == ups_name or dbn_clean == u_clean:
                        target_names.append(dbn)
                    elif ("local1" in u_clean or "primary" in u_clean or "usb1" in u_clean or "tec" in u_clean) and \
                         ("local1" in dbn_clean or "primary" in dbn_clean or "usb1" in dbn_clean or "tec" in dbn_clean):
                        target_names.append(dbn)
                    elif ("local2" in u_clean or "secondary" in u_clean or "usb2" in u_clean or "turbo" in u_clean) and \
                         ("local2" in dbn_clean or "secondary" in dbn_clean or "usb2" in dbn_clean or "turbo" in dbn_clean):
                        target_names.append(dbn)
                    elif ("remote" in u_clean or "network" in u_clean or "site" in u_clean or "ip" in u_clean) and \
                         ("remote" in dbn_clean or "network" in dbn_clean or "site" in dbn_clean or "ip" in dbn_clean):
                        target_names.append(dbn)
                names = target_names if target_names else [ups_name]
            else:
                names = all_db_names

            data_by_ups: Dict[str, List[Dict[str, Any]]] = {}

            for name in names:
                # Count total points in range
                count_row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM telemetry WHERE ups_name = ? AND timestamp >= ?",
                    (name, start_time),
                ).fetchone()
                total_cnt = count_row["cnt"] if count_row else 0

                if total_cnt == 0:
                    data_by_ups[name] = []
                    continue

                if total_cnt <= max_points:
                    rows = conn.execute(
                        """
                        SELECT timestamp, mode, input_v, output_v, input_hz,
                               load_pct, load_w, battery_v, battery_pct, runtime_min
                        FROM telemetry
                        WHERE ups_name = ? AND timestamp >= ?
                        ORDER BY timestamp ASC
                        """,
                        (name, start_time),
                    ).fetchall()
                    data_by_ups[name] = [
                        {
                            "timestamp": r["timestamp"],
                            "time_label": time.strftime(
                                "%H:%M:%S" if period_seconds <= 86400 else "%m/%d %H:%M",
                                time.localtime(r["timestamp"]),
                            ),
                            "mode": r["mode"],
                            "input_v": r["input_v"],
                            "output_v": r["output_v"],
                            "input_hz": r["input_hz"],
                            "load_pct": r["load_pct"],
                            "load_w": r["load_w"],
                            "battery_v": r["battery_v"],
                            "battery_pct": r["battery_pct"],
                            "runtime_min": r["runtime_min"],
                        }
                        for r in rows
                    ]
                else:
                    # Time bucket aggregation
                    bucket_size = max(1.0, period_seconds / max_points)
                    rows = conn.execute(
                        f"""
                        SELECT 
                            CAST(timestamp / {bucket_size} AS INT) * {bucket_size} as bucket_time,
                            mode,
                            ROUND(AVG(input_v), 1) as input_v,
                            ROUND(AVG(output_v), 1) as output_v,
                            ROUND(AVG(input_hz), 1) as input_hz,
                            ROUND(AVG(load_pct), 1) as load_pct,
                            ROUND(AVG(load_w), 1) as load_w,
                            ROUND(AVG(battery_v), 2) as battery_v,
                            ROUND(AVG(battery_pct), 1) as battery_pct,
                            ROUND(AVG(runtime_min), 1) as runtime_min
                        FROM telemetry
                        WHERE ups_name = ? AND timestamp >= ?
                        GROUP BY CAST(timestamp / {bucket_size} AS INT)
                        ORDER BY bucket_time ASC
                        """,
                        (name, start_time),
                    ).fetchall()
                    data_by_ups[name] = [
                        {
                            "timestamp": r["bucket_time"],
                            "time_label": time.strftime(
                                "%H:%M:%S" if period_seconds <= 86400 else "%m/%d %H:%M",
                                time.localtime(r["bucket_time"]),
                            ),
                            "mode": r["mode"],
                            "input_v": r["input_v"],
                            "output_v": r["output_v"],
                            "input_hz": r["input_hz"],
                            "load_pct": r["load_pct"],
                            "load_w": r["load_w"],
                            "battery_v": r["battery_v"],
                            "battery_pct": r["battery_pct"],
                            "runtime_min": r["runtime_min"],
                        }
                        for r in rows
                    ]

            return data_by_ups

    def export_events_csv(self) -> str:
        events = self.get_events(limit=5000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "DateTime", "UPS", "Event Type", "Severity", "Message"])
        for e in events:
            writer.writerow([
                e.get("id"),
                e.get("timestamp"),
                e.get("timestamp_iso"),
                e.get("ups_name"),
                e.get("event_type"),
                e.get("severity"),
                e.get("message"),
            ])
        return output.getvalue()

    def export_telemetry_csv(self, hours: int = 24, ups_name: Optional[str] = None) -> str:
        start_time = time.time() - (hours * 3600)
        query = "SELECT * FROM telemetry WHERE timestamp >= ?"
        params: List[Any] = [start_time]
        if ups_name:
            query += " AND ups_name = ?"
            params.append(ups_name)
        query += " ORDER BY timestamp ASC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Timestamp", "DateTime", "UPS", "Connected", "Mode",
                "Input(V)", "Output(V)", "Input(Hz)", "Load(%)", "Load(W)",
                "Battery(V)", "Battery(%)", "Runtime(min)", "Temp(C)"
            ])
            for r in rows:
                writer.writerow([
                    r["timestamp"],
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["timestamp"])),
                    r["ups_name"],
                    r["connected"],
                    r["mode"],
                    r["input_v"],
                    r["output_v"],
                    r["input_hz"],
                    r["load_pct"],
                    r["load_w"],
                    r["battery_v"],
                    r["battery_pct"],
                    r["runtime_min"],
                    r["temperature_c"],
                ])
            return output.getvalue()

    def cleanup_old_records(self, retention_days: int = 30) -> int:
        if retention_days <= 0:
            return 0  # 0 means Infinite / Unlimited history retention
        cutoff = time.time() - (retention_days * 86400)
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM telemetry WHERE timestamp < ?", (cutoff,))
            deleted = cur.rowcount
            conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM self_test_history WHERE timestamp < ?", (cutoff,))
            return deleted

    def log_self_test_record(
        self,
        ups_name: str,
        slot_name: str,
        status: str,
        battery_v_before: Optional[float] = None,
        battery_v_min: Optional[float] = None,
        battery_pct: Optional[float] = None,
        load_pct: Optional[float] = None,
        duration_sec: float = 10.0,
        trigger_type: str = "manual",
        details: str = "",
        timestamp: Optional[float] = None,
    ) -> int:
        ts = timestamp if timestamp is not None else time.time()
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO self_test_history (
                    timestamp, ups_name, slot_name, status,
                    battery_v_before, battery_v_min, battery_pct,
                    load_pct, duration_sec, trigger_type, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    ups_name,
                    slot_name,
                    status,
                    battery_v_before,
                    battery_v_min,
                    battery_pct,
                    load_pct,
                    duration_sec,
                    trigger_type,
                    details,
                ),
            )
            return cur.lastrowid

    def get_last_self_test(self, slot_or_name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM self_test_history
                WHERE slot_name = ? OR ups_name = ?
                ORDER BY timestamp DESC LIMIT 1
                """,
                (slot_or_name, slot_or_name),
            ).fetchone()
            if row:
                item = dict(row)
                item["timestamp_iso"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(item["timestamp"])
                )
                return item
            return None

    def get_all_latest_self_tests(self) -> Dict[str, Dict[str, Any]]:
        """Returns map of slot_name -> latest self-test dict."""
        results: Dict[str, Dict[str, Any]] = {}
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM self_test_history
                ORDER BY timestamp DESC
                """
            ).fetchall()
            for r in rows:
                slot = r["slot_name"]
                if slot not in results:
                    item = dict(r)
                    item["timestamp_iso"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(item["timestamp"])
                    )
                    results[slot] = item
        return results

    def get_self_test_history(
        self,
        slot_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM self_test_history"
        params: List[Any] = []
        if slot_name:
            query += " WHERE slot_name = ? OR ups_name = ?"
            params.extend([slot_name, slot_name])
        lim = int(limit.default if hasattr(limit, "default") else limit)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(lim)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["timestamp_iso"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(item["timestamp"])
                )
                results.append(item)
            return results
