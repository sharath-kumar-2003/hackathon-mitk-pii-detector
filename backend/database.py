import sqlite3
import json
import os
import time
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "firewall_audit.db")

class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Audit events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE,
                    timestamp REAL,
                    timestamp_iso TEXT,
                    session_id TEXT,
                    tool_name TEXT,
                    user_prompt_preview TEXT,
                    original_arguments_preview TEXT,
                    sanitized_arguments_preview TEXT,
                    policy_decision TEXT,
                    policy_reason TEXT,
                    pii_detected TEXT,
                    sanitization_action TEXT,
                    outbound_verification TEXT,
                    restoration_outcome TEXT,
                    timings_ms TEXT,
                    final_status TEXT,
                    is_evaluation_run INTEGER
                )
            """)

            # Evaluation runs summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT UNIQUE,
                    timestamp_iso TEXT,
                    total_requests INTEGER,
                    allowed_count INTEGER,
                    sanitized_count INTEGER,
                    blocked_count INTEGER,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    detection_rate REAL,
                    leakage_prevention_rate REAL,
                    full_report_json TEXT
                )
            """)

            conn.commit()

    def log_event(self, event: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audit_events (
                    request_id, timestamp, timestamp_iso, session_id, tool_name,
                    user_prompt_preview, original_arguments_preview, sanitized_arguments_preview,
                    policy_decision, policy_reason, pii_detected, sanitization_action,
                    outbound_verification, restoration_outcome, timings_ms, final_status, is_evaluation_run
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.get("request_id"),
                event.get("timestamp", time.time()),
                event.get("timestamp_iso", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                event.get("session_id", "session_default"),
                event.get("tool_name", "unknown"),
                event.get("user_prompt_preview", ""),
                json.dumps(event.get("original_arguments_preview", {})),
                json.dumps(event.get("sanitized_arguments_preview", {})),
                event.get("policy_decision", "UNKNOWN"),
                event.get("policy_reason", ""),
                json.dumps(event.get("pii_detected", [])),
                event.get("sanitization_action", "none"),
                json.dumps(event.get("outbound_verification", {})),
                json.dumps(event.get("restoration_outcome", {})),
                json.dumps(event.get("timings_ms", {})),
                event.get("final_status", "COMPLETED"),
                1 if event.get("is_evaluation_run", False) else 0
            ))
            conn.commit()

    def get_logs(self, limit: int = 100, tool_name: Optional[str] = None, outcome: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM audit_events WHERE 1=1"
            params = []
            if tool_name:
                query += " AND tool_name = ?"
                params.append(tool_name)
            if outcome:
                query += " AND (LOWER(final_status) = ? OR LOWER(policy_decision) = ?)"
                params.append(outcome.lower())
                params.append(outcome.lower())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                logs.append({
                    "request_id": row["request_id"],
                    "timestamp": row["timestamp"],
                    "timestamp_iso": row["timestamp_iso"],
                    "session_id": row["session_id"],
                    "tool_name": row["tool_name"],
                    "user_prompt_preview": row["user_prompt_preview"],
                    "original_arguments_preview": json.loads(row["original_arguments_preview"] or "{}"),
                    "sanitized_arguments_preview": json.loads(row["sanitized_arguments_preview"] or "{}"),
                    "policy_decision": row["policy_decision"],
                    "policy_reason": row["policy_reason"],
                    "pii_detected": json.loads(row["pii_detected"] or "[]"),
                    "sanitization_action": row["sanitization_action"],
                    "outbound_verification": json.loads(row["outbound_verification"] or "{}"),
                    "restoration_outcome": json.loads(row["restoration_outcome"] or "{}"),
                    "timings_ms": json.loads(row["timings_ms"] or "{}"),
                    "final_status": row["final_status"],
                    "is_evaluation_run": bool(row["is_evaluation_run"])
                })
            return logs

    def save_evaluation_run(self, run_id: str, results: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            req_sum = results.get("requests_summary", {})
            det_ana = results.get("detection_analytics", {})
            leak_ana = results.get("leakage_prevention", {})
            
            cursor.execute("""
                INSERT OR REPLACE INTO evaluation_runs (
                    run_id, timestamp_iso, total_requests, allowed_count, sanitized_count,
                    blocked_count, precision, recall, f1_score, detection_rate,
                    leakage_prevention_rate, full_report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                results.get("total_requests", 0),
                req_sum.get("allowed", 0),
                req_sum.get("sanitized", 0),
                req_sum.get("blocked", 0),
                det_ana.get("precision", 0.0),
                det_ana.get("recall", 0.0),
                det_ana.get("f1_score", 0.0),
                det_ana.get("detection_rate_pct", 0.0),
                leak_ana.get("leakage_prevention_rate_pct", 100.0),
                json.dumps(results)
            ))
            conn.commit()

    def clear_all(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audit_events")
            cursor.execute("DELETE FROM evaluation_runs")
            conn.commit()
